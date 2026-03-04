#!/usr/bin/env bash
# =============================================================================
# deploy/proxmox-attach-disks.sh
# Run on the Proxmox HOST (not inside the VM).
#
# Discovers all physical HDDs/SSDs that are NOT the Proxmox root/boot disk,
# shows full details for each one, asks for per-disk confirmation, then
# passes confirmed disks through to VM 106 as SCSI passthrough devices.
#
# Prerequisites on the Proxmox host:
#   - qm, lsblk, udevadm  (all included in Proxmox VE)
#
# Usage:
#   bash proxmox-attach-disks.sh [--vm-id 106] [--yes-all]
#
# Flags:
#   --vm-id N    Target VM ID (default: 106)
#   --yes-all    Skip per-disk prompts and attach everything automatically
#
# The VM must be shut down before running this script.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
VM_ID=106
YES_ALL=false
SCSI_START=1

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()    { echo -e "\033[1;32m[INFO]\033[0m    $*"; }
warn()    { echo -e "\033[1;33m[WARN]\033[0m    $*"; }
error()   { echo -e "\033[1;31m[ERROR]\033[0m   $*" >&2; exit 1; }
header()  { echo -e "\033[1;36m$*\033[0m"; }
confirm() {
    # confirm <prompt>  → returns 0 (yes) or 1 (no)
    local answer
    while true; do
        read -rp "$1 [y/n]: " answer
        case "${answer,,}" in
            y|yes) return 0 ;;
            n|no)  return 1 ;;
            *) echo "  Please answer y or n." ;;
        esac
    done
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --vm-id)  VM_ID="$2"; shift 2 ;;
        --yes-all) YES_ALL=true; shift ;;
        *) error "Unknown argument: $1" ;;
    esac
done

# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------
[[ $(id -u) -eq 0 ]] || error "This script must be run as root on the Proxmox host."
command -v qm    &>/dev/null || error "'qm' not found — are you on the Proxmox host?"
command -v lsblk &>/dev/null || error "'lsblk' not found."

qm status "$VM_ID" &>/dev/null || error "VM $VM_ID does not exist."

VM_STATUS=$(qm status "$VM_ID" | awk '{print $2}')
if [[ "$VM_STATUS" != "stopped" ]]; then
    error "VM $VM_ID is currently '$VM_STATUS'. Shut it down first:
       qm shutdown $VM_ID"
fi
info "VM $VM_ID is stopped — safe to attach disks."
echo ""

# ---------------------------------------------------------------------------
# Step 1: Identify the Proxmox root disk (excluded from passthrough)
# ---------------------------------------------------------------------------
ROOT_DISK=$(lsblk -no PKNAME "$(findmnt -n -o SOURCE /)" 2>/dev/null \
            || lsblk -no PKNAME "$(df / | tail -1 | awk '{print $1}')" 2>/dev/null \
            || echo "")
ROOT_DISK=$(basename "$ROOT_DISK")
info "Proxmox root disk (will be excluded): ${ROOT_DISK:-unknown}"
echo ""

# ---------------------------------------------------------------------------
# Step 2: Enumerate candidate disks with full detail
# ---------------------------------------------------------------------------
header "════════════════════════════════════════════════════════════════"
header "  Disk Discovery"
header "════════════════════════════════════════════════════════════════"
echo ""

# Collect current VM config once for idempotency checks
CURRENT_CONF=$(qm config "$VM_ID" 2>/dev/null || true)
MAX_SCSI=$(echo "$CURRENT_CONF" | grep -oP 'scsi\K[0-9]+' | sort -n | tail -1 || echo "0")
NEXT_SLOT=$(( MAX_SCSI + 1 ))
[[ "$NEXT_SLOT" -lt "$SCSI_START" ]] && NEXT_SLOT=$SCSI_START

# Arrays built during enumeration
DISK_NAMES=()
DISK_SIZES=()
DISK_TYPES=()
DISK_MODELS=()
DISK_SERIALS=()
DISK_PATHS=()      # by-id or /dev/sdX
DISK_SLOTS=()      # scsi<N> slot assignment
DISK_SKIP=()       # reason to skip, or ""

SLOT_CURSOR=$NEXT_SLOT

while IFS= read -r line; do
    name=$(awk  '{print $1}' <<< "$line")
    size=$(awk  '{print $2}' <<< "$line")
    rota=$(awk  '{print $3}' <<< "$line")
    model=$(awk '{$1=$2=$3=""; print $0}' <<< "$line" | xargs)
    type=$([[ "$rota" == "1" ]] && echo "HDD" || echo "SSD/NVMe")

    serial=$(udevadm info --query=property --name="/dev/$name" 2>/dev/null \
             | grep -m1 ID_SERIAL_SHORT | cut -d= -f2 || echo "unknown")

    wwn=$(udevadm info --query=property --name="/dev/$name" 2>/dev/null \
          | grep -m1 ID_WWN | cut -d= -f2 || echo "")

    # Partitions present?
    parts=$(lsblk -no NAME "/dev/$name" 2>/dev/null | grep -v "^$name$" | wc -l || echo 0)

    # by-id path
    BY_ID=$(ls -1 /dev/disk/by-id/ 2>/dev/null \
            | grep -v "part\|wwn-\|dm-\|md-" \
            | xargs -I{} bash -c \
                'target=$(readlink -f /dev/disk/by-id/{}); \
                 [[ "$target" == "/dev/'"$name"'" ]] && echo "{}"' \
            | head -1 || true)

    if [[ -n "$BY_ID" ]]; then
        disk_path="/dev/disk/by-id/${BY_ID}"
    else
        disk_path="/dev/$name"
    fi

    # Determine skip reason
    skip_reason=""
    if [[ "$name" == "$ROOT_DISK" ]]; then
        skip_reason="Proxmox root disk"
    elif echo "$CURRENT_CONF" | grep -q "$name\|$BY_ID"; then
        skip_reason="already attached to VM $VM_ID"
    fi

    DISK_NAMES+=("$name")
    DISK_SIZES+=("$size")
    DISK_TYPES+=("$type")
    DISK_MODELS+=("${model:-unknown}")
    DISK_SERIALS+=("$serial")
    DISK_PATHS+=("$disk_path")
    DISK_SLOTS+=("scsi${SLOT_CURSOR}")
    DISK_SKIP+=("$skip_reason")

    [[ -z "$skip_reason" ]] && SLOT_CURSOR=$(( SLOT_CURSOR + 1 ))

done < <(lsblk -dno NAME,SIZE,ROTA,MODEL --include 8,259,252 2>/dev/null \
         | grep -v "^loop\|^sr\|^fd")

if [[ ${#DISK_NAMES[@]} -eq 0 ]]; then
    warn "No block devices found."
    exit 0
fi

# ---------------------------------------------------------------------------
# Step 3: Print full summary table of ALL disks
# ---------------------------------------------------------------------------
printf "  %-6s  %-8s  %-8s  %-28s  %-16s  %-10s  %s\n" \
       "DEVICE" "SIZE" "TYPE" "MODEL" "SERIAL" "SCSI SLOT" "STATUS"
printf "  %-6s  %-8s  %-8s  %-28s  %-16s  %-10s  %s\n" \
       "------" "----" "----" "-----" "------" "---------" "------"

for i in "${!DISK_NAMES[@]}"; do
    skip="${DISK_SKIP[$i]}"
    slot="${DISK_SLOTS[$i]}"
    if [[ -n "$skip" ]]; then
        slot="—"
        status="SKIP ($skip)"
        colour="\033[2m"   # dim
    else
        status="will attach → VM${VM_ID}:${slot}"
        colour="\033[0m"
    fi
    printf "${colour}  %-6s  %-8s  %-8s  %-28s  %-16s  %-10s  %s\033[0m\n" \
           "${DISK_NAMES[$i]}" \
           "${DISK_SIZES[$i]}" \
           "${DISK_TYPES[$i]}" \
           "${DISK_MODELS[$i]:0:28}" \
           "${DISK_SERIALS[$i]:0:16}" \
           "$slot" \
           "$status"
done

echo ""

# Check there is anything left to attach
PENDING=()
for i in "${!DISK_NAMES[@]}"; do
    [[ -z "${DISK_SKIP[$i]}" ]] && PENDING+=("$i")
done

if [[ ${#PENDING[@]} -eq 0 ]]; then
    warn "All candidate disks are already attached or excluded. Nothing to do."
    exit 0
fi

# ---------------------------------------------------------------------------
# Step 4: Per-disk confirmation
# ---------------------------------------------------------------------------
header "════════════════════════════════════════════════════════════════"
header "  Per-Disk Confirmation"
header "════════════════════════════════════════════════════════════════"
echo ""

CONFIRMED=()   # indices from DISK_NAMES[] that the user approved

for i in "${PENDING[@]}"; do
    echo -e "\033[1m  Disk:    /dev/${DISK_NAMES[$i]}\033[0m"
    echo    "  Size:    ${DISK_SIZES[$i]}"
    echo    "  Type:    ${DISK_TYPES[$i]}"
    echo    "  Model:   ${DISK_MODELS[$i]}"
    echo    "  Serial:  ${DISK_SERIALS[$i]}"
    echo    "  Path:    ${DISK_PATHS[$i]}"
    echo    "  → Will be attached as VM${VM_ID}:${DISK_SLOTS[$i]}"
    echo    ""

    if $YES_ALL; then
        info "  --yes-all set — auto-confirming."
        CONFIRMED+=("$i")
    else
        if confirm "  Attach /dev/${DISK_NAMES[$i]} to VM ${VM_ID}?"; then
            CONFIRMED+=("$i")
            info "  Confirmed."
        else
            warn "  Skipped by user."
        fi
    fi
    echo ""
done

if [[ ${#CONFIRMED[@]} -eq 0 ]]; then
    warn "No disks confirmed. Nothing was changed."
    exit 0
fi

# ---------------------------------------------------------------------------
# Step 5: Final confirmation — show exactly what will be run
# ---------------------------------------------------------------------------
header "════════════════════════════════════════════════════════════════"
header "  Execution Plan"
header "════════════════════════════════════════════════════════════════"
echo ""

for i in "${CONFIRMED[@]}"; do
    echo "  qm set ${VM_ID} --${DISK_SLOTS[$i]} ${DISK_PATHS[$i]},backup=0,cache=none,aio=native"
done

if ! echo "$CURRENT_CONF" | grep -q "scsihw:"; then
    echo "  qm set ${VM_ID} --scsihw virtio-scsi-single"
fi

echo ""
if ! confirm "Execute the above commands now?"; then
    warn "Aborted — no changes made."
    exit 0
fi

# ---------------------------------------------------------------------------
# Step 6: Execute
# ---------------------------------------------------------------------------
echo ""
header "════════════════════════════════════════════════════════════════"
header "  Attaching Disks"
header "════════════════════════════════════════════════════════════════"
echo ""

ATTACHED_COUNT=0
for i in "${CONFIRMED[@]}"; do
    info "Attaching /dev/${DISK_NAMES[$i]} → VM${VM_ID}:${DISK_SLOTS[$i]}"
    qm set "${VM_ID}" \
        --"${DISK_SLOTS[$i]}" "${DISK_PATHS[$i]},backup=0,cache=none,aio=native"
    info "  ✓ Done"
    ATTACHED_COUNT=$(( ATTACHED_COUNT + 1 ))
done

if ! echo "$CURRENT_CONF" | grep -q "scsihw:"; then
    info "Adding SCSI controller (virtio-scsi-single)"
    qm set "${VM_ID}" --scsihw virtio-scsi-single
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Done. ${ATTACHED_COUNT} disk(s) attached to VM ${VM_ID}."
echo ""
echo "  Verify config:        qm config ${VM_ID}"
echo "  Start VM:             qm start ${VM_ID}"
echo "  Inside VM — confirm:  lsblk"
echo "                        ls /dev/disk/by-id/"
echo "  Then run:             bash deploy/setup-mxlinux.sh"
echo "════════════════════════════════════════════════════════════════"
