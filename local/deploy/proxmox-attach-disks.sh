#!/usr/bin/env bash
# =============================================================================
# deploy/proxmox-attach-disks.sh
# Run on the Proxmox HOST (not inside the VM).
#
# Discovers all physical HDDs/SSDs that are NOT the Proxmox root/boot disk,
# shows full details for each, asks for per-disk confirmation, then passes
# confirmed disks through to a target VM as SCSI passthrough devices.
#
# Prerequisites (all present on a standard Proxmox VE host):
#   qm, lsblk, udevadm
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
VM_ID=106
YES_ALL=false
SCSI_START=1

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --vm-id)   VM_ID="$2"; shift 2 ;;
        --yes-all) YES_ALL=true; shift ;;
        *) error "Unknown argument: $1" ;;
    esac
done

# ---------------------------------------------------------------------------
# Initialise report
# ---------------------------------------------------------------------------
init_report "proxmox-attach-disks"
_rpt "| Target VM | $VM_ID |"
_rpt "| --yes-all | $YES_ALL |"
_rpt ""

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------
step "Pre-flight Checks"

[[ $(id -u) -eq 0 ]] || error "Must be run as root on the Proxmox host."
ok "Running as root"

command -v qm     &>/dev/null || error "'qm' not found — run this on the Proxmox host."
command -v lsblk  &>/dev/null || error "'lsblk' not found."
command -v udevadm &>/dev/null || error "'udevadm' not found."
ok "qm, lsblk, udevadm available"

qm status "$VM_ID" &>/dev/null || error "VM $VM_ID does not exist. Check --vm-id."

VM_STATUS=$(qm status "$VM_ID" | awk '{print $2}')
if [[ "$VM_STATUS" != "stopped" ]]; then
    error "VM $VM_ID is currently '$VM_STATUS'. Shut it down first:
       qm shutdown $VM_ID"
fi
ok "VM $VM_ID exists and is stopped"
_rpt "| VM $VM_ID status | stopped ✔ |"

# ---------------------------------------------------------------------------
# Step 1: Identify Proxmox root disk
# ---------------------------------------------------------------------------
step "1 — Identify Proxmox Root Disk (excluded from passthrough)"

ROOT_DISK=$(lsblk -no PKNAME "$(findmnt -n -o SOURCE /)" 2>/dev/null \
            || lsblk -no PKNAME "$(df / | awk 'NR==2{print $1}')" 2>/dev/null \
            || echo "")
ROOT_DISK=$(basename "${ROOT_DISK:-}")

ROOT_MODEL=$(lsblk -dno MODEL "/dev/$ROOT_DISK" 2>/dev/null | xargs || echo "unknown")
ROOT_SIZE=$(lsblk -dno SIZE "/dev/$ROOT_DISK" 2>/dev/null || echo "?")
ROOT_SERIAL=$(udevadm info --query=property --name="/dev/$ROOT_DISK" 2>/dev/null \
              | grep -m1 ID_SERIAL_SHORT | cut -d= -f2 || echo "unknown")

info "Proxmox root disk: /dev/$ROOT_DISK  ($ROOT_SIZE, $ROOT_MODEL, s/n $ROOT_SERIAL)"
ok "Root disk identified — will be excluded"
_rpt "| Root disk | /dev/$ROOT_DISK |"
_rpt "| Root model | $ROOT_MODEL |"
_rpt "| Root size | $ROOT_SIZE |"
_rpt "| Root serial | $ROOT_SERIAL |"

# ---------------------------------------------------------------------------
# Step 2: Enumerate candidate disks
# ---------------------------------------------------------------------------
step "2 — Disk Discovery"

CURRENT_CONF=$(qm config "$VM_ID" 2>/dev/null || true)
MAX_SCSI=$(echo "$CURRENT_CONF" | grep -oP 'scsi\K[0-9]+' | sort -n | tail -1 2>/dev/null || echo "0")
NEXT_SLOT=$(( MAX_SCSI + 1 ))
[[ "$NEXT_SLOT" -lt "$SCSI_START" ]] && NEXT_SLOT=$SCSI_START

DISK_NAMES=()
DISK_SIZES=()
DISK_TYPES=()
DISK_MODELS=()
DISK_SERIALS=()
DISK_WWNS=()
DISK_PATHS=()
DISK_SLOTS=()
DISK_SKIP=()
DISK_PARTS=()

SLOT_CURSOR=$NEXT_SLOT

while IFS= read -r line; do
    name=$(awk  '{print $1}' <<< "$line")
    size=$(awk  '{print $2}' <<< "$line")
    rota=$(awk  '{print $3}' <<< "$line")
    model=$(awk '{$1=$2=$3=""; print $0}' <<< "$line" | xargs)
    type=$([[ "$rota" == "1" ]] && echo "HDD" || echo "SSD/NVMe")

    serial=$(udevadm info --query=property --name="/dev/$name" 2>/dev/null \
             | grep -m1 ID_SERIAL_SHORT | cut -d= -f2 || echo "")
    wwn=$(udevadm info --query=property --name="/dev/$name" 2>/dev/null \
          | grep -m1 ID_WWN | cut -d= -f2 || echo "")
    parts=$(lsblk -no NAME "/dev/$name" 2>/dev/null | grep -vc "^${name}$" || echo 0)

    BY_ID=$(ls -1 /dev/disk/by-id/ 2>/dev/null \
            | grep -v "part\|wwn-\|dm-\|md-" \
            | while read -r id; do
                target=$(readlink -f "/dev/disk/by-id/$id" 2>/dev/null || true)
                [[ "$target" == "/dev/$name" ]] && echo "$id" && break
              done | head -1 || true)

    disk_path=$([[ -n "$BY_ID" ]] && echo "/dev/disk/by-id/$BY_ID" || echo "/dev/$name")

    skip_reason=""
    if [[ "$name" == "$ROOT_DISK" ]]; then
        skip_reason="Proxmox root disk"
    elif echo "$CURRENT_CONF" | grep -qF "$name"; then
        skip_reason="already attached to VM $VM_ID"
    elif [[ -n "$BY_ID" ]] && echo "$CURRENT_CONF" | grep -qF "$BY_ID"; then
        skip_reason="already attached to VM $VM_ID (by-id)"
    fi

    DISK_NAMES+=("$name")
    DISK_SIZES+=("$size")
    DISK_TYPES+=("$type")
    DISK_MODELS+=("${model:-unknown}")
    DISK_SERIALS+=("${serial:-unknown}")
    DISK_WWNS+=("${wwn:-}")
    DISK_PATHS+=("$disk_path")
    DISK_SLOTS+=("scsi${SLOT_CURSOR}")
    DISK_SKIP+=("$skip_reason")
    DISK_PARTS+=("$parts")

    [[ -z "$skip_reason" ]] && SLOT_CURSOR=$(( SLOT_CURSOR + 1 ))

done < <(lsblk -dno NAME,SIZE,ROTA,MODEL --include 8,259,252 2>/dev/null \
         | grep -v "^loop\|^sr\|^fd")

if [[ ${#DISK_NAMES[@]} -eq 0 ]]; then
    warn "No block devices found."
    finish_report "NO DISKS FOUND"
    print_report_path
    exit 0
fi

# Print summary table
printf "\n"
printf "  %-8s  %-7s  %-8s  %-26s  %-18s  %-6s  %-10s  %s\n" \
       "DEVICE" "SIZE" "TYPE" "MODEL" "SERIAL" "PARTS" "SCSI SLOT" "STATUS"
printf "  %-8s  %-7s  %-8s  %-26s  %-18s  %-6s  %-10s  %s\n" \
       "--------" "-------" "--------" "--------------------------" \
       "------------------" "------" "----------" "------"

_rpt "| Device | Size | Type | Model | Serial | Parts | SCSI Slot | Status |"
_rpt "|--------|------|------|-------|--------|-------|-----------|--------|"

for i in "${!DISK_NAMES[@]}"; do
    skip="${DISK_SKIP[$i]}"
    slot="${DISK_SLOTS[$i]}"
    if [[ -n "$skip" ]]; then
        slot="—"
        status="SKIP ($skip)"
        colour="${_C_DIM}"
    else
        status="→ VM${VM_ID}:${slot}"
        colour="${_C_RESET}"
    fi
    printf "${colour}  %-8s  %-7s  %-8s  %-26s  %-18s  %-6s  %-10s  %s${_C_RESET}\n" \
           "/dev/${DISK_NAMES[$i]}" \
           "${DISK_SIZES[$i]}" \
           "${DISK_TYPES[$i]}" \
           "${DISK_MODELS[$i]:0:26}" \
           "${DISK_SERIALS[$i]:0:18}" \
           "${DISK_PARTS[$i]}" \
           "$slot" \
           "$status"
    _rpt "| /dev/${DISK_NAMES[$i]} | ${DISK_SIZES[$i]} | ${DISK_TYPES[$i]} | ${DISK_MODELS[$i]} | ${DISK_SERIALS[$i]} | ${DISK_PARTS[$i]} | $slot | $status |"
done

echo ""

PENDING=()
for i in "${!DISK_NAMES[@]}"; do
    [[ -z "${DISK_SKIP[$i]}" ]] && PENDING+=("$i")
done

if [[ ${#PENDING[@]} -eq 0 ]]; then
    warn "All candidate disks are already attached or excluded. Nothing to do."
    finish_report "NOTHING TO DO"
    print_report_path
    exit 0
fi

# ---------------------------------------------------------------------------
# Step 3: Per-disk confirmation
# ---------------------------------------------------------------------------
step "3 — Per-Disk Confirmation"

_rpt "| Disk | Serial | Slot | User Decision |"
_rpt "|------|--------|------|---------------|"

CONFIRMED=()

for i in "${PENDING[@]}"; do
    banner "/dev/${DISK_NAMES[$i]}"
    printf "  %-16s %s\n" "Size:"   "${DISK_SIZES[$i]}"
    printf "  %-16s %s\n" "Type:"   "${DISK_TYPES[$i]}"
    printf "  %-16s %s\n" "Model:"  "${DISK_MODELS[$i]}"
    printf "  %-16s %s\n" "Serial:" "${DISK_SERIALS[$i]}"
    [[ -n "${DISK_WWNS[$i]}" ]] && printf "  %-16s %s\n" "WWN:" "${DISK_WWNS[$i]}"
    printf "  %-16s %s\n" "Partitions:" "${DISK_PARTS[$i]}"
    printf "  %-16s %s\n" "by-id path:" "${DISK_PATHS[$i]}"
    printf "  %-16s %s\n" "VM slot:"    "VM${VM_ID}:${DISK_SLOTS[$i]}"
    echo ""

    if $YES_ALL; then
        info "--yes-all: auto-confirming /dev/${DISK_NAMES[$i]}"
        CONFIRMED+=("$i")
        _rpt "| /dev/${DISK_NAMES[$i]} | ${DISK_SERIALS[$i]} | ${DISK_SLOTS[$i]} | ✔ confirmed (--yes-all) |"
    else
        local disk_answer
        while true; do
            read -rp "  Attach /dev/${DISK_NAMES[$i]} to VM ${VM_ID} as ${DISK_SLOTS[$i]}? [y/n]: " disk_answer
            case "${disk_answer,,}" in
                y|yes)
                    CONFIRMED+=("$i")
                    ok "Confirmed — /dev/${DISK_NAMES[$i]}"
                    _rpt "| /dev/${DISK_NAMES[$i]} | ${DISK_SERIALS[$i]} | ${DISK_SLOTS[$i]} | ✔ confirmed |"
                    break ;;
                n|no)
                    warn "Skipped — /dev/${DISK_NAMES[$i]}"
                    _rpt "| /dev/${DISK_NAMES[$i]} | ${DISK_SERIALS[$i]} | ${DISK_SLOTS[$i]} | ✗ skipped by user |"
                    break ;;
                *) echo "  Please answer y or n." ;;
            esac
        done
    fi
    echo ""
done

if [[ ${#CONFIRMED[@]} -eq 0 ]]; then
    warn "No disks confirmed. Nothing was changed."
    finish_report "NO DISKS CONFIRMED"
    print_report_path
    exit 0
fi

# ---------------------------------------------------------------------------
# Step 4: Execution plan
# ---------------------------------------------------------------------------
step "4 — Execution Plan"

_rpt "**Commands to be executed:**"
_rpt "\`\`\`"

NEEDS_CONTROLLER=false
! echo "$CURRENT_CONF" | grep -q "scsihw:" && NEEDS_CONTROLLER=true

for i in "${CONFIRMED[@]}"; do
    CMD="qm set ${VM_ID} --${DISK_SLOTS[$i]} ${DISK_PATHS[$i]},backup=0,cache=none,aio=native"
    echo "  $CMD"
    _rpt "$CMD"
done

if $NEEDS_CONTROLLER; then
    CMD="qm set ${VM_ID} --scsihw virtio-scsi-single"
    echo "  $CMD"
    _rpt "$CMD"
fi
_rpt "\`\`\`"

echo ""
read -rp "  Execute the above commands now? [y/n]: " exec_answer
if [[ "${exec_answer,,}" != "y" && "${exec_answer,,}" != "yes" ]]; then
    warn "Aborted — no changes made."
    _rpt ""
    _rpt "> **ABORTED** by user at final confirmation."
    finish_report "ABORTED"
    print_report_path
    exit 0
fi
_rpt ""
_rpt "> User confirmed: **YES** — executing."

# ---------------------------------------------------------------------------
# Step 5: Execute
# ---------------------------------------------------------------------------
step "5 — Attaching Disks"

_rpt "| Disk | Slot | Path | Result |"
_rpt "|------|------|------|--------|"

ATTACHED=0
FAILED=0

for i in "${CONFIRMED[@]}"; do
    banner "/dev/${DISK_NAMES[$i]}  →  VM${VM_ID}:${DISK_SLOTS[$i]}"

    CMD="qm set ${VM_ID} --${DISK_SLOTS[$i]} ${DISK_PATHS[$i]},backup=0,cache=none,aio=native"
    echo -e "      ${_C_DIM}\$ $CMD${_C_RESET}"
    _rpt "  - \`$CMD\`"

    if qm set "${VM_ID}" \
           --"${DISK_SLOTS[$i]}" "${DISK_PATHS[$i]},backup=0,cache=none,aio=native"; then
        ok "Attached /dev/${DISK_NAMES[$i]} → VM${VM_ID}:${DISK_SLOTS[$i]}"
        _rpt "| /dev/${DISK_NAMES[$i]} | ${DISK_SLOTS[$i]} | ${DISK_PATHS[$i]} | ✔ attached |"
        ATTACHED=$(( ATTACHED + 1 ))
    else
        warn "Failed to attach /dev/${DISK_NAMES[$i]}"
        _rpt "| /dev/${DISK_NAMES[$i]} | ${DISK_SLOTS[$i]} | ${DISK_PATHS[$i]} | ✗ FAILED |"
        FAILED=$(( FAILED + 1 ))
    fi
done

if $NEEDS_CONTROLLER; then
    info "Adding SCSI controller (virtio-scsi-single)…"
    run_cmd "qm set ${VM_ID} --scsihw virtio-scsi-single"
    ok "SCSI controller set"
fi

# ---------------------------------------------------------------------------
# Final summary
# ---------------------------------------------------------------------------
step "Summary"

echo -e "${_C_GREEN}  ┌──────────────────────────────────────────────────────────────┐${_C_RESET}"
printf  "${_C_GREEN}  │  %-62s│${_C_RESET}\n" "✔  $ATTACHED disk(s) attached to VM ${VM_ID}."
[[ $FAILED -gt 0 ]] && \
printf  "\033[1;31m  │  ✗  $FAILED disk(s) FAILED to attach.%-33s│\033[0m\n" ""
echo -e "${_C_GREEN}  └──────────────────────────────────────────────────────────────┘${_C_RESET}"
echo ""
echo "  Verify config:       qm config ${VM_ID}"
echo "  Start VM:            qm start ${VM_ID}"
echo "  Inside VM — confirm: lsblk -o NAME,SIZE,MODEL,SERIAL"
echo "  Then run:            sudo bash deploy/vm-mount-disks.sh --wipe"
echo ""

_rpt ""
_rpt "| Metric | Count |"
_rpt "|--------|-------|"
_rpt "| Disks attached | $ATTACHED |"
_rpt "| Disks failed | $FAILED |"
_rpt ""
_rpt "**Post-attach commands:**"
_rpt "\`\`\`"
_rpt "qm config ${VM_ID}"
_rpt "qm start ${VM_ID}"
_rpt "\`\`\`"

RESULT="SUCCESS"
[[ $FAILED -gt 0 ]] && RESULT="PARTIAL ($ATTACHED attached, $FAILED failed)"

finish_report "$RESULT"
print_report_path
