#!/usr/bin/env bash
# =============================================================================
# deploy/vm-mount-disks.sh
# Run INSIDE the VM (not on the Proxmox host).
#
# Identifies the four passed-through disks and mounts them per the archiver
# storage plan. Three strategies attempted in order:
#
#   1. Serial-number match  (preferred — stable across reboots)
#   2. Capacity match       (fallback — ±20% tolerance)
#   3. Interactive prompt   (last resort — user types device name)
#
# Storage plan (based on confirmed Proxmox disk inventory):
#   D1  6 TB  sda  WD6002FZWX  K8GD7LDD         /mnt/models/d1  raw giants
#   D2  3 TB  sdc  WD30EZRZ    WD-WCC4N7XKD9UC  /mnt/models/d2  raw mid-size + Tier D
#   D3  3 TB  sdd  WD30EFRX    WD-WCC1T1259471  /mnt/models/d3  GGUF quants
#   D5  1 TB  sdb  WD1003FZEX  WD-WCC3F2587126  /mnt/models/d5  archive + logs
#
# .tmp scratch → D1 (/mnt/models/d1/.tmp)  ~1.9 TB headroom post-downloads
#
# Usage:
#   bash vm-mount-disks.sh [OPTIONS]
#
# Flags:
#   --force-format   Format partitions that have no filesystem as ext4.
#                    Partitions that already have ext4 are NOT touched unless
#                    --wipe is also passed.
#   --wipe           DESTRUCTIVE. Wipes the entire disk (partition table + data),
#                    creates a fresh GPT with a single partition spanning the full
#                    disk, then formats it ext4. Use this when drives have stale
#                    data/partitions. Implies --force-format. IRREVERSIBLE.
#   --dry-run        Print all actions without executing them.
#
# Typical first-run with stale disks:
#   sudo bash vm-mount-disks.sh --wipe
#
# Subsequent runs (already formatted, just remount after reboot):
#   sudo bash vm-mount-disks.sh
#
# Run as root inside the VM.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Known disk serials — update these if drives change.
# Source: Proxmox host  lsblk -o NAME,SIZE,MODEL,SERIAL
# ---------------------------------------------------------------------------
SERIAL_D1="K8GD7LDD"           # WD 6TB  WD6002FZWX  → /mnt/models/d1
SERIAL_D2="WD-WCC4N7XKD9UC"    # WD 3TB  WD30EZRZ    → /mnt/models/d2
SERIAL_D3="WD-WCC1T1259471"     # WD 3TB  WD30EFRX    → /mnt/models/d3
SERIAL_D5="WD-WCC3F2587126"     # WD 1TB  WD1003FZEX  → /mnt/models/d5

# ---------------------------------------------------------------------------
# Capacity fallback targets (GiB, ±20% tolerance)
# ---------------------------------------------------------------------------
CAP_D1=5500    # "6 TB"  → matches 4400–6600 GiB
CAP_D2=2750    # "3 TB"  → matches 2200–3300 GiB
CAP_D3=2750
CAP_D5=910     # "1 TB"  → matches  728–1092 GiB
MATCH_TOL=20

# ---------------------------------------------------------------------------
# Mount points
# ---------------------------------------------------------------------------
MOUNT_D1=/mnt/models/d1
MOUNT_D2=/mnt/models/d2
MOUNT_D3=/mnt/models/d3
MOUNT_D5=/mnt/models/d5

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
FORCE_FORMAT=false
WIPE=false
DRY_RUN=false

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { echo -e "\033[1;32m[INFO]\033[0m    $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m    $*"; }
error() { echo -e "\033[1;31m[ERROR]\033[0m   $*" >&2; exit 1; }
run()   {
    if $DRY_RUN; then
        echo -e "\033[1;34m[DRY-RUN]\033[0m $*"
    else
        eval "$*"
    fi
}

in_range() {
    local val=$1 target=$2 tol=${3:-20}
    local low=$(( target - target * tol / 100 ))
    local high=$(( target + target * tol / 100 ))
    [[ "$val" -ge "$low" && "$val" -le "$high" ]]
}

# Return the first partition of a disk (e.g. sda → sda1).
# Returns empty string if no partition exists.
first_partition() {
    local disk=$1
    lsblk -lno NAME "/dev/$disk" 2>/dev/null | grep -v "^${disk}$" | head -1
}

# Wipe disk, create fresh GPT + single partition, return the new partition name.
# Only called when --wipe is active.
wipe_and_partition() {
    local disk=$1 label=$2
    info "  Wiping /dev/$disk — zeroing first/last 10 MB…"
    # Zero the beginning (MBR, GPT header) and end (GPT backup) of the disk
    run "dd if=/dev/zero of='/dev/$disk' bs=1M count=10 status=none"
    local disk_bytes
    disk_bytes=$(lsblk -bdno SIZE "/dev/$disk" 2>/dev/null || echo 0)
    if [[ "$disk_bytes" -gt 0 ]] && ! $DRY_RUN; then
        local end_offset=$(( disk_bytes / 512 - 20480 ))  # 10 MB from end in 512-byte sectors
        dd if=/dev/zero of="/dev/$disk" bs=512 count=20480 seek="$end_offset" status=none 2>/dev/null || true
    fi

    info "  Creating fresh GPT partition table on /dev/$disk…"
    # sgdisk -Z: zap all GPT/MBR structures
    # sgdisk -n 0:0:0: new partition, auto-number, start=first usable, end=last usable
    # sgdisk -t 0:8300: type Linux filesystem
    # sgdisk -c 0:<label>: set partition name
    run "sgdisk -Z '/dev/$disk'"
    run "sgdisk -n 0:0:0 -t 0:8300 -c '0:$label' '/dev/$disk'"

    # Inform the kernel of the new partition table
    run "partprobe '/dev/$disk'" || run "blockdev --rereadpt '/dev/$disk'"
    sleep 1   # give udev a moment to create the device node

    # The new partition is always disk-name + "1" (sgdisk auto-numbers from 1)
    echo "${disk}1"
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --force-format) FORCE_FORMAT=true; shift ;;
        --wipe)         WIPE=true; FORCE_FORMAT=true; shift ;;
        --dry-run)      DRY_RUN=true;      shift ;;
        *) error "Unknown argument: $1" ;;
    esac
done

# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------
[[ $(id -u) -eq 0 ]] || error "Must be run as root."
command -v lsblk     &>/dev/null || error "'lsblk' not found."
command -v blkid     &>/dev/null || error "'blkid' not found."
command -v mkfs.ext4 &>/dev/null || error "'mkfs.ext4' not found — install e2fsprogs."
command -v wipefs    &>/dev/null || error "'wipefs' not found — install util-linux."
command -v sgdisk    &>/dev/null || error "'sgdisk' not found — install gdisk (Debian: apt install gdisk)."

# ---------------------------------------------------------------------------
# Step 1: Enumerate all whole-disk block devices (not partitions, not root)
# ---------------------------------------------------------------------------
ROOT_DISK=$(lsblk -no PKNAME "$(findmnt -n -o SOURCE /)" 2>/dev/null \
            || lsblk -no PKNAME "$(df / | awk 'NR==2{print $1}')" 2>/dev/null \
            || echo "")
ROOT_DISK=$(basename "${ROOT_DISK:-}")

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Disk Discovery"
echo "════════════════════════════════════════════════════════════════"
echo ""
printf "  %-10s %-8s %-10s %-28s %-22s %s\n" \
       "DISK" "SIZE" "SIZE_GiB" "MODEL" "SERIAL" "ROOT?"
printf "  %-10s %-8s %-10s %-28s %-22s %s\n" \
       "----" "----" "--------" "-----" "------" "-----"

declare -A DISK_SIZE_GIB   # disk name → size in GiB
declare -A DISK_SERIAL     # disk name → serial number
declare -A PART_FSTYPE     # partition name → fstype
declare -A PART_UUID       # partition name → UUID
DISK_LIST=()

while IFS= read -r diskname; do
    [[ -z "$diskname" ]] && continue
    size_b=$(lsblk -bdno SIZE "/dev/$diskname" 2>/dev/null || echo 0)
    size_gib=$(( size_b / 1024 / 1024 / 1024 ))
    size_h=$(lsblk -dno SIZE "/dev/$diskname" 2>/dev/null || echo "?")
    model=$(lsblk -dno MODEL "/dev/$diskname" 2>/dev/null | xargs || echo "")
    serial=$(lsblk -dno SERIAL "/dev/$diskname" 2>/dev/null | xargs || echo "")
    # lsblk may not have SERIAL column on older kernels — fall back to udevadm
    if [[ -z "$serial" ]]; then
        serial=$(udevadm info --query=property --name="/dev/$diskname" 2>/dev/null \
                 | grep ID_SERIAL_SHORT | cut -d= -f2 || echo "")
    fi

    DISK_SIZE_GIB["$diskname"]=$size_gib
    DISK_SERIAL["$diskname"]=$serial
    DISK_LIST+=("$diskname")

    is_root=""
    [[ "$diskname" == "$ROOT_DISK" ]] && is_root="← ROOT (skip)"

    printf "  %-10s %-8s %-10s %-28s %-22s %s\n" \
           "/dev/$diskname" "$size_h" "$size_gib" "${model:--}" "${serial:--}" "$is_root"

    # Enumerate partitions for this disk
    while IFS= read -r partname; do
        [[ "$partname" == "$diskname" ]] && continue
        p_fstype=$(blkid -s TYPE  -o value "/dev/$partname" 2>/dev/null || echo "")
        p_uuid=$(blkid   -s UUID  -o value "/dev/$partname" 2>/dev/null || echo "")
        PART_FSTYPE["$partname"]=$p_fstype
        PART_UUID["$partname"]=$p_uuid
    done < <(lsblk -lno NAME "/dev/$diskname" 2>/dev/null)

done < <(lsblk -dno NAME 2>/dev/null | grep -v "^loop\|^sr\|^fd\|^ram")

echo ""

# ---------------------------------------------------------------------------
# Step 2: Match disks to roles — serial first, capacity fallback
# ---------------------------------------------------------------------------
echo "════════════════════════════════════════════════════════════════"
echo "  Drive Assignment"
echo "════════════════════════════════════════════════════════════════"
echo ""

DEV_D1="" DEV_D2="" DEV_D3="" DEV_D5=""

assign_by_serial() {
    local target_serial=$1 role=$2 varname=$3
    for disk in "${DISK_LIST[@]}"; do
        [[ "$disk" == "$ROOT_DISK" ]] && continue
        if [[ "${DISK_SERIAL[$disk]:-}" == "$target_serial" ]]; then
            eval "$varname=$disk"
            info "  /dev/$disk  serial=$target_serial  → $role  [serial match]"
            return 0
        fi
    done
    return 1
}

assign_by_serial "$SERIAL_D1" "D1 (6 TB, raw giants)"           DEV_D1 || true
assign_by_serial "$SERIAL_D5" "D5 (1 TB, archive/logs)"         DEV_D5 || true
assign_by_serial "$SERIAL_D2" "D2 (3 TB, raw mid-size + Tier D)" DEV_D2 || true
assign_by_serial "$SERIAL_D3" "D3 (3 TB, GGUF quants)"          DEV_D3 || true

# Capacity-based fallback for any drive not matched by serial
THREE_TB_CAP=()
for disk in "${DISK_LIST[@]}"; do
    [[ "$disk" == "$ROOT_DISK" ]]  && continue
    [[ "$disk" == "${DEV_D1:-}" ]] && continue
    [[ "$disk" == "${DEV_D2:-}" ]] && continue
    [[ "$disk" == "${DEV_D3:-}" ]] && continue
    [[ "$disk" == "${DEV_D5:-}" ]] && continue

    gib=${DISK_SIZE_GIB[$disk]}
    if [[ -z "$DEV_D1" ]] && in_range "$gib" "$CAP_D1" "$MATCH_TOL"; then
        DEV_D1="$disk"
        warn "  /dev/$disk  ${gib} GiB  → D1 [capacity fallback — serial not matched]"
    elif [[ -z "$DEV_D5" ]] && in_range "$gib" "$CAP_D5" "$MATCH_TOL"; then
        DEV_D5="$disk"
        warn "  /dev/$disk  ${gib} GiB  → D5 [capacity fallback]"
    elif in_range "$gib" "$CAP_D2" "$MATCH_TOL"; then
        THREE_TB_CAP+=("$disk")
        warn "  /dev/$disk  ${gib} GiB  → 3 TB pool [capacity fallback]"
    fi
done

# Assign remaining 3 TB drives as D2/D3 if not already set
IFS=$'\n' THREE_TB_SORTED=($(sort <<<"${THREE_TB_CAP[*]:-}")); unset IFS
for disk in "${THREE_TB_SORTED[@]:-}"; do
    if [[ -z "$DEV_D2" ]]; then
        DEV_D2="$disk"
        warn "  /dev/$disk → D2 [capacity fallback]"
    elif [[ -z "$DEV_D3" ]]; then
        DEV_D3="$disk"
        warn "  /dev/$disk → D3 [capacity fallback]"
    fi
done

echo ""

# ---------------------------------------------------------------------------
# Step 3: Interactive fallback for any still-unassigned drives
# ---------------------------------------------------------------------------
AVAIL_UNASSIGNED=()
for disk in "${DISK_LIST[@]}"; do
    [[ "$disk" == "$ROOT_DISK" ]]  && continue
    [[ "$disk" == "${DEV_D1:-}" ]] && continue
    [[ "$disk" == "${DEV_D2:-}" ]] && continue
    [[ "$disk" == "${DEV_D3:-}" ]] && continue
    [[ "$disk" == "${DEV_D5:-}" ]] && continue
    AVAIL_UNASSIGNED+=("/dev/$disk (${DISK_SIZE_GIB[$disk]} GiB, serial=${DISK_SERIAL[$disk]:-?})")
done

prompt_for_drive() {
    local role=$1 varname=$2
    warn "Could not auto-identify $role (serial not found, capacity ambiguous)."
    if [[ ${#AVAIL_UNASSIGNED[@]} -gt 0 ]]; then
        echo "  Unassigned devices:"
        printf "    %s\n" "${AVAIL_UNASSIGNED[@]}"
    fi
    echo "  Full disk list:"
    lsblk -dno NAME,SIZE,MODEL,SERIAL 2>/dev/null | grep -v "^loop\|^sr\|^fd" | sed 's/^/    /'
    read -rp "  Enter device name for $role (e.g. sdb) — blank to skip: " chosen
    if [[ -n "$chosen" ]]; then
        chosen=$(basename "$chosen")
        eval "$varname=$chosen"
        # Populate size/serial if not already cached
        if [[ -z "${DISK_SIZE_GIB[$chosen]+_}" ]]; then
            size_b=$(lsblk -bdno SIZE "/dev/$chosen" 2>/dev/null || echo 0)
            DISK_SIZE_GIB["$chosen"]=$(( size_b / 1024 / 1024 / 1024 ))
        fi
        # Populate partitions
        while IFS= read -r p; do
            [[ "$p" == "$chosen" ]] && continue
            PART_FSTYPE["$p"]=$(blkid -s TYPE -o value "/dev/$p" 2>/dev/null || echo "")
            PART_UUID["$p"]=$(blkid   -s UUID -o value "/dev/$p" 2>/dev/null || echo "")
        done < <(lsblk -lno NAME "/dev/$chosen" 2>/dev/null)
        info "  Manually assigned /dev/$chosen → $role"
    else
        warn "  Skipping $role."
    fi
}

[[ -z "$DEV_D1" ]] && prompt_for_drive "D1 (6 TB — raw giants + .tmp scratch)" DEV_D1
[[ -z "$DEV_D2" ]] && prompt_for_drive "D2 (3 TB — raw mid-size + Tier D)"     DEV_D2
[[ -z "$DEV_D3" ]] && prompt_for_drive "D3 (3 TB — GGUF quants)"               DEV_D3
[[ -z "$DEV_D5" ]] && prompt_for_drive "D5 (1 TB — archive + logs)"            DEV_D5

# D1 and D5 are hard-required
MISSING=()
[[ -z "$DEV_D1" ]] && MISSING+=("D1 (6 TB — raw model storage + .tmp scratch)")
[[ -z "$DEV_D5" ]] && MISSING+=("D5 (1 TB — archive / logs / run_state)")
if [[ ${#MISSING[@]} -gt 0 ]]; then
    error "Required drives not identified: ${MISSING[*]}
  Run: lsblk -o NAME,SIZE,MODEL,SERIAL  to inspect available disks."
fi

# ---------------------------------------------------------------------------
# Step 4: Resolve the partition to actually format/mount for each disk
# ---------------------------------------------------------------------------
# When --wipe: blow away old partition table, create fresh GPT + partition 1.
# Otherwise: use the existing first partition (sda1 etc.), or the disk itself
#            if no partition exists yet.

resolve_partition() {
    local disk=$1 label=$2
    if $WIPE; then
        # wipe_and_partition runs after the confirmation prompt (Step 5).
        # Here we just compute what the new partition name will be.
        echo "${disk}1"
    else
        local p
        p=$(first_partition "$disk")
        if [[ -z "$p" ]]; then
            # No partition found — use the raw disk (unusual but handled)
            echo "$disk"
        else
            echo "$p"
        fi
    fi
}

PART_D1=$(resolve_partition "$DEV_D1" "models-d1")
PART_D5=$(resolve_partition "$DEV_D5" "models-d5")
PART_D2=$( [[ -n "$DEV_D2" ]] && resolve_partition "$DEV_D2" "models-d2" || echo "")
PART_D3=$( [[ -n "$DEV_D3" ]] && resolve_partition "$DEV_D3" "models-d3" || echo "")

# Pre-populate fstype/UUID for existing partitions (skip when --wipe since they'll be recreated)
if ! $WIPE; then
    for p in "$PART_D1" "$PART_D5" ${PART_D2:+$PART_D2} ${PART_D3:+$PART_D3}; do
        if [[ -z "${PART_FSTYPE[$p]+_}" ]]; then
            PART_FSTYPE["$p"]=$(blkid -s TYPE -o value "/dev/$p" 2>/dev/null || echo "")
            PART_UUID["$p"]=$(blkid   -s UUID -o value "/dev/$p" 2>/dev/null || echo "")
        fi
    done
fi

# ---------------------------------------------------------------------------
# Step 5: Show the plan and confirm
# ---------------------------------------------------------------------------
echo "════════════════════════════════════════════════════════════════"
echo "  Proposed Mount Plan"
echo "════════════════════════════════════════════════════════════════"
echo ""
printf "  %-5s %-8s %-12s %-22s %-12s %s\n" \
       "ROLE" "DISK" "PARTITION" "MOUNT POINT" "CURRENT FS" "ACTION"
printf "  %-5s %-8s %-12s %-22s %-12s %s\n" \
       "----" "----" "---------" "-----------" "----------" "------"

show_row() {
    local role=$1 disk=$2 part=$3 mount=$4
    [[ -z "$disk" ]] && { printf "  %-5s %-8s %-12s %-22s %-12s %s\n" \
        "$role" "(none)" "(none)" "$mount" "—" "SKIPPED"; return; }
    local fs action
    if $WIPE; then
        fs="(will wipe)"
        action="zero + GPT + new partition + ext4"
    else
        fs=${PART_FSTYPE[$part]:-none}
        if [[ "$fs" == "ext4" ]]; then
            action="mount existing ext4 (use --wipe to reformat)"
        elif [[ -z "$fs" || "$fs" == "none" ]]; then
            $FORCE_FORMAT && action="FORMAT ext4 + mount" || action="NEEDS --force-format"
        else
            action="WARNING: unexpected fs=$fs — use --wipe to overwrite"
        fi
    fi
    printf "  %-5s %-8s %-12s %-22s %-12s %s\n" \
           "$role" "/dev/$disk" "/dev/$part" "$mount" "$fs" "$action"
}

show_row "D1" "$DEV_D1" "$PART_D1" "$MOUNT_D1"
show_row "D2" "${DEV_D2:-}" "${PART_D2:-}" "$MOUNT_D2"
show_row "D3" "${DEV_D3:-}" "${PART_D3:-}" "$MOUNT_D3"
show_row "D5" "$DEV_D5" "$PART_D5" "$MOUNT_D5"
echo ""
echo "  .tmp scratch → $MOUNT_D1/.tmp   (~1.9 TB headroom on D1 post-downloads)"
echo ""

# Check whether any partition needs formatting but --force-format is absent
NEED_FORMAT=false
for p in "$PART_D1" "$PART_D5" ${PART_D2:+$PART_D2} ${PART_D3:+$PART_D3}; do
    fs=${PART_FSTYPE[$p]:-none}
    [[ -z "$fs" || "$fs" == "none" ]] && NEED_FORMAT=true
done

if $NEED_FORMAT && ! $FORCE_FORMAT; then
    echo "  One or more partitions have no filesystem."
    echo "  Re-run with --force-format to create ext4 on them."
    echo "  WARNING: --force-format ERASES all data on unformatted partitions."
    echo ""
    exit 0
fi

if $WIPE; then
    echo ""
    echo "  ┌─────────────────────────────────────────────────────────┐"
    echo "  │  ⚠  WARNING — --wipe flag is set                        │"
    echo "  │  ALL DATA on the four partitions will be PERMANENTLY     │"
    echo "  │  ERASED and reformatted as ext4. This cannot be undone. │"
    echo "  └─────────────────────────────────────────────────────────┘"
    echo ""
fi

read -rp "  Proceed with the above plan? [y/n]: " answer
[[ "${answer,,}" == "y" || "${answer,,}" == "yes" ]] || { warn "Aborted."; exit 0; }

# ---------------------------------------------------------------------------
# Step 6: Format partitions that need it
# ---------------------------------------------------------------------------
format_partition() {
    local part=$1 label=$2
    local fs=${PART_FSTYPE[$part]:-none}

    if [[ -z "$fs" || "$fs" == "none" ]]; then
        if $FORCE_FORMAT; then
            info "Formatting /dev/$part as ext4 (label=$label)…"
            # -m 1: reserve 1% for root (not root-reserved, just less wasted space)
            # -E lazy_*: skip slow inode table initialisation on first mkfs of large HDD
            run "mkfs.ext4 -L '$label' -m 1 \
                 -E lazy_itable_init=0,lazy_journal_init=0 '/dev/$part'"
            PART_UUID["$part"]=$(blkid -s UUID -o value "/dev/$part" 2>/dev/null || echo "")
            info "  UUID: ${PART_UUID[$part]:-unknown}"
        fi
    elif [[ "$fs" == "ext4" ]]; then
        info "/dev/$part already ext4 — skipping format (use --wipe to reformat)"
        [[ -z "${PART_UUID[$part]:-}" ]] && \
            PART_UUID["$part"]=$(blkid -s UUID -o value "/dev/$part" 2>/dev/null || echo "")
    else
        error "/dev/$part has unexpected filesystem '$fs' — aborting to avoid data loss.
  Re-run with --wipe to fully erase and reformat."
    fi
}

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Partitioning + Formatting"
echo "════════════════════════════════════════════════════════════════"
echo ""

if $WIPE; then
    # Wipe and repartition each raw disk first, then update PART_* vars
    # with the freshly created partition names before mkfs runs.
    PART_D1=$(wipe_and_partition "$DEV_D1" "models-d1")
    PART_D5=$(wipe_and_partition "$DEV_D5" "models-d5")
    [[ -n "$DEV_D2" ]] && PART_D2=$(wipe_and_partition "$DEV_D2" "models-d2")
    [[ -n "$DEV_D3" ]] && PART_D3=$(wipe_and_partition "$DEV_D3" "models-d3")
    # Reset fstype so format_partition proceeds unconditionally
    for p in "$PART_D1" "$PART_D5" ${PART_D2:+$PART_D2} ${PART_D3:+$PART_D3}; do
        PART_FSTYPE["$p"]="none"
        PART_UUID["$p"]=""
    done
fi

format_partition "$PART_D1" "models-d1"
[[ -n "$PART_D2" ]] && format_partition "$PART_D2" "models-d2"
[[ -n "$PART_D3" ]] && format_partition "$PART_D3" "models-d3"
format_partition "$PART_D5" "models-d5"

# ---------------------------------------------------------------------------
# Step 7: Create mount points and mount
# ---------------------------------------------------------------------------
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Mounting"
echo "════════════════════════════════════════════════════════════════"
echo ""

do_mount() {
    local part=$1 mp=$2
    run "mkdir -p '$mp'"
    if mountpoint -q "$mp" 2>/dev/null; then
        info "  $mp already mounted — skipping"
        return
    fi
    info "  /dev/$part → $mp"
    run "mount -o noatime,nodiratime '/dev/$part' '$mp'"
}

do_mount "$PART_D1" "$MOUNT_D1"
[[ -n "$PART_D2" ]] && do_mount "$PART_D2" "$MOUNT_D2"
[[ -n "$PART_D3" ]] && do_mount "$PART_D3" "$MOUNT_D3"
do_mount "$PART_D5" "$MOUNT_D5"

# ---------------------------------------------------------------------------
# Step 8: Create directory structure
# ---------------------------------------------------------------------------
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Directory Structure"
echo "════════════════════════════════════════════════════════════════"
echo ""

run "mkdir -p '$MOUNT_D1/raw/.keep' '$MOUNT_D1/.tmp'"
info "  D1: raw/  .tmp/"

if [[ -n "$DEV_D2" ]]; then
    run "mkdir -p '$MOUNT_D2/raw/.keep' '$MOUNT_D2/uncensored/.keep'"
    info "  D2: raw/  uncensored/"
fi

if [[ -n "$DEV_D3" ]]; then
    run "mkdir -p '$MOUNT_D3/quantized/.keep'"
    info "  D3: quantized/"
fi

run "mkdir -p '$MOUNT_D5/archive/checksums' '$MOUNT_D5/archive/manifests' '$MOUNT_D5/logs'"
info "  D5: archive/  logs/"

# ---------------------------------------------------------------------------
# Step 9: Write /etc/fstab entries (UUID-based, idempotent)
# ---------------------------------------------------------------------------
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  /etc/fstab"
echo "════════════════════════════════════════════════════════════════"
echo ""

write_fstab() {
    local part=$1 mp=$2
    local uuid=${PART_UUID[$part]:-}
    if [[ -z "$uuid" ]]; then
        warn "  No UUID for /dev/$part ($mp) — skipping fstab entry"
        return
    fi
    local entry="UUID=$uuid  $mp  ext4  noatime,nodiratime,defaults  0  2"
    # Remove any pre-existing line for this mount point (stale UUID after --wipe)
    if grep -qs "$mp" /etc/fstab 2>/dev/null; then
        if grep -qs "$uuid" /etc/fstab 2>/dev/null; then
            info "  $mp already in /etc/fstab with correct UUID — skipping"
            return
        else
            info "  Replacing stale /etc/fstab entry for $mp…"
            if ! $DRY_RUN; then
                # Remove old line(s) for this mount point
                sed -i "\| $mp |d" /etc/fstab
            else
                echo -e "\033[1;34m[DRY-RUN]\033[0m  sed -i remove old entry for $mp"
            fi
        fi
    fi
    info "  Adding: $entry"
    if ! $DRY_RUN; then
        echo "$entry" >> /etc/fstab
    else
        echo -e "\033[1;34m[DRY-RUN]\033[0m  >> /etc/fstab: $entry"
    fi
}

write_fstab "$PART_D1" "$MOUNT_D1"
[[ -n "$PART_D2" ]] && write_fstab "$PART_D2" "$MOUNT_D2"
[[ -n "$PART_D3" ]] && write_fstab "$PART_D3" "$MOUNT_D3"
write_fstab "$PART_D5" "$MOUNT_D5"

# ---------------------------------------------------------------------------
# Step 10: Verify
# ---------------------------------------------------------------------------
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Mount Verification"
echo "════════════════════════════════════════════════════════════════"
echo ""

MOUNT_LIST=("$MOUNT_D1" "$MOUNT_D5")
[[ -n "$DEV_D2" ]] && MOUNT_LIST+=("$MOUNT_D2")
[[ -n "$DEV_D3" ]] && MOUNT_LIST+=("$MOUNT_D3")

df -h "${MOUNT_LIST[@]}" 2>/dev/null \
    | awk 'NR==1 { printf "  %-24s %6s %6s %6s %5s %s\n",$1,$2,$3,$4,$5,$6; next }
                 { printf "  %-24s %6s %6s %6s %5s %s\n",$1,$2,$3,$4,$5,$6 }'

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Done."
echo ""
echo "  Mounts active and written to /etc/fstab."
echo ""
echo "  Summary of assigned serials (for reference):"
printf "    D1 %-12s → %s\n" "$SERIAL_D1" "$MOUNT_D1"
printf "    D2 %-12s → %s\n" "$SERIAL_D2" "${MOUNT_D2:-skipped}"
printf "    D3 %-12s → %s\n" "$SERIAL_D3" "${MOUNT_D3:-skipped}"
printf "    D5 %-12s → %s\n" "$SERIAL_D5" "$MOUNT_D5"
echo ""
echo "  Next: deploy the archiver on this VM."
echo "    bash deploy/setup-mxlinux.sh    # MX Linux / Debian"
echo "    bash deploy/setup-artix.sh      # Artix Linux / Arch"
echo "════════════════════════════════════════════════════════════════"
