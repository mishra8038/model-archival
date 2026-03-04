#!/usr/bin/env bash
# =============================================================================
# deploy/proxmox-attach-disks.sh
# Run on the Proxmox HOST (not inside the VM).
#
# Discovers all physical HDDs/SSDs that are NOT used by Proxmox itself
# (i.e. not part of a ZFS pool, LVM group, or holding the OS), then
# passes them through to VM 106 as individual SCSI passthrough devices.
#
# Prerequisites on the Proxmox host:
#   - qm          (included in Proxmox VE)
#   - lsblk, lspci, udevadm  (included in all Proxmox installs)
#
# Usage:
#   bash proxmox-attach-disks.sh [--vm-id 106] [--dry-run] [--force]
#
# Safety:
#   - By default runs in DRY-RUN mode and only prints the qm commands.
#   - Pass --force to actually execute them.
#   - The VM must be shut down before disks are attached (checked below).
#   - Only whole-disk passthrough (not partition) is used, which is the
#     safest and most portable method.
#   - The script is idempotent: disks already attached are detected and
#     skipped.
#
# SCSI controller:
#   Proxmox VE uses VirtIO-SCSI by default. We attach each disk as
#   scsi<N> starting from scsi1 (scsi0 is typically the OS disk).
#   The VM must have a SCSI controller configured (VirtIO-SCSI or LSI).
#
# After running this script:
#   - Boot the VM.
#   - Inside the VM: run   lsblk   to confirm the disks appear.
#   - Format / mount them as needed, add entries to /etc/fstab by UUID.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
VM_ID=106
DRY_RUN=true   # safe by default; override with --force
SCSI_START=1   # first SCSI slot to use (0 is usually the OS boot disk)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { echo -e "\033[1;32m[INFO]\033[0m  $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
error() { echo -e "\033[1;31m[ERROR]\033[0m $*" >&2; exit 1; }
run()   {
    if $DRY_RUN; then
        echo -e "\033[1;34m[DRY-RUN]\033[0m  $*"
    else
        info "Running: $*"
        eval "$*"
    fi
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --vm-id)   VM_ID="$2";    shift 2 ;;
        --dry-run) DRY_RUN=true;  shift   ;;
        --force)   DRY_RUN=false; shift   ;;
        *) error "Unknown argument: $1" ;;
    esac
done

# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------
[[ $(id -u) -eq 0 ]] || error "This script must be run as root on the Proxmox host."
command -v qm      &>/dev/null || error "'qm' not found — are you on the Proxmox host?"
command -v lsblk   &>/dev/null || error "'lsblk' not found."
command -v pvs     &>/dev/null || PVS_AVAIL=false && PVS_AVAIL=true
command -v zpool   &>/dev/null || ZPOOL_AVAIL=false && ZPOOL_AVAIL=true

# Check VM exists
qm status "$VM_ID" &>/dev/null || error "VM $VM_ID does not exist."

# Check VM is stopped (passthrough requires the VM to be off)
VM_STATUS=$(qm status "$VM_ID" | awk '{print $2}')
if [[ "$VM_STATUS" != "stopped" ]]; then
    error "VM $VM_ID is currently '$VM_STATUS'. Shut it down before attaching disks:
       qm shutdown $VM_ID"
fi
info "VM $VM_ID is stopped — safe to attach disks."

# ---------------------------------------------------------------------------
# Step 1: Collect disks that Proxmox itself is using (to exclude them)
# ---------------------------------------------------------------------------

# ZFS pool members
ZFS_DISKS=()
if $ZPOOL_AVAIL; then
    while IFS= read -r line; do
        # zpool status shows member disks as bare names (sda) or full paths
        dev=$(echo "$line" | awk '{print $1}' | sed 's|/dev/||')
        [[ -n "$dev" && "$dev" != "NAME" ]] && ZFS_DISKS+=("$dev")
    done < <(zpool status 2>/dev/null | awk '/^\s+(sd[a-z]+|nvme[0-9]+n[0-9]+|vd[a-z]+)/{print $1}')
fi
info "ZFS member disks: ${ZFS_DISKS[*]:-none}"

# LVM physical volumes
LVM_DISKS=()
if $PVS_AVAIL; then
    while IFS= read -r pv; do
        dev=$(basename "$pv" | sed 's/[0-9]*$//')   # strip partition number
        [[ -n "$dev" ]] && LVM_DISKS+=("$dev")
    done < <(pvs --noheadings -o pv_name 2>/dev/null | awk '{print $1}')
fi
info "LVM physical volumes: ${LVM_DISKS[*]:-none}"

# Disk holding the root filesystem
ROOT_DISK=$(lsblk -no PKNAME "$(findmnt -n -o SOURCE /)" 2>/dev/null \
            || lsblk -no PKNAME "$(df / | tail -1 | awk '{print $1}')" 2>/dev/null \
            || echo "")
ROOT_DISK=$(basename "$ROOT_DISK")
info "Root filesystem disk: ${ROOT_DISK:-unknown}"

# Build exclusion set
declare -A EXCLUDE
for d in "${ZFS_DISKS[@]:-}" "${LVM_DISKS[@]:-}"; do
    [[ -n "$d" ]] && EXCLUDE["$d"]=1
done
[[ -n "$ROOT_DISK" ]] && EXCLUDE["$ROOT_DISK"]=1

# ---------------------------------------------------------------------------
# Step 2: Enumerate candidate disks
# ---------------------------------------------------------------------------
info "Scanning block devices…"
echo ""
printf "%-12s %-8s %-10s %-30s %s\n" "DEVICE" "SIZE" "ROTA" "MODEL" "SERIAL"
printf "%-12s %-8s %-10s %-30s %s\n" "------" "----" "----" "-----" "------"

CANDIDATES=()
while IFS= read -r dev; do
    name=$(echo "$dev" | awk '{print $1}')
    size=$(echo "$dev" | awk '{print $2}')
    rota=$(echo "$dev" | awk '{print $3}')   # 1=HDD, 0=SSD/NVMe
    model=$(echo "$dev" | awk '{print $4}')
    serial=$(udevadm info --query=property --name="/dev/$name" 2>/dev/null \
             | grep ID_SERIAL_SHORT | cut -d= -f2 || echo "unknown")
    type=$([[ "$rota" == "1" ]] && echo "HDD" || echo "SSD")

    # Skip if in exclusion set (or a child partition/loop device)
    if [[ -n "${EXCLUDE[$name]:-}" ]]; then
        printf "%-12s %-8s %-10s %-30s %s  [SKIP — in use by Proxmox]\n" \
               "$name" "$size" "$type" "$model" "$serial"
        continue
    fi

    printf "%-12s %-8s %-10s %-30s %s\n" "$name" "$size" "$type" "$model" "$serial"
    CANDIDATES+=("$name")
done < <(lsblk -dno NAME,SIZE,ROTA,MODEL --include 8,259,252 2>/dev/null \
         | grep -v "^loop\|^sr\|^fd")

echo ""

if [[ ${#CANDIDATES[@]} -eq 0 ]]; then
    warn "No candidate disks found to attach. All disks appear to be in use by Proxmox."
    exit 0
fi

info "Candidate disks for VM $VM_ID passthrough: ${CANDIDATES[*]}"

# ---------------------------------------------------------------------------
# Step 3: Detect already-attached disks (idempotency)
# ---------------------------------------------------------------------------
CURRENT_CONF=$(qm config "$VM_ID" 2>/dev/null || true)
ALREADY_ATTACHED=()
for dev in "${CANDIDATES[@]}"; do
    if echo "$CURRENT_CONF" | grep -q "$dev"; then
        warn "  /dev/$dev already appears in VM $VM_ID config — will skip."
        ALREADY_ATTACHED+=("$dev")
    fi
done

# ---------------------------------------------------------------------------
# Step 4: Determine next free SCSI slots
# ---------------------------------------------------------------------------
# Find highest used scsi<N> in current config
MAX_SCSI=$(echo "$CURRENT_CONF" | grep -oP 'scsi\K[0-9]+' | sort -n | tail -1 || echo "0")
NEXT_SLOT=$(( MAX_SCSI + 1 ))
[[ "$NEXT_SLOT" -lt "$SCSI_START" ]] && NEXT_SLOT=$SCSI_START

# ---------------------------------------------------------------------------
# Step 5: Build and run qm commands
# ---------------------------------------------------------------------------
echo ""
info "Attaching disks to VM $VM_ID 👇"
echo ""

ATTACHED_COUNT=0
for dev in "${CANDIDATES[@]}"; do
    # Skip already attached
    if printf '%s\n' "${ALREADY_ATTACHED[@]:-}" | grep -qx "$dev"; then
        continue
    fi

    SLOT="scsi${NEXT_SLOT}"

    # Get the disk's by-id symlink — more stable than /dev/sdX across reboots
    BY_ID=$(ls -1 /dev/disk/by-id/ 2>/dev/null \
            | grep -v "part" \
            | xargs -I{} bash -c \
                'target=$(readlink -f /dev/disk/by-id/{}); \
                 [[ "$target" == "/dev/'"$dev"'" ]] && echo "{}"' \
            | grep -v "wwn-\|dm-\|md-" \
            | head -1 || true)

    if [[ -n "$BY_ID" ]]; then
        DISK_PATH="/dev/disk/by-id/${BY_ID}"
        ID_SOURCE="by-id"
    else
        DISK_PATH="/dev/$dev"
        ID_SOURCE="/dev path (no by-id symlink found)"
    fi

    SIZE=$(lsblk -dno SIZE "/dev/$dev" 2>/dev/null || echo "?")
    ROTA=$(lsblk -dno ROTA "/dev/$dev" 2>/dev/null || echo "?")
    TYPE=$([[ "$ROTA" == "1" ]] && echo "HDD" || echo "SSD/NVMe")

    info "  /dev/$dev  →  VM${VM_ID}:${SLOT}  (${SIZE}, ${TYPE}, path: ${DISK_PATH} [${ID_SOURCE}])"

    run "qm set ${VM_ID} \
        --${SLOT} ${DISK_PATH},backup=0,cache=none,aio=native"

    NEXT_SLOT=$(( NEXT_SLOT + 1 ))
    ATTACHED_COUNT=$(( ATTACHED_COUNT + 1 ))
done

# ---------------------------------------------------------------------------
# Step 6: Enable SCSI controller if not already present
# ---------------------------------------------------------------------------
if ! echo "$CURRENT_CONF" | grep -q "scsihw:"; then
    info "No SCSI controller configured — adding VirtIO-SCSI-single"
    run "qm set ${VM_ID} --scsihw virtio-scsi-single"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
if $DRY_RUN; then
    echo "============================================================"
    echo "  DRY-RUN complete — no changes were made."
    echo "  Review the [DRY-RUN] commands above, then run:"
    echo "    bash $0 --force"
    echo "============================================================"
else
    echo "============================================================"
    echo "  Done. ${ATTACHED_COUNT} disk(s) attached to VM ${VM_ID}."
    echo ""
    echo "  Verify with:"
    echo "    qm config ${VM_ID}"
    echo ""
    echo "  Start the VM:"
    echo "    qm start ${VM_ID}"
    echo ""
    echo "  Inside the VM, confirm disks are visible:"
    echo "    lsblk"
    echo "    ls /dev/disk/by-id/"
    echo ""
    echo "  Then run the archiver setup script:"
    echo "    bash deploy/setup-mxlinux.sh    # or setup-artix.sh"
    echo "============================================================"
fi
