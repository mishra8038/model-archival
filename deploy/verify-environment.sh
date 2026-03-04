#!/usr/bin/env bash
# =============================================================================
# deploy/verify-environment.sh
# Pre-execution environment verification for the model archiver.
#
# Checks the system, Python environment, drives, network, HuggingFace token,
# and registry — then writes a structured Markdown report.  Run this BEFORE
# starting the archiver to confirm everything is in order.
#
# Usage:
#   bash verify-environment.sh [OPTIONS]
#
# Options:
#   --repo-dir PATH     Path to model-archival repo (default: parent of this script)
#   --skip-network      Skip network / HF reachability checks
#   --skip-token        Skip HuggingFace token access checks
#   --skip-hf-api       Skip per-model HF API token checks (fast mode)
#   --min-free-gb N     Minimum free GB per drive to pass (default: 50)
#
# Exit codes:
#   0  All checks passed (green / warnings only)
#   1  One or more checks FAILED
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SKIP_NETWORK=false
SKIP_TOKEN=false
SKIP_HF_API=false
MIN_FREE_GB=50

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
PASS=0
WARN=0
FAIL=0

pass()  {
    echo -e "      ${_C_GREEN}✔  PASS${_C_RESET}  $*"
    _rpt "| ✔ PASS | $* |"
    PASS=$(( PASS + 1 ))
}
warn_check() {
    echo -e "      ${_C_YELLOW}⚠  WARN${_C_RESET}  $*"
    _rpt "| ⚠ WARN | $* |"
    WARN=$(( WARN + 1 ))
}
fail() {
    echo -e "      ${_C_RED}✗  FAIL${_C_RESET}  $*"
    _rpt "| ✗ FAIL | $* |"
    FAIL=$(( FAIL + 1 ))
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo-dir)      REPO_DIR="$2"; shift 2 ;;
        --skip-network)  SKIP_NETWORK=true; shift ;;
        --skip-token)    SKIP_TOKEN=true; shift ;;
        --skip-hf-api)   SKIP_HF_API=true; shift ;;
        --min-free-gb)   MIN_FREE_GB="$2"; shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Initialise report
# ---------------------------------------------------------------------------
init_report "verify-environment"
_rpt "| Repo dir | \`$REPO_DIR\` |"
_rpt "| Min free GB | $MIN_FREE_GB GB per drive |"
_rpt "| Skip network | $SKIP_NETWORK |"
_rpt "| Skip token | $SKIP_TOKEN |"
_rpt ""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
hr() { echo ""; }

bytes_to_human() {
    local b=$1
    if   (( b >= 1099511627776 )); then printf "%.1f TB" "$(echo "scale=1; $b/1099511627776" | bc)"
    elif (( b >= 1073741824 ));    then printf "%.1f GB" "$(echo "scale=1; $b/1073741824" | bc)"
    elif (( b >= 1048576 ));       then printf "%.1f MB" "$(echo "scale=1; $b/1048576" | bc)"
    else printf "%d B" "$b"
    fi
}

check_tool() {
    local name="$1" install_hint="${2:-}"
    if command -v "$name" &>/dev/null; then
        local ver
        ver=$("$name" --version 2>&1 | head -1 || true)
        pass "$name found — $ver"
    else
        if [[ -n "$install_hint" ]]; then
            fail "$name not found in PATH  ($install_hint)"
        else
            fail "$name not found in PATH"
        fi
    fi
}

# ---------------------------------------------------------------------------
# ══════════════════════════════════════════════════════════════════════════
# SECTION 1 — System Tools
# ══════════════════════════════════════════════════════════════════════════
# ---------------------------------------------------------------------------
step "1 — System Tools"
_rpt "| Result | Check |"
_rpt "|--------|-------|"

check_tool "python3"   "apt install python3 / pacman -S python"
check_tool "aria2c"    "apt install aria2   / pacman -S aria2"
check_tool "git"       "apt install git     / pacman -S git"
check_tool "screen"    "apt install screen  / pacman -S screen"
check_tool "rsync"     "apt install rsync   / pacman -S rsync"
check_tool "sgdisk"    "apt install gdisk   / pacman -S gptfdisk"
check_tool "wipefs"    "apt install util-linux (should be present)"
check_tool "lsblk"     "apt install util-linux (should be present)"
check_tool "blkid"     "apt install util-linux (should be present)"
check_tool "curl"      "apt install curl    / pacman -S curl"
check_tool "uv"        "curl -LsSf https://astral.sh/uv/install.sh | sh"

# ---------------------------------------------------------------------------
# SECTION 2 — Python / Virtual Environment
# ---------------------------------------------------------------------------
step "2 — Python Environment"
_rpt "| Result | Check |"
_rpt "|--------|-------|"

if [[ ! -f "$REPO_DIR/pyproject.toml" ]]; then
    fail "pyproject.toml not found in $REPO_DIR"
else
    pass "pyproject.toml found at $REPO_DIR"
fi

if [[ ! -d "$REPO_DIR/.venv" ]]; then
    fail ".venv not found — run: cd $REPO_DIR && uv sync"
else
    pass ".venv directory exists at $REPO_DIR/.venv"

    if command -v uv &>/dev/null; then
        VENV_PY=$(uv run --project "$REPO_DIR" python --version 2>&1 || echo "")
        if [[ -n "$VENV_PY" ]]; then
            pass "Virtual env Python: $VENV_PY"
        else
            fail "Could not execute Python in .venv"
        fi

        ARCHIVER_VER=$(uv run --project "$REPO_DIR" archiver --version 2>&1 \
                       || uv run --project "$REPO_DIR" archiver --help 2>&1 | head -1 \
                       || echo "")
        if [[ -n "$ARCHIVER_VER" ]]; then
            pass "archiver CLI accessible — $ARCHIVER_VER"
        else
            fail "archiver CLI not accessible (uv run archiver --help failed)"
        fi

        # Check all declared dependencies are installed
        DEP_CHECK=$(uv run --project "$REPO_DIR" python -c "
import importlib, sys
deps = ['huggingface_hub','aria2p','httpx','click','rich','yaml','psutil']
missing = [d for d in deps if not importlib.util.find_spec(d.replace('-','_'))]
if missing:
    print('MISSING: ' + ', '.join(missing))
    sys.exit(1)
else:
    print('all present')
" 2>&1)
        if echo "$DEP_CHECK" | grep -q "MISSING"; then
            fail "Python dependencies incomplete: $DEP_CHECK — run: uv sync"
        else
            pass "Python dependencies: all present"
        fi
    else
        fail "uv not found — cannot check virtual environment"
    fi
fi

# ---------------------------------------------------------------------------
# SECTION 3 — Registry
# ---------------------------------------------------------------------------
step "3 — Registry & Configuration"
_rpt "| Result | Check |"
_rpt "|--------|-------|"

REGISTRY_FILE="$REPO_DIR/config/registry.yaml"
DRIVES_FILE="$REPO_DIR/config/drives.yaml"

if [[ ! -f "$REGISTRY_FILE" ]]; then
    fail "registry.yaml not found: $REGISTRY_FILE"
else
    pass "registry.yaml found"
fi

if [[ ! -f "$DRIVES_FILE" ]]; then
    fail "drives.yaml not found: $DRIVES_FILE"
else
    pass "drives.yaml found"
fi

if [[ -f "$REGISTRY_FILE" && -f "$DRIVES_FILE" ]] && command -v uv &>/dev/null; then
    # Parse registry via Python to get exact counts
    REG_STATS=$(uv run --project "$REPO_DIR" python -c "
import sys; sys.path.insert(0,'$REPO_DIR/src')
from archiver.models import load_registry
from pathlib import Path
try:
    reg = load_registry(Path('$REGISTRY_FILE'), Path('$DRIVES_FILE'))
    m = reg.models
    gated   = [x for x in m if x.requires_auth]
    free    = [x for x in m if not x.requires_auth]
    tiers   = {t: len([x for x in m if x.tier==t]) for t in 'ABCD'}
    drives  = {d: len([x for x in m if x.drive==d]) for d in set(x.drive for x in m)}
    print(f'total={len(m)} free={len(free)} gated={len(gated)} '
          f'tA={tiers[\"A\"]} tB={tiers[\"B\"]} tC={tiers[\"C\"]} tD={tiers[\"D\"]}')
except Exception as e:
    print(f'ERROR={e}')
" 2>&1)

    if echo "$REG_STATS" | grep -q "ERROR="; then
        fail "Registry parse error: $REG_STATS"
    else
        TOTAL=$(echo "$REG_STATS"  | grep -oP 'total=\K[0-9]+')
        FREE_M=$(echo "$REG_STATS" | grep -oP 'free=\K[0-9]+')
        GATED=$(echo "$REG_STATS"  | grep -oP 'gated=\K[0-9]+')
        TA=$(echo "$REG_STATS"     | grep -oP 'tA=\K[0-9]+')
        TB=$(echo "$REG_STATS"     | grep -oP 'tB=\K[0-9]+')
        TC=$(echo "$REG_STATS"     | grep -oP 'tC=\K[0-9]+')
        TD=$(echo "$REG_STATS"     | grep -oP 'tD=\K[0-9]+')
        pass "Registry parsed: $TOTAL models — Tier A:$TA  B:$TB  C:$TC  D:$TD"
        pass "Auth breakdown: $FREE_M token-free (priority 1),  $GATED gated (priority 2)"
        _rpt ""
        _rpt "**Registry contents:**"
        _rpt ""
        _rpt "| Category | Count |"
        _rpt "|----------|-------|"
        _rpt "| Total models | $TOTAL |"
        _rpt "| Token-free (P1) | $FREE_M |"
        _rpt "| Gated (P2) | $GATED |"
        _rpt "| Tier A | $TA |"
        _rpt "| Tier B | $TB |"
        _rpt "| Tier C | $TC |"
        _rpt "| Tier D | $TD |"
    fi

    # Run archiver's built-in registry validation
    VAL_OUT=$(uv run --project "$REPO_DIR" python -c "
import sys; sys.path.insert(0,'$REPO_DIR/src')
from archiver.models import load_registry
from archiver.preflight import check_registry
from pathlib import Path
try:
    reg = load_registry(Path('$REGISTRY_FILE'), Path('$DRIVES_FILE'))
    check_registry(reg)
    print('OK')
except Exception as e:
    print(f'FAIL:{e}')
" 2>&1)
    if [[ "$VAL_OUT" == "OK" ]]; then
        pass "Registry schema validation passed"
    else
        fail "Registry schema validation failed: $VAL_OUT"
    fi
fi

# ---------------------------------------------------------------------------
# SECTION 4 — Drives
# ---------------------------------------------------------------------------
step "4 — Drive Mounts, Filesystem & Space"

# Expected allocation (used for "enough space?" check per drive)
# Format: drive_label:min_free_gb:expected_use_tb:role
DRIVE_EXPECTATIONS=(
    "d1:200:3.4:Raw giants (Tier A/B large)"
    "d2:100:2.1:Raw mid-size + Tier D uncensored"
    "d3:100:1.4:Quantized GGUF (Tier C + D-quants)"
    "d5:10:0.1:Archive + logs + run_state"
)

_rpt ""
_rpt "| Drive | Mount | Filesystem | UUID | Total | Used | Free | Free% | Writable | Status |"
_rpt "|-------|-------|------------|------|-------|------|------|-------|----------|--------|"

for entry in "${DRIVE_EXPECTATIONS[@]}"; do
    IFS=: read -r label min_free_gb expected_use_tb role <<< "$entry"
    banner "Drive $label — $role"

    # Read mount point from drives.yaml
    mp=$(grep -A3 "^${label}:" "$DRIVES_FILE" 2>/dev/null \
         | grep "mount_point:" | awk '{print $2}' | tr -d '"' || echo "")

    if [[ -z "$mp" ]]; then
        fail "$label: not found in drives.yaml"
        _rpt "| $label | (not in drives.yaml) | — | — | — | — | — | — | — | ✗ FAIL |"
        continue
    fi

    printf "  %-14s %s\n" "Mount point:" "$mp"
    printf "  %-14s %s\n" "Role:" "$role"
    printf "  %-14s %s GB minimum\n" "Min free:" "$min_free_gb"

    # Check mount point exists
    if [[ ! -d "$mp" ]]; then
        fail "$label ($mp): directory does not exist — not mounted"
        _rpt "| $label | $mp | — | — | — | — | — | — | — | ✗ not mounted |"
        continue
    fi
    pass "$label: mount point $mp exists"

    # Check it is actually a separate mount (not just a subdirectory of root)
    mp_dev=$(stat -c '%d' "$mp" 2>/dev/null || echo "0")
    root_dev=$(stat -c '%d' / 2>/dev/null || echo "1")
    if [[ "$mp_dev" == "$root_dev" ]]; then
        warn_check "$label ($mp): appears to be on the root filesystem — not a separate disk mount"
        MOUNT_STATUS="⚠ on root fs"
    else
        pass "$label: mounted as separate filesystem (device $mp_dev)"
        MOUNT_STATUS="✔ mounted"
    fi

    # Filesystem type
    FS_TYPE=$(findmnt -no FSTYPE "$mp" 2>/dev/null || blkid -o value -s TYPE "$(df "$mp" | tail -1 | awk '{print $1}')" 2>/dev/null || echo "unknown")
    if [[ "$FS_TYPE" == "ext4" ]]; then
        pass "$label: filesystem type ext4"
    else
        warn_check "$label: filesystem type is '$FS_TYPE' (expected ext4)"
    fi

    # UUID
    DEVICE=$(df "$mp" 2>/dev/null | tail -1 | awk '{print $1}')
    UUID=$(blkid -s UUID -o value "$DEVICE" 2>/dev/null || echo "")
    if [[ -n "$UUID" ]]; then
        pass "$label: UUID $UUID"
        printf "  %-14s %s\n" "UUID:" "$UUID"
    else
        warn_check "$label: could not read UUID from $DEVICE"
    fi

    # /etc/fstab entry
    if grep -qs "$mp" /etc/fstab 2>/dev/null; then
        FSTAB_LINE=$(grep "$mp" /etc/fstab | head -1)
        if [[ -n "$UUID" ]] && grep -qs "$UUID" /etc/fstab 2>/dev/null; then
            pass "$label: /etc/fstab entry present with correct UUID"
        else
            warn_check "$label: /etc/fstab has a line for $mp but UUID doesn't match — may not survive reboot"
        fi
    else
        warn_check "$label ($mp): no /etc/fstab entry — drive will NOT auto-mount on reboot"
    fi

    # Disk space
    DISK_INFO=$(df -B1 "$mp" 2>/dev/null | tail -1 || echo "")
    if [[ -n "$DISK_INFO" ]]; then
        TOTAL_B=$(echo "$DISK_INFO" | awk '{print $2}')
        USED_B=$(echo  "$DISK_INFO" | awk '{print $3}')
        FREE_B=$(echo  "$DISK_INFO" | awk '{print $4}')
        PCT=$(echo     "$DISK_INFO" | awk '{print $5}')

        TOTAL_H=$(bytes_to_human "$TOTAL_B")
        USED_H=$(bytes_to_human  "$USED_B")
        FREE_H=$(bytes_to_human  "$FREE_B")
        FREE_GB=$(echo "scale=1; $FREE_B/1073741824" | bc)
        FREE_GB_INT=${FREE_GB%.*}

        printf "  %-14s %s\n"  "Total:"     "$TOTAL_H"
        printf "  %-14s %s\n"  "Used:"      "$USED_H"
        printf "  %-14s %s  (%s used)\n" "Free:" "$FREE_H" "$PCT"

        if (( FREE_GB_INT >= min_free_gb )); then
            pass "$label: ${FREE_H} free — above minimum ${min_free_gb} GB threshold"
            SPACE_STATUS="✔ ${FREE_H} free"
        else
            fail "$label: only ${FREE_H} free — below minimum ${min_free_gb} GB  (add more storage or free space)"
            SPACE_STATUS="✗ ${FREE_H} free (need ${min_free_gb} GB)"
        fi
    else
        warn_check "$label: could not read disk usage"
        TOTAL_H="?"; USED_H="?"; FREE_H="?"; PCT="?"; SPACE_STATUS="? unknown"
    fi

    # Write test
    TEST_FILE="$mp/.verify_write_$$"
    if touch "$TEST_FILE" 2>/dev/null; then
        rm -f "$TEST_FILE"
        pass "$label: write test passed"
        WRITABLE="✔"
    else
        fail "$label ($mp): not writable by current user"
        WRITABLE="✗"
    fi

    # .tmp scratch check for D1
    if [[ "$label" == "d1" ]]; then
        TMP_DIR="$mp/.tmp"
        if [[ -d "$TMP_DIR" ]]; then
            pass "$label: .tmp scratch directory exists at $TMP_DIR"
        else
            warn_check "$label: .tmp scratch directory missing ($TMP_DIR) — created by vm-mount-disks.sh"
        fi
    fi

    echo ""
    _rpt "| $label | $mp | $FS_TYPE | \`$UUID\` | $TOTAL_H | $USED_H | $FREE_H | $PCT | $WRITABLE | $MOUNT_STATUS / $SPACE_STATUS |"
done

# ---------------------------------------------------------------------------
# SECTION 5 — Network
# ---------------------------------------------------------------------------
step "5 — Network Connectivity"
_rpt "| Result | Check |"
_rpt "|--------|-------|"

if $SKIP_NETWORK; then
    warn_check "Network checks skipped (--skip-network)"
else
    HOSTS=(
        "huggingface.co:443:HuggingFace main site"
        "cdn-lfs.huggingface.co:443:HuggingFace LFS CDN"
        "huggingface.co:80:HuggingFace HTTP redirect"
    )

    for entry in "${HOSTS[@]}"; do
        IFS=: read -r host port desc <<< "$entry"
        if timeout 8 bash -c "echo > /dev/tcp/$host/$port" 2>/dev/null; then
            pass "$desc ($host:$port) — reachable"
        else
            fail "$desc ($host:$port) — unreachable"
        fi
    done

    # DNS resolution
    if command -v host &>/dev/null; then
        if host huggingface.co &>/dev/null 2>&1; then
            HF_IP=$(host huggingface.co 2>/dev/null | grep "has address" | head -1 | awk '{print $4}')
            pass "DNS resolution for huggingface.co → $HF_IP"
        else
            fail "DNS resolution for huggingface.co failed"
        fi
    elif command -v nslookup &>/dev/null; then
        if nslookup huggingface.co &>/dev/null 2>&1; then
            pass "DNS resolution for huggingface.co — OK"
        else
            fail "DNS resolution for huggingface.co failed"
        fi
    else
        warn_check "Neither 'host' nor 'nslookup' available — skipping DNS check"
    fi

    # HTTP check via curl
    if command -v curl &>/dev/null; then
        HTTP_CODE=$(curl -sLo /dev/null -w "%{http_code}" \
                    --max-time 10 https://huggingface.co 2>/dev/null || echo "000")
        if [[ "$HTTP_CODE" -ge 200 && "$HTTP_CODE" -lt 400 ]]; then
            pass "HTTPS GET huggingface.co → HTTP $HTTP_CODE"
        else
            fail "HTTPS GET huggingface.co → HTTP $HTTP_CODE"
        fi
    fi
fi

# ---------------------------------------------------------------------------
# SECTION 6 — HuggingFace Token
# ---------------------------------------------------------------------------
step "6 — HuggingFace Token & Model Access"
_rpt "| Result | Check |"
_rpt "|--------|-------|"

HF_TOKEN="${HF_TOKEN:-}"

if [[ -z "$HF_TOKEN" ]]; then
    warn_check "HF_TOKEN not set in environment"
    warn_check "Gated models (priority 2) require a token — see docs/HF-TOKEN-GUIDE.md"
    _rpt ""
    _rpt "> Set token with:  \`export HF_TOKEN=hf_...\`"
    _rpt "> See: \`docs/HF-TOKEN-GUIDE.md\`"
else
    # Validate token format
    if [[ "$HF_TOKEN" =~ ^hf_[A-Za-z0-9]{10,}$ ]]; then
        pass "HF_TOKEN format looks valid (hf_...)"
    else
        warn_check "HF_TOKEN format looks unusual (expected hf_XXXX...)"
    fi

    # Test token against HF API
    if $SKIP_TOKEN || $SKIP_HF_API; then
        warn_check "HF API token checks skipped (--skip-token / --skip-hf-api)"
    else
        info "Testing HF token against gated model repos…"
        _rpt ""
        _rpt "| Model | HF Repo | HTTP | Accessible |"
        _rpt "|-------|---------|------|------------|"

        TOKEN_PASS=0
        TOKEN_FAIL=0

        # Read gated models from registry
        if [[ -f "$REGISTRY_FILE" ]] && command -v uv &>/dev/null; then
            GATED_LIST=$(uv run --project "$REPO_DIR" python -c "
import sys; sys.path.insert(0,'$REPO_DIR/src')
from archiver.models import load_registry
from pathlib import Path
reg = load_registry(Path('$REGISTRY_FILE'), Path('$DRIVES_FILE'))
for m in reg.gated():
    print(f'{m.id}|{m.hf_repo}')
" 2>&1)

            while IFS='|' read -r model_id hf_repo; do
                [[ -z "$model_id" ]] && continue
                HTTP=$(curl -sLo /dev/null -w "%{http_code}" \
                       -H "Authorization: Bearer $HF_TOKEN" \
                       --max-time 15 \
                       "https://huggingface.co/api/models/$hf_repo" 2>/dev/null \
                       || echo "000")
                if [[ "$HTTP" == "200" ]]; then
                    pass "$model_id ($hf_repo) — HTTP $HTTP — accessible"
                    _rpt "| $model_id | $hf_repo | $HTTP | ✔ yes |"
                    TOKEN_PASS=$(( TOKEN_PASS + 1 ))
                elif [[ "$HTTP" == "401" || "$HTTP" == "403" ]]; then
                    fail "$model_id ($hf_repo) — HTTP $HTTP — access denied (request access on HF)"
                    _rpt "| $model_id | $hf_repo | $HTTP | ✗ denied |"
                    TOKEN_FAIL=$(( TOKEN_FAIL + 1 ))
                else
                    warn_check "$model_id ($hf_repo) — HTTP $HTTP — unexpected response"
                    _rpt "| $model_id | $hf_repo | $HTTP | ⚠ unexpected |"
                fi
            done <<< "$GATED_LIST"

            echo ""
            if [[ $TOKEN_FAIL -eq 0 ]]; then
                pass "All $TOKEN_PASS gated models accessible"
            else
                fail "$TOKEN_FAIL gated model(s) not accessible — see docs/HF-TOKEN-GUIDE.md"
            fi
        fi
    fi
fi

# ---------------------------------------------------------------------------
# SECTION 7 — Estimated Storage Requirements vs Available
# ---------------------------------------------------------------------------
step "7 — Storage Requirements vs Available"

_rpt ""
_rpt "| Drive | Available | Required (planned) | Headroom | Status |"
_rpt "|-------|-----------|--------------------|----------|--------|"

# Expected allocations in GB (from REQUIREMENTS.md)
declare -A DRIVE_REQUIRED=(
    ["d1"]="3400"    # DeepSeek-V3 + R1 + Llama405B + DS-Coder-V2
    ["d2"]="2100"    # All mid-size + Tier D uncensored
    ["d3"]="1400"    # All GGUF quants
    ["d5"]="50"      # archive/logs/state — tiny
)

ALL_SPACE_OK=true

for label in d1 d2 d3 d5; do
    mp=$(grep -A3 "^${label}:" "$DRIVES_FILE" 2>/dev/null \
         | grep "mount_point:" | awk '{print $2}' | tr -d '"' || echo "")
    required_gb=${DRIVE_REQUIRED[$label]:-0}
    required_h=$(bytes_to_human $(( required_gb * 1073741824 )))

    if [[ -z "$mp" || ! -d "$mp" ]]; then
        fail "$label: not mounted — cannot check storage"
        _rpt "| $label | — | ~${required_gb} GB | — | ✗ not mounted |"
        ALL_SPACE_OK=false
        continue
    fi

    avail_b=$(df -B1 "$mp" 2>/dev/null | tail -1 | awk '{print $4}' || echo "0")
    avail_gb=$(echo "scale=0; $avail_b/1073741824" | bc)
    avail_h=$(bytes_to_human "$avail_b")
    headroom_gb=$(( avail_gb - required_gb ))

    printf "  %-6s  Available: %-10s  Required: %-10s  Headroom: %+d GB\n" \
           "$label" "$avail_h" "~${required_gb} GB" "$headroom_gb"

    if (( avail_gb >= required_gb )); then
        pass "$label: ${avail_h} available  ≥  ~${required_gb} GB needed  (+${headroom_gb} GB headroom)"
        _rpt "| $label | $avail_h | ~${required_gb} GB | +${headroom_gb} GB | ✔ OK |"
    else
        SHORTFALL=$(( required_gb - avail_gb ))
        fail "$label: only ${avail_h} available  <  ~${required_gb} GB needed  (SHORT by ${SHORTFALL} GB)"
        _rpt "| $label | $avail_h | ~${required_gb} GB | -${SHORTFALL} GB | ✗ insufficient |"
        ALL_SPACE_OK=false
    fi
done

echo ""
if $ALL_SPACE_OK; then
    ok "All drives have sufficient space for the planned archive"
else
    echo -e "  ${_C_RED}One or more drives do not have sufficient space — review allocations.${_C_RESET}"
fi

# ---------------------------------------------------------------------------
# SECTION 8 — archiver download dry-run
# ---------------------------------------------------------------------------
step "8 — Archiver Dry-Run (registry + path resolution)"
_rpt "| Result | Check |"
_rpt "|--------|-------|"

if command -v uv &>/dev/null && [[ -d "$REPO_DIR/.venv" ]]; then
    info "Running: archiver download --all --dry-run"
    DRYRUN_OUT=$(cd "$REPO_DIR" && uv run archiver download --all --dry-run 2>&1 || true)
    echo "$DRYRUN_OUT" | head -40 | sed 's/^/      /'
    if echo "$DRYRUN_OUT" | grep -qi "error\|exception\|traceback"; then
        fail "Dry-run produced errors — check output above"
        _rpt "\`\`\`"
        echo "$DRYRUN_OUT" | head -50 | while IFS= read -r l; do _rpt "$l"; done
        _rpt "\`\`\`"
    else
        pass "Dry-run completed without Python errors"
        _rpt "\`\`\`"
        echo "$DRYRUN_OUT" | head -30 | while IFS= read -r l; do _rpt "$l"; done
        _rpt "\`\`\`"
    fi
else
    warn_check "uv or .venv not available — skipping dry-run"
fi

# ---------------------------------------------------------------------------
# FINAL SUMMARY
# ---------------------------------------------------------------------------
step "Verification Summary"

TOTAL_CHECKS=$(( PASS + WARN + FAIL ))
echo ""
echo -e "  Checks run:   ${_C_BOLD}$TOTAL_CHECKS${_C_RESET}"
echo -e "  ${_C_GREEN}Passed:${_C_RESET}        $PASS"
echo -e "  ${_C_YELLOW}Warnings:${_C_RESET}      $WARN"
echo -e "  ${_C_RED}Failed:${_C_RESET}        $FAIL"
echo ""

_rpt ""
_rpt "---"
_rpt ""
_rpt "## Verification Summary"
_rpt ""
_rpt "| Metric | Count |"
_rpt "|--------|-------|"
_rpt "| Total checks | $TOTAL_CHECKS |"
_rpt "| ✔ Passed | $PASS |"
_rpt "| ⚠ Warnings | $WARN |"
_rpt "| ✗ Failed | $FAIL |"
_rpt ""

if [[ $FAIL -eq 0 && $WARN -eq 0 ]]; then
    echo -e "${_C_GREEN}  ┌──────────────────────────────────────────────────────────────┐${_C_RESET}"
    echo -e "${_C_GREEN}  │  ✔  All checks passed — environment is ready.                │${_C_RESET}"
    echo -e "${_C_GREEN}  │     Safe to run: archiver download --all --priority-only 1   │${_C_RESET}"
    echo -e "${_C_GREEN}  └──────────────────────────────────────────────────────────────┘${_C_RESET}"
    _rpt "> **RESULT: ✔ ALL PASSED — environment is ready for archiver execution.**"
    FINAL_STATUS="ALL PASSED"

elif [[ $FAIL -eq 0 ]]; then
    echo -e "${_C_YELLOW}  ┌──────────────────────────────────────────────────────────────┐${_C_RESET}"
    echo -e "${_C_YELLOW}  │  ⚠  Passed with $WARN warning(s).                              │${_C_RESET}"
    echo -e "${_C_YELLOW}  │     Review warnings above before starting downloads.          │${_C_RESET}"
    echo -e "${_C_YELLOW}  └──────────────────────────────────────────────────────────────┘${_C_RESET}"
    _rpt "> **RESULT: ⚠ PASSED WITH ${WARN} WARNING(S) — review before proceeding.**"
    FINAL_STATUS="PASSED WITH WARNINGS ($WARN)"

else
    echo -e "${_C_RED}  ┌──────────────────────────────────────────────────────────────┐${_C_RESET}"
    echo -e "${_C_RED}  │  ✗  $FAIL check(s) FAILED.                                     │${_C_RESET}"
    echo -e "${_C_RED}  │     Fix the failures listed above before running archiver.    │${_C_RESET}"
    echo -e "${_C_RED}  └──────────────────────────────────────────────────────────────┘${_C_RESET}"
    _rpt "> **RESULT: ✗ ${FAIL} FAILURE(S) — do not run archiver until fixed.**"
    FINAL_STATUS="FAILED ($FAIL failures, $WARN warnings)"
fi

echo ""
echo "  Quick-start (if all green):"
echo "    cd $REPO_DIR"
echo "    screen -S archiver"
echo "    uv run archiver download --all --priority-only 1"
echo ""

finish_report "$FINAL_STATUS"
print_report_path

echo ""
[[ $FAIL -gt 0 ]] && exit 1 || exit 0
