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
# Report file — written alongside the script output
# ---------------------------------------------------------------------------
REPORT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORT_FILE="$REPORT_DIR/disk-setup-report-$(date +%Y-%m-%d_%H-%M-%S).md"
REPORT_LINES=()   # accumulated lines, flushed at the end

rpt() {
    # Append a line to the in-memory report buffer (no colour codes)
    REPORT_LINES+=("$*")
}

flush_report() {
    printf '%s\n' "${REPORT_LINES[@]}" > "$REPORT_FILE"
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
TS()    { date '+%H:%M:%S'; }

# Coloured console + plain report
info()  {
    echo -e "\033[1;32m[$(TS) INFO]\033[0m  $*"
    rpt "  ✓ $*"
}
warn()  {
    echo -e "\033[1;33m[$(TS) WARN]\033[0m  $*"
    rpt "  ⚠ $*"
}
error() {
    echo -e "\033[1;31m[$(TS) ERROR]\033[0m $*" >&2
    rpt "  ✗ ERROR: $*"
    flush_report
    exit 1
}
step()  {
    # Section header — bold cyan on console, markdown heading in report
    echo ""
    echo -e "\033[1;36m━━━  $*  ━━━\033[0m"
    echo ""
    rpt ""
    rpt "## $*"
    rpt ""
}
disk_banner() {
    # Per-disk operation header — highly visible
    local disk=$1 role=$2 size=$3
    echo ""
    echo -e "\033[1;45m  ▶  /dev/$disk  ($role, $size)  \033[0m"
    echo ""
    rpt ""
    rpt "### /dev/$disk — $role ($size)"
    rpt ""
}
ok()    {
    echo -e "      \033[1;32m✔\033[0m  $*"
    rpt "  - ✔ $*"
}
run()   {
    # Execute a command, show it, capture and display output
    if $DRY_RUN; then
        echo -e "      \033[1;34m[DRY-RUN]\033[0m $*"
        rpt "  - [DRY-RUN] \`$*\`"
        return
    fi
    echo -e "      \033[2m\$ $*\033[0m"
    rpt "  - \`$*\`"
    eval "$*"
}
run_capture() {
    # Run a command and capture+display its output (for sgdisk verbose info)
    if $DRY_RUN; then
        echo -e "      \033[1;34m[DRY-RUN]\033[0m $*"
        rpt "  - [DRY-RUN] \`$*\`"
        return
    fi
    echo -e "      \033[2m\$ $*\033[0m"
    rpt "  - \`$*\`"
    local out
    out=$(eval "$*" 2>&1) || true
    if [[ -n "$out" ]]; then
        echo "$out" | sed 's/^/        /'
        rpt "\`\`\`"
        echo "$out" >> /dev/null   # already captured
        while IFS= read -r l; do rpt "    $l"; done <<< "$out"
        rpt "\`\`\`"
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
    local disk_bytes size_gib

    disk_bytes=$(lsblk -bdno SIZE "/dev/$disk" 2>/dev/null || echo 0)
    size_gib=$(( disk_bytes / 1024 / 1024 / 1024 ))

    # ── Step A: Zero first 10 MB (MBR + GPT primary header) ──────────────
    echo -e "    \033[33m[1/5]\033[0m  Zeroing first 10 MB of /dev/$disk  (MBR + GPT header)…"
    rpt "  **[1/5] Zero first 10 MB** (MBR / GPT primary header)"
    if ! $DRY_RUN; then
        dd if=/dev/zero of="/dev/$disk" bs=1M count=10 conv=fsync status=progress 2>&1 \
            | tail -1 | sed 's/^/        /'
        rpt "  - \`dd if=/dev/zero of=/dev/$disk bs=1M count=10\` — done"
    else
        echo -e "        \033[2m[DRY-RUN] dd if=/dev/zero of=/dev/$disk bs=1M count=10\033[0m"
        rpt "  - [DRY-RUN] dd zeroing skipped"
    fi
    ok "First 10 MB zeroed"

    # ── Step B: Zero last 10 MB (GPT backup header) ───────────────────────
    echo -e "    \033[33m[2/5]\033[0m  Zeroing last 10 MB of /dev/$disk   (GPT backup header)…"
    rpt "  **[2/5] Zero last 10 MB** (GPT backup header)"
    if [[ "$disk_bytes" -gt 0 ]] && ! $DRY_RUN; then
        local end_offset=$(( disk_bytes / 512 - 20480 ))
        dd if=/dev/zero of="/dev/$disk" bs=512 count=20480 seek="$end_offset" \
           conv=fsync status=none 2>/dev/null || true
        rpt "  - \`dd if=/dev/zero ... seek=$end_offset\` — done"
    else
        echo -e "        \033[2m[DRY-RUN] dd tail-zeroing skipped\033[0m"
        rpt "  - [DRY-RUN] skipped"
    fi
    ok "Last 10 MB zeroed"

    # ── Step C: Zap any remaining GPT/MBR remnants ───────────────────────
    echo -e "    \033[33m[3/5]\033[0m  Zapping all GPT/MBR signatures on /dev/$disk  (sgdisk -Z)…"
    rpt "  **[3/5] sgdisk -Z** — destroy all GPT/MBR structures"
    if ! $DRY_RUN; then
        local zap_out
        zap_out=$(sgdisk -Z "/dev/$disk" 2>&1) || true
        echo "$zap_out" | sed 's/^/        /'
        while IFS= read -r l; do rpt "    $l"; done <<< "$zap_out"
    else
        echo -e "        \033[2m[DRY-RUN] sgdisk -Z /dev/$disk\033[0m"
        rpt "  - [DRY-RUN] sgdisk -Z skipped"
    fi
    ok "GPT/MBR signatures destroyed"

    # ── Step D: Create fresh GPT + single partition ───────────────────────
    echo -e "    \033[33m[4/5]\033[0m  Creating GPT partition table + partition 1 on /dev/$disk…"
    rpt "  **[4/5] Create GPT + partition**"
    rpt "  - Partition: type=8300 (Linux filesystem), spans 100% of disk, label=\`$label\`"
    if ! $DRY_RUN; then
        local gpt_out
        gpt_out=$(sgdisk \
            -n "0:0:0" \
            -t "0:8300" \
            -c "0:$label" \
            "/dev/$disk" 2>&1)
        echo "$gpt_out" | sed 's/^/        /'
        while IFS= read -r l; do rpt "    $l"; done <<< "$gpt_out"

        # Show the resulting partition table
        local pt_out
        pt_out=$(sgdisk -p "/dev/$disk" 2>&1)
        echo ""
        echo "$pt_out" | sed 's/^/        /'
        rpt ""
        rpt "  Partition table after creation:"
        rpt "  \`\`\`"
        while IFS= read -r l; do rpt "    $l"; done <<< "$pt_out"
        rpt "  \`\`\`"
    else
        echo -e "        \033[2m[DRY-RUN] sgdisk -n 0:0:0 -t 0:8300 -c 0:$label /dev/$disk\033[0m"
        rpt "  - [DRY-RUN] sgdisk create partition skipped"
    fi
    ok "GPT created, partition 1 spans full disk, label=$label"

    # ── Step E: Reload partition table in kernel ──────────────────────────
    echo -e "    \033[33m[5/5]\033[0m  Reloading partition table in kernel…"
    rpt "  **[5/5] Reload partition table** (partprobe / blockdev)"
    if ! $DRY_RUN; then
        partprobe "/dev/$disk" 2>/dev/null \
            || blockdev --rereadpt "/dev/$disk" 2>/dev/null \
            || true
        sleep 2   # give udev time to create /dev/sdX1
        # Confirm the partition node exists
        if [[ -b "/dev/${disk}1" ]]; then
            ok "Partition node /dev/${disk}1 confirmed"
            rpt "  - /dev/${disk}1 exists and is a block device ✔"
        else
            warn "/dev/${disk}1 not yet visible — waiting 3 more seconds…"
            sleep 3
            if [[ -b "/dev/${disk}1" ]]; then
                ok "Partition node /dev/${disk}1 confirmed (after extra wait)"
                rpt "  - /dev/${disk}1 visible after extra wait ✔"
            else
                warn "/dev/${disk}1 still not visible — continuing anyway (may fail at mkfs)"
                rpt "  - /dev/${disk}1 NOT YET VISIBLE — check kernel messages"
            fi
        fi
    else
        echo -e "        \033[2m[DRY-RUN] partprobe /dev/$disk\033[0m"
        rpt "  - [DRY-RUN] partprobe skipped"
    fi

    echo ""
    echo -e "    \033[1;32m✔  /dev/$disk  fully wiped and repartitioned → /dev/${disk}1\033[0m"
    rpt ""
    rpt "  **Result:** /dev/${disk}1 ready for ext4 formatting"

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

# ── Report header ─────────────────────────────────────────────────────────
RUN_TIME=$(date '+%Y-%m-%d %H:%M:%S %Z')
HOSTNAME=$(hostname)
rpt "# Disk Setup Report"
rpt ""
rpt "| Field | Value |"
rpt "|-------|-------|"
rpt "| Host | $HOSTNAME |"
rpt "| Run time | $RUN_TIME |"
rpt "| Script | vm-mount-disks.sh |"
rpt "| Mode | $( $WIPE && echo '--wipe (full repartition)' || ( $FORCE_FORMAT && echo '--force-format' || echo 'mount only' ) ) |"
rpt "| Dry run | $DRY_RUN |"
rpt ""
rpt "---"

step "Disk Discovery"
printf "  %-10s %-8s %-10s %-28s %-22s %s\n" \
       "DISK" "SIZE" "SIZE_GiB" "MODEL" "SERIAL" "ROOT?"
printf "  %-10s %-8s %-10s %-28s %-22s %s\n" \
       "----" "----" "--------" "-----" "------" "-----"
rpt "| Device | Size | GiB | Model | Serial | Root? |"
rpt "|--------|------|-----|-------|--------|-------|"

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
    rpt "| /dev/$diskname | $size_h | $size_gib | ${model:--} | ${serial:--} | ${is_root:-no} |"

    # Enumerate partitions for this disk
    while IFS= read -r partname; do
        [[ "$partname" == "$diskname" ]] && continue
        p_fstype=$(blkid -s TYPE  -o value "/dev/$partname" 2>/dev/null || echo "")
        p_uuid=$(blkid   -s UUID  -o value "/dev/$partname" 2>/dev/null || echo "")
        PART_FSTYPE["$partname"]=$p_fstype
        PART_UUID["$partname"]=$p_uuid
    done < <(lsblk -lno NAME "/dev/$diskname" 2>/dev/null)

done < <(lsblk -dno NAME 2>/dev/null | grep -v "^loop\|^sr\|^fd\|^ram")

step "Drive Assignment"

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
step "Proposed Mount Plan"

printf "  %-5s %-10s %-12s %-22s %-14s %s\n" \
       "ROLE" "DISK" "PARTITION" "MOUNT POINT" "CURRENT FS" "ACTION"
printf "  %-5s %-10s %-12s %-22s %-14s %s\n" \
       "----" "----" "---------" "-----------" "----------" "------"
rpt "| Role | Disk | Partition | Mount Point | Current FS | Action |"
rpt "|------|------|-----------|-------------|------------|--------|"

show_row() {
    local role=$1 disk=$2 part=$3 mount=$4
    if [[ -z "$disk" ]]; then
        printf "  %-5s %-10s %-12s %-22s %-14s %s\n" \
            "$role" "(none)" "(none)" "$mount" "—" "SKIPPED"
        rpt "| $role | (none) | (none) | $mount | — | SKIPPED |"
        return
    fi
    local fs action
    if $WIPE; then
        fs="(will wipe)"
        action="zero + GPT + partition + ext4"
    else
        fs=${PART_FSTYPE[$part]:-none}
        if [[ "$fs" == "ext4" ]]; then
            action="mount existing ext4"
        elif [[ -z "$fs" || "$fs" == "none" ]]; then
            $FORCE_FORMAT && action="FORMAT ext4 + mount" || action="NEEDS --force-format"
        else
            action="WARNING: unexpected fs=$fs"
        fi
    fi
    printf "  %-5s %-10s %-12s %-22s %-14s %s\n" \
           "$role" "/dev/$disk" "/dev/$part" "$mount" "$fs" "$action"
    rpt "| $role | /dev/$disk | /dev/$part | $mount | $fs | $action |"
}

show_row "D1" "$DEV_D1" "$PART_D1" "$MOUNT_D1"
show_row "D2" "${DEV_D2:-}" "${PART_D2:-}" "$MOUNT_D2"
show_row "D3" "${DEV_D3:-}" "${PART_D3:-}" "$MOUNT_D3"
show_row "D5" "$DEV_D5" "$PART_D5" "$MOUNT_D5"
echo ""
echo "  .tmp scratch → $MOUNT_D1/.tmp   (~1.9 TB headroom on D1 post-downloads)"
rpt ""
rpt "> .tmp scratch: \`$MOUNT_D1/.tmp\` (~1.9 TB headroom on D1 post-downloads)"

# Check whether any partition needs formatting but --force-format is absent
NEED_FORMAT=false
for p in "$PART_D1" "$PART_D5" ${PART_D2:+$PART_D2} ${PART_D3:+$PART_D3}; do
    fs=${PART_FSTYPE[$p]:-none}
    [[ -z "$fs" || "$fs" == "none" ]] && NEED_FORMAT=true
done

if $NEED_FORMAT && ! $FORCE_FORMAT; then
    echo ""
    echo "  One or more partitions have no filesystem."
    echo "  Re-run with --force-format to create ext4 on them."
    echo "  WARNING: --force-format ERASES all data on unformatted partitions."
    echo ""
    rpt ""
    rpt "> **ABORTED** — partitions need formatting but --force-format not set."
    flush_report
    exit 0
fi

echo ""
if $WIPE; then
    echo -e "  \033[1;31m┌─────────────────────────────────────────────────────────────┐\033[0m"
    echo -e "  \033[1;31m│  ⚠  WARNING — --wipe is set                                  │\033[0m"
    echo -e "  \033[1;31m│  ALL DATA on all four disks will be PERMANENTLY ERASED and   │\033[0m"
    echo -e "  \033[1;31m│  reformatted as ext4. This CANNOT be undone.                 │\033[0m"
    echo -e "  \033[1;31m└─────────────────────────────────────────────────────────────┘\033[0m"
    echo ""
fi

read -rp "  Proceed with the above plan? [y/n]: " answer
if [[ "${answer,,}" != "y" && "${answer,,}" != "yes" ]]; then
    warn "Aborted by user."
    rpt ""
    rpt "> **ABORTED** by user at confirmation prompt."
    flush_report
    exit 0
fi
rpt ""
rpt "> User confirmed: **YES** — proceeding."

# ---------------------------------------------------------------------------
# Step 6: Wipe + Partition + Format
# ---------------------------------------------------------------------------
step "Wipe / Partition / Format"

format_partition() {
    local disk=$1 part=$2 label=$3
    local role=$4 mount=$5
    disk_banner "$disk" "$role" "$(lsblk -dno SIZE /dev/$disk 2>/dev/null || echo '?')"

    if [[ -z "${PART_FSTYPE[$part]+_}" ]]; then
        PART_FSTYPE["$part"]=$(blkid -s TYPE -o value "/dev/$part" 2>/dev/null || echo "")
    fi
    local fs=${PART_FSTYPE[$part]:-none}

    if [[ -z "$fs" || "$fs" == "none" ]]; then
        echo -e "    \033[33m[fmt]\033[0m  Formatting /dev/$part as ext4 (label=$label)…"
        rpt "  **Format ext4**"
        rpt "  - Partition: /dev/$part"
        rpt "  - Label: $label"
        rpt "  - Reserved blocks: 1%"
        if ! $DRY_RUN; then
            # -m 1: 1% reserved blocks  -E lazy_*: faster initial format on large HDDs
            mkfs.ext4 -L "$label" -m 1 \
                -E lazy_itable_init=0,lazy_journal_init=0 \
                "/dev/$part" 2>&1 | sed 's/^/        /'
            PART_UUID["$part"]=$(blkid -s UUID -o value "/dev/$part" 2>/dev/null || echo "")
            ok "ext4 formatted — UUID: ${PART_UUID[$part]}"
            rpt "  - UUID: \`${PART_UUID[$part]}\`"
            rpt "  - Status: ✔ formatted"
        else
            echo -e "        \033[2m[DRY-RUN] mkfs.ext4 -L $label /dev/$part\033[0m"
            rpt "  - [DRY-RUN] mkfs.ext4 skipped"
        fi
    elif [[ "$fs" == "ext4" ]]; then
        info "  /dev/$part already ext4 — skipping format (use --wipe to reformat)"
        rpt "  - Already ext4 — format skipped"
        [[ -z "${PART_UUID[$part]:-}" ]] && \
            PART_UUID["$part"]=$(blkid -s UUID -o value "/dev/$part" 2>/dev/null || echo "")
        rpt "  - UUID: \`${PART_UUID[$part]}\`"
    else
        rpt "  - **ERROR**: unexpected filesystem '$fs'"
        flush_report
        error "/dev/$part has unexpected filesystem '$fs'.
  Re-run with --wipe to fully erase and reformat."
    fi
}

if $WIPE; then
    # Per-disk: banner → zero → sgdisk -Z → sgdisk create → partprobe → mkfs
    PART_D1=$(wipe_and_partition "$DEV_D1" "models-d1")
    format_partition "$DEV_D1" "$PART_D1" "models-d1" "D1 — 6TB raw giants" "$MOUNT_D1"

    PART_D5=$(wipe_and_partition "$DEV_D5" "models-d5")
    format_partition "$DEV_D5" "$PART_D5" "models-d5" "D5 — 1TB archive/logs" "$MOUNT_D5"

    if [[ -n "$DEV_D2" ]]; then
        PART_D2=$(wipe_and_partition "$DEV_D2" "models-d2")
        format_partition "$DEV_D2" "$PART_D2" "models-d2" "D2 — 3TB raw mid-size" "$MOUNT_D2"
    fi
    if [[ -n "$DEV_D3" ]]; then
        PART_D3=$(wipe_and_partition "$DEV_D3" "models-d3")
        format_partition "$DEV_D3" "$PART_D3" "models-d3" "D3 — 3TB GGUF quants" "$MOUNT_D3"
    fi
else
    format_partition "$DEV_D1" "$PART_D1" "models-d1" "D1 — 6TB raw giants"   "$MOUNT_D1"
    format_partition "$DEV_D5" "$PART_D5" "models-d5" "D5 — 1TB archive/logs" "$MOUNT_D5"
    [[ -n "$DEV_D2" ]] && \
        format_partition "$DEV_D2" "$PART_D2" "models-d2" "D2 — 3TB raw mid-size" "$MOUNT_D2"
    [[ -n "$DEV_D3" ]] && \
        format_partition "$DEV_D3" "$PART_D3" "models-d3" "D3 — 3TB GGUF quants"  "$MOUNT_D3"
fi

# ---------------------------------------------------------------------------
# Step 7: Mount
# ---------------------------------------------------------------------------
step "Mounting"
rpt "| Partition | Mount Point | Result |"
rpt "|-----------|-------------|--------|"

do_mount() {
    local part=$1 mp=$2
    if ! $DRY_RUN; then
        mkdir -p "$mp"
    else
        echo -e "        \033[2m[DRY-RUN] mkdir -p $mp\033[0m"
    fi
    if mountpoint -q "$mp" 2>/dev/null; then
        info "  $mp already mounted — skipping"
        rpt "| /dev/$part | $mp | already mounted |"
        return
    fi
    info "  Mounting /dev/$part → $mp"
    if ! $DRY_RUN; then
        mount -o noatime,nodiratime "/dev/$part" "$mp"
        ok "  Mounted"
        rpt "| /dev/$part | $mp | ✔ mounted |"
    else
        echo -e "        \033[2m[DRY-RUN] mount /dev/$part $mp\033[0m"
        rpt "| /dev/$part | $mp | [DRY-RUN] |"
    fi
}

do_mount "$PART_D1" "$MOUNT_D1"
[[ -n "$PART_D2" ]] && do_mount "$PART_D2" "$MOUNT_D2"
[[ -n "$PART_D3" ]] && do_mount "$PART_D3" "$MOUNT_D3"
do_mount "$PART_D5" "$MOUNT_D5"

# ---------------------------------------------------------------------------
# Step 8: Directory structure
# ---------------------------------------------------------------------------
step "Directory Structure"

mk() {
    if ! $DRY_RUN; then mkdir -p "$1"; else echo -e "        \033[2m[DRY-RUN] mkdir -p $1\033[0m"; fi
    ok "  $1"
    rpt "  - \`$1\`"
}

rpt "**D1** — raw model storage + .tmp scratch:"
mk "$MOUNT_D1/raw/.keep"
mk "$MOUNT_D1/.tmp"

if [[ -n "$DEV_D2" ]]; then
    rpt "**D2** — raw mid-size + uncensored:"
    mk "$MOUNT_D2/raw/.keep"
    mk "$MOUNT_D2/uncensored/.keep"
fi

if [[ -n "$DEV_D3" ]]; then
    rpt "**D3** — GGUF quantized:"
    mk "$MOUNT_D3/quantized/.keep"
fi

rpt "**D5** — archive + logs:"
mk "$MOUNT_D5/archive/checksums"
mk "$MOUNT_D5/archive/manifests"
mk "$MOUNT_D5/logs"

# ---------------------------------------------------------------------------
# Step 9: /etc/fstab
# ---------------------------------------------------------------------------
step "/etc/fstab"
rpt "| Mount Point | UUID | Entry added? |"
rpt "|-------------|------|--------------|"

write_fstab() {
    local part=$1 mp=$2
    local uuid=${PART_UUID[$part]:-}
    if [[ -z "$uuid" ]]; then
        warn "  No UUID for /dev/$part ($mp) — skipping fstab entry"
        rpt "| $mp | (none) | ⚠ skipped — no UUID |"
        return
    fi
    local entry="UUID=$uuid  $mp  ext4  noatime,nodiratime,defaults  0  2"
    if grep -qs "$mp" /etc/fstab 2>/dev/null; then
        if grep -qs "$uuid" /etc/fstab 2>/dev/null; then
            info "  $mp already in /etc/fstab with correct UUID"
            rpt "| $mp | \`$uuid\` | already present |"
            return
        else
            info "  Replacing stale /etc/fstab entry for $mp"
            if ! $DRY_RUN; then
                sed -i "\| $mp |d" /etc/fstab
            fi
        fi
    fi
    info "  Adding $mp → UUID=$uuid"
    if ! $DRY_RUN; then
        echo "$entry" >> /etc/fstab
        ok "  Written"
        rpt "| $mp | \`$uuid\` | ✔ added |"
    else
        echo -e "        \033[2m[DRY-RUN] >> /etc/fstab: $entry\033[0m"
        rpt "| $mp | \`$uuid\` | [DRY-RUN] |"
    fi
}

write_fstab "$PART_D1" "$MOUNT_D1"
[[ -n "$PART_D2" ]] && write_fstab "$PART_D2" "$MOUNT_D2"
[[ -n "$PART_D3" ]] && write_fstab "$PART_D3" "$MOUNT_D3"
write_fstab "$PART_D5" "$MOUNT_D5"

# ---------------------------------------------------------------------------
# Step 10: Verify + final summary
# ---------------------------------------------------------------------------
step "Mount Verification"

MOUNT_LIST=("$MOUNT_D1" "$MOUNT_D5")
[[ -n "$DEV_D2" ]] && MOUNT_LIST+=("$MOUNT_D2")
[[ -n "$DEV_D3" ]] && MOUNT_LIST+=("$MOUNT_D3")

rpt "| Mount Point | Size | Used | Free | Use% |"
rpt "|-------------|------|------|------|------|"

if ! $DRY_RUN; then
    df -h "${MOUNT_LIST[@]}" 2>/dev/null \
        | awk 'NR==1 { printf "  %-24s %6s %6s %6s %5s\n","Filesystem",$2,$3,$4,$5; next }
                     { printf "  %-24s %6s %6s %6s %5s\n",$1,$2,$3,$4,$5 }'
    # Add df output to report
    while IFS= read -r mp; do
        read -r fs size used free pct _ < <(df -h "$mp" 2>/dev/null | tail -1)
        rpt "| $mp | $size | $used | $free | $pct |"
    done < <(printf '%s\n' "${MOUNT_LIST[@]}")
else
    echo "  [DRY-RUN] — no mounts to verify"
    rpt "| (dry run) | — | — | — | — |"
fi

# ── Final summary ─────────────────────────────────────────────────────────
FINISH_TIME=$(date '+%Y-%m-%d %H:%M:%S %Z')
echo ""
echo -e "\033[1;32m════════════════════════════════════════════════════════════════\033[0m"
echo -e "\033[1;32m  ✔  All done.\033[0m"
echo ""
echo -e "  \033[1mDisk → Mount summary:\033[0m"
printf "    %-5s  %-10s  %-12s  %-22s  %s\n" "ROLE" "DISK" "PARTITION" "MOUNT" "UUID"
printf "    %-5s  %-10s  %-12s  %-22s  %s\n" "----" "----" "---------" "-----" "----"
printf "    %-5s  %-10s  %-12s  %-22s  %s\n" \
    "D1" "/dev/$DEV_D1" "/dev/$PART_D1" "$MOUNT_D1" "${PART_UUID[$PART_D1]:-?}"
[[ -n "$DEV_D2" ]] && printf "    %-5s  %-10s  %-12s  %-22s  %s\n" \
    "D2" "/dev/$DEV_D2" "/dev/$PART_D2" "$MOUNT_D2" "${PART_UUID[$PART_D2]:-?}"
[[ -n "$DEV_D3" ]] && printf "    %-5s  %-10s  %-12s  %-22s  %s\n" \
    "D3" "/dev/$DEV_D3" "/dev/$PART_D3" "$MOUNT_D3" "${PART_UUID[$PART_D3]:-?}"
printf "    %-5s  %-10s  %-12s  %-22s  %s\n" \
    "D5" "/dev/$DEV_D5" "/dev/$PART_D5" "$MOUNT_D5" "${PART_UUID[$PART_D5]:-?}"
echo ""
echo "  Next: deploy the archiver."
echo "    bash deploy/setup-mxlinux.sh    # MX Linux / Debian"
echo "    bash deploy/setup-artix.sh      # Artix Linux / Arch"
echo ""
echo -e "  Report saved → \033[1m$REPORT_FILE\033[0m"
echo -e "\033[1;32m════════════════════════════════════════════════════════════════\033[0m"

rpt ""
rpt "---"
rpt ""
rpt "## Final Summary"
rpt ""
rpt "| Role | Disk | Partition | Mount | UUID |"
rpt "|------|------|-----------|-------|------|"
rpt "| D1 | /dev/$DEV_D1 | /dev/$PART_D1 | $MOUNT_D1 | \`${PART_UUID[$PART_D1]:-?}\` |"
[[ -n "$DEV_D2" ]] && rpt "| D2 | /dev/$DEV_D2 | /dev/$PART_D2 | $MOUNT_D2 | \`${PART_UUID[$PART_D2]:-?}\` |"
[[ -n "$DEV_D3" ]] && rpt "| D3 | /dev/$DEV_D3 | /dev/$PART_D3 | $MOUNT_D3 | \`${PART_UUID[$PART_D3]:-?}\` |"
rpt "| D5 | /dev/$DEV_D5 | /dev/$PART_D5 | $MOUNT_D5 | \`${PART_UUID[$PART_D5]:-?}\` |"
rpt ""
rpt "Completed: $FINISH_TIME"

flush_report
echo ""
echo "  Report also available at: $REPORT_FILE"
