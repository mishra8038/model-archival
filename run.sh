#!/usr/bin/env bash
# =============================================================================
# run.sh — Universal archiver orchestrator
# Run from the repo root on the target VM.
#
# Executes the full archiver pipeline in order:
#   1. Environment verification  (deploy/verify-environment.sh)
#   2. Archiver download         (uv run archiver download ...)
#   3. Post-download status      (uv run archiver status)
#   4. Archive integrity check   (verification/verify-archive.py)
#
# Generates a single timestamped Markdown report in the repo root:
#   run-report-<timestamp>.md
#
# Usage:
#   bash run.sh [OPTIONS]
#
# Options:
#   --dry-run             Simulate everything; no actual downloads or writes
#   --priority-only 1     Only download P1 (token-free) models  [default: 1]
#   --tier A|B|C|D        Restrict downloads to one tier
#   --all                 Download all models (P1 + P2; token required for P2)
#   --rehash              After download, do full SHA-256 re-hash (slow)
#   --skip-env-check      Skip the environment pre-check step
#   --skip-verify         Skip the post-download integrity verification step
#   --bandwidth-cap N     Cap download bandwidth at N MB/s
#   --max-parallel N      Max parallel drive workers (default: 4)
#   --skip-network        Pass --skip-network to environment check
#   --help                Show this message
#
# Examples:
#   # Typical first run (token-free models, dry-run preview):
#   bash run.sh --dry-run
#
#   # Actual first run (priority 1 / token-free only):
#   bash run.sh --priority-only 1
#
#   # Full run all tiers with bandwidth cap and re-hash verify:
#   bash run.sh --all --bandwidth-cap 200 --rehash
#
#   # Tier A only, dry-run:
#   bash run.sh --tier A --dry-run
# =============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$REPO_DIR/deploy/_common.sh"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DRY_RUN=false
PRIORITY_ONLY=1
TIER=""
DOWNLOAD_ALL=false
REHASH=false
SKIP_ENV_CHECK=false
SKIP_VERIFY=false
BANDWIDTH_CAP=""
MAX_PARALLEL=4
SKIP_NETWORK=false

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
usage() {
    sed -n '/^# Usage:/,/^# =====/{s/^# \{0,1\}//p}' "${BASH_SOURCE[0]}"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)          DRY_RUN=true;             shift ;;
        --priority-only)    PRIORITY_ONLY="$2";        shift 2 ;;
        --tier)             TIER="$2";                 shift 2 ;;
        --all)              DOWNLOAD_ALL=true;         shift ;;
        --rehash)           REHASH=true;               shift ;;
        --skip-env-check)   SKIP_ENV_CHECK=true;       shift ;;
        --skip-verify)      SKIP_VERIFY=true;          shift ;;
        --bandwidth-cap)    BANDWIDTH_CAP="$2";        shift 2 ;;
        --max-parallel)     MAX_PARALLEL="$2";         shift 2 ;;
        --skip-network)     SKIP_NETWORK=true;         shift ;;
        --help|-h)          usage ;;
        *) echo "Unknown option: $1  (run with --help)"; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Initialise report (lands in REPO_DIR)
# ---------------------------------------------------------------------------
_REPORT_DIR_OVERRIDE="$REPO_DIR"
init_report "run"        # creates run-report-<ts>.md in REPO_DIR via _common.sh

# Override _common.sh default (which uses deploy/ as dir) so report lands in root
_REPORT_FILE="$REPO_DIR/run-report-$(date +%Y-%m-%d_%H-%M-%S).md"
# Re-write the header now that we have the correct path
_REPORT_LINES=()
_rpt "# Archiver Run — Orchestration Report"
_rpt ""
_rpt "| Field | Value |"
_rpt "|-------|-------|"
_rpt "| Host | $(hostname) |"
_rpt "| User | $(whoami) |"
_rpt "| Started | $(date '+%Y-%m-%d %H:%M:%S %Z') |"
_rpt "| Repo | \`$REPO_DIR\` |"
_rpt "| Dry run | $DRY_RUN |"
_rpt "| Priority only | ${PRIORITY_ONLY:-all} |"
_rpt "| Tier filter | ${TIER:-all} |"
_rpt "| Download all | $DOWNLOAD_ALL |"
_rpt "| Rehash verify | $REHASH |"
_rpt "| Bandwidth cap | ${BANDWIDTH_CAP:-unlimited} MB/s |"
_rpt "| Max parallel | $MAX_PARALLEL |"
_rpt ""
_rpt "---"
_rpt ""
flush_report

# ---------------------------------------------------------------------------
# Header banner
# ---------------------------------------------------------------------------
echo ""
echo -e "${_C_CYAN}╔══════════════════════════════════════════════════════════════════╗${_C_RESET}"
echo -e "${_C_CYAN}║${_C_RESET}${_C_BOLD}              Model Archiver — Run Orchestrator                   ${_C_RESET}${_C_CYAN}║${_C_RESET}"
echo -e "${_C_CYAN}╚══════════════════════════════════════════════════════════════════╝${_C_RESET}"
echo ""
info "Repo:         $REPO_DIR"
info "Dry run:      $DRY_RUN"
info "Priority:     ${PRIORITY_ONLY:-all}"
info "Tier:         ${TIER:-all}"
info "Rehash:       $REHASH"
info "Report:       $_REPORT_FILE"
echo ""

if $DRY_RUN; then
    echo -e "  ${_C_YELLOW}┌─────────────────────────────────────────────────────────────┐${_C_RESET}"
    echo -e "  ${_C_YELLOW}│  DRY RUN MODE — no downloads, no writes to drives            │${_C_RESET}"
    echo -e "  ${_C_YELLOW}└─────────────────────────────────────────────────────────────┘${_C_RESET}"
    echo ""
fi

# ---------------------------------------------------------------------------
# Guard: uv must exist
# ---------------------------------------------------------------------------
if ! command -v uv &>/dev/null; then
    error "uv not found in PATH. Run deploy/setup-mxlinux.sh or deploy/setup-artix.sh first."
fi
if [[ ! -d "$REPO_DIR/.venv" ]]; then
    error ".venv not found at $REPO_DIR — run: cd $REPO_DIR && uv sync"
fi

# ---------------------------------------------------------------------------
# Step counters
# ---------------------------------------------------------------------------
STEP_PASS=0
STEP_WARN=0
STEP_FAIL=0

record_step_pass() { STEP_PASS=$(( STEP_PASS + 1 )); _rpt "- ✔ $*"; }
record_step_warn() { STEP_WARN=$(( STEP_WARN + 1 )); _rpt "- ⚠ $*"; }
record_step_fail() { STEP_FAIL=$(( STEP_FAIL + 1 )); _rpt "- ✗ $*"; }

# ---------------------------------------------------------------------------
# ════════════════════════════════════════════════════════════════════════════
# STEP 1 — Environment Verification
# ════════════════════════════════════════════════════════════════════════════
# ---------------------------------------------------------------------------
step "Step 1 — Environment Verification"
_rpt "## Step 1 — Environment Verification"
_rpt ""

if $SKIP_ENV_CHECK; then
    warn "Skipping environment check (--skip-env-check)"
    record_step_warn "Environment check skipped"
else
    ENV_ARGS=("--repo-dir" "$REPO_DIR")
    $SKIP_NETWORK && ENV_ARGS+=("--skip-network")
    $DRY_RUN      && ENV_ARGS+=("--skip-network" "--skip-token")

    # Capture output and exit code
    ENV_OUT_FILE=$(mktemp /tmp/archiver-env-XXXXXX.txt)
    ENV_RC=0
    bash "$REPO_DIR/deploy/verify-environment.sh" "${ENV_ARGS[@]}" 2>&1 \
        | tee "$ENV_OUT_FILE" || ENV_RC=$?

    # Extract pass/warn/fail counts from the output
    ENV_PASS=$(grep -c "✔  PASS" "$ENV_OUT_FILE" 2>/dev/null || echo 0)
    ENV_WARN=$(grep -c "⚠  WARN" "$ENV_OUT_FILE" 2>/dev/null || echo 0)
    ENV_FAIL=$(grep -c "✗  FAIL" "$ENV_OUT_FILE" 2>/dev/null || echo 0)

    _rpt "Environment check completed."
    _rpt ""
    _rpt "| Checks | Count |"
    _rpt "|--------|-------|"
    _rpt "| Passed | $ENV_PASS |"
    _rpt "| Warnings | $ENV_WARN |"
    _rpt "| Failed | $ENV_FAIL |"
    _rpt ""

    # Embed the verify-environment report path if it was written
    ENV_REPORT=$(ls -t "$REPO_DIR/deploy"/verify-environment-report-*.md 2>/dev/null | head -1 || echo "")
    if [[ -n "$ENV_REPORT" ]]; then
        _rpt "Full environment report: \`$ENV_REPORT\`"
        _rpt ""
    fi
    rm -f "$ENV_OUT_FILE"

    if [[ $ENV_RC -ne 0 || $ENV_FAIL -gt 0 ]]; then
        record_step_fail "Environment check: $ENV_FAIL failure(s)"
        if ! $DRY_RUN; then
            error "Environment check failed — fix the issues above before running downloads."
        else
            warn "Environment issues detected (dry-run continues anyway)"
        fi
    elif [[ $ENV_WARN -gt 0 ]]; then
        record_step_warn "Environment check passed with $ENV_WARN warning(s)"
        ok "Environment check passed (with $ENV_WARN warning(s))"
    else
        record_step_pass "Environment check: all checks passed"
        ok "Environment check: all checks passed"
    fi
fi

flush_report

# ---------------------------------------------------------------------------
# ════════════════════════════════════════════════════════════════════════════
# STEP 2 — Download Plan (always shown, even in dry-run)
# ════════════════════════════════════════════════════════════════════════════
# ---------------------------------------------------------------------------
step "Step 2 — Download Plan"
_rpt "## Step 2 — Download Plan"
_rpt ""

# Build archiver download args
DOWNLOAD_ARGS=()
if $DOWNLOAD_ALL; then
    DOWNLOAD_ARGS+=("--all")
else
    DOWNLOAD_ARGS+=("--all")  # default to --all; priority/tier filter below
fi
[[ -n "$TIER" ]]         && DOWNLOAD_ARGS+=("--tier" "$TIER")
[[ -n "$PRIORITY_ONLY" ]] && DOWNLOAD_ARGS+=("--priority-only" "$PRIORITY_ONLY")
[[ -n "$BANDWIDTH_CAP" ]] && DOWNLOAD_ARGS+=("--bandwidth-cap" "$BANDWIDTH_CAP")
DOWNLOAD_ARGS+=("--max-parallel-drives" "$MAX_PARALLEL")

info "Running dry-run to capture download plan…"
PLAN_OUT=$(cd "$REPO_DIR" && uv run archiver download "${DOWNLOAD_ARGS[@]}" --dry-run 2>&1 || true)
echo "$PLAN_OUT"

_rpt "\`\`\`"
echo "$PLAN_OUT" | while IFS= read -r l; do _rpt "$l"; done
_rpt "\`\`\`"
_rpt ""

# Count models from plan output
MODEL_COUNT=$(echo "$PLAN_OUT" | grep -c "│" 2>/dev/null || echo "?")
record_step_pass "Download plan generated ($MODEL_COUNT table rows shown above)"

flush_report

# ---------------------------------------------------------------------------
# ════════════════════════════════════════════════════════════════════════════
# STEP 3 — Download
# ════════════════════════════════════════════════════════════════════════════
# ---------------------------------------------------------------------------
step "Step 3 — Download"
_rpt "## Step 3 — Download"
_rpt ""

if $DRY_RUN; then
    warn "DRY RUN — skipping actual downloads"
    _rpt "_Dry run — downloads skipped._"
    _rpt ""
    record_step_warn "Download skipped (dry-run)"
else
    info "Starting download — this may run for hours."
    info "Logs → $(cd "$REPO_DIR" && uv run python3 -c "
import sys; sys.path.insert(0,'src')
from archiver.models import load_registry
from pathlib import Path
reg = load_registry(Path('config/registry.yaml'), Path('config/drives.yaml'))
d5 = reg.drives.get('d5')
print(d5.mount_point / 'logs' if d5 else '/tmp/archiver/logs')
" 2>/dev/null || echo "<d5>/logs")"

    _rpt "Download started at $(date '+%Y-%m-%d %H:%M:%S %Z')"
    _rpt ""

    DL_RC=0
    cd "$REPO_DIR" && uv run archiver download "${DOWNLOAD_ARGS[@]}" || DL_RC=$?

    _rpt "Download finished at $(date '+%Y-%m-%d %H:%M:%S %Z')"
    _rpt ""

    if [[ $DL_RC -eq 0 ]]; then
        record_step_pass "Download completed successfully (exit code 0)"
        ok "Download completed."
    else
        record_step_fail "Download finished with errors (exit code $DL_RC)"
        warn "Download finished with non-zero exit code ($DL_RC) — some models may have failed."
    fi
fi

flush_report

# ---------------------------------------------------------------------------
# ════════════════════════════════════════════════════════════════════════════
# STEP 4 — Post-download Status
# ════════════════════════════════════════════════════════════════════════════
# ---------------------------------------------------------------------------
step "Step 4 — Archive Status"
_rpt "## Step 4 — Archive Status"
_rpt ""

if $DRY_RUN; then
    warn "DRY RUN — status skipped (nothing was downloaded)"
    _rpt "_Dry run — status skipped._"
    _rpt ""
    record_step_warn "Status skipped (dry-run)"
else
    STATUS_OUT=$(cd "$REPO_DIR" && uv run archiver status 2>&1 || true)
    echo "$STATUS_OUT"

    _rpt "\`\`\`"
    echo "$STATUS_OUT" | while IFS= read -r l; do _rpt "$l"; done
    _rpt "\`\`\`"
    _rpt ""

    N_COMPLETE=$(echo "$STATUS_OUT" | grep -c "complete" 2>/dev/null || echo 0)
    N_FAILED=$(echo "$STATUS_OUT"   | grep -c "failed"   2>/dev/null || echo 0)
    record_step_pass "Status captured: ~$N_COMPLETE complete, ~$N_FAILED failed"
fi

flush_report

# ---------------------------------------------------------------------------
# ════════════════════════════════════════════════════════════════════════════
# STEP 5 — Archive Integrity Verification
# ════════════════════════════════════════════════════════════════════════════
# ---------------------------------------------------------------------------
step "Step 5 — Archive Integrity Verification"
_rpt "## Step 5 — Archive Integrity Verification"
_rpt ""

if $SKIP_VERIFY; then
    warn "Skipping verification (--skip-verify)"
    _rpt "_Verification skipped (--skip-verify)._"
    _rpt ""
    record_step_warn "Verification skipped"
elif $DRY_RUN; then
    warn "DRY RUN — verification skipped (nothing was downloaded)"
    _rpt "_Dry run — verification skipped._"
    _rpt ""
    record_step_warn "Verification skipped (dry-run)"
else
    # Read drive mount points from drives.yaml
    DRIVES_FILE="$REPO_DIR/config/drives.yaml"
    MOUNT_POINTS=()
    while IFS= read -r line; do
        mp=$(echo "$line" | grep "mount_point:" | awk '{print $2}' | tr -d '"')
        [[ -n "$mp" && -d "$mp" ]] && MOUNT_POINTS+=("$mp")
    done < "$DRIVES_FILE"

    if [[ ${#MOUNT_POINTS[@]} -eq 0 ]]; then
        warn "No mounted drives found — skipping verification"
        record_step_warn "Verification skipped (no drives mounted)"
    else
        info "Verifying drives: ${MOUNT_POINTS[*]}"

        # Determine report dir (d5/logs if available, else repo root)
        D5_LOGS=$(cd "$REPO_DIR" && uv run python3 -c "
import sys; sys.path.insert(0,'src')
from archiver.models import load_registry
from pathlib import Path
reg = load_registry(Path('config/registry.yaml'), Path('config/drives.yaml'))
d5 = reg.drives.get('d5')
p = d5.mount_point / 'logs' if d5 else Path('.')
p.mkdir(parents=True, exist_ok=True)
print(p)
" 2>/dev/null || echo "$REPO_DIR")

        VERIFY_ARGS=("--drives" "${MOUNT_POINTS[@]}" "--report-dir" "$D5_LOGS")
        $REHASH && VERIFY_ARGS+=("--rehash")
        $REHASH && info "Full re-hash requested — this will read every byte from disk (may take hours)."

        VERIFY_OUT=$(python3 "$REPO_DIR/verification/verify-archive.py" "${VERIFY_ARGS[@]}" 2>&1 \
                     || true)
        VERIFY_RC=$?
        echo "$VERIFY_OUT"

        # Find the most recent verify report
        VERIFY_REPORT=$(ls -t "$D5_LOGS"/verify-report-*.md 2>/dev/null | head -1 || echo "")

        _rpt "Verification method: $( $REHASH && echo "full re-hash" || echo "sidecar cross-check" )"
        _rpt ""
        _rpt "\`\`\`"
        # Embed summary section only (last ~30 lines which contain the summary)
        echo "$VERIFY_OUT" | tail -40 | while IFS= read -r l; do _rpt "$l"; done
        _rpt "\`\`\`"
        _rpt ""
        if [[ -n "$VERIFY_REPORT" ]]; then
            _rpt "Full verification report: \`$VERIFY_REPORT\`"
            _rpt ""
        fi

        if [[ $VERIFY_RC -eq 0 ]]; then
            record_step_pass "Archive integrity: all models passed"
            ok "Archive integrity: all models passed."
        else
            record_step_fail "Archive integrity: one or more models FAILED"
            warn "Archive integrity check found failures — see report above."
        fi
    fi
fi

flush_report

# ---------------------------------------------------------------------------
# ════════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ════════════════════════════════════════════════════════════════════════════
# ---------------------------------------------------------------------------
step "Run Summary"

TOTAL_STEPS=$(( STEP_PASS + STEP_WARN + STEP_FAIL ))
echo ""
echo -e "  Steps completed:   ${_C_BOLD}$TOTAL_STEPS${_C_RESET}"
echo -e "  ${_C_GREEN}Passed:${_C_RESET}            $STEP_PASS"
echo -e "  ${_C_YELLOW}Warnings:${_C_RESET}          $STEP_WARN"
echo -e "  ${_C_RED}Failed:${_C_RESET}            $STEP_FAIL"
echo ""

_rpt ""
_rpt "---"
_rpt ""
_rpt "## Run Summary"
_rpt ""
_rpt "| Metric | Value |"
_rpt "|--------|-------|"
_rpt "| Steps completed | $TOTAL_STEPS |"
_rpt "| ✔ Passed | $STEP_PASS |"
_rpt "| ⚠ Warnings | $STEP_WARN |"
_rpt "| ✗ Failed | $STEP_FAIL |"
_rpt "| Finished | $(date '+%Y-%m-%d %H:%M:%S %Z') |"
_rpt ""

if [[ $STEP_FAIL -eq 0 && $STEP_WARN -eq 0 ]]; then
    echo -e "${_C_GREEN}  ╔══════════════════════════════════════════════════════════════╗${_C_RESET}"
    echo -e "${_C_GREEN}  ║  ✔  Run complete — all steps passed.                        ║${_C_RESET}"
    echo -e "${_C_GREEN}  ╚══════════════════════════════════════════════════════════════╝${_C_RESET}"
    FINAL_STATUS="SUCCESS"
elif [[ $STEP_FAIL -eq 0 ]]; then
    echo -e "${_C_YELLOW}  ╔══════════════════════════════════════════════════════════════╗${_C_RESET}"
    echo -e "${_C_YELLOW}  ║  ⚠  Run complete with $STEP_WARN warning(s).                    ║${_C_RESET}"
    echo -e "${_C_YELLOW}  ╚══════════════════════════════════════════════════════════════╝${_C_RESET}"
    FINAL_STATUS="SUCCESS WITH WARNINGS ($STEP_WARN)"
else
    echo -e "${_C_RED}  ╔══════════════════════════════════════════════════════════════╗${_C_RESET}"
    echo -e "${_C_RED}  ║  ✗  Run finished with $STEP_FAIL failure(s).                    ║${_C_RESET}"
    echo -e "${_C_RED}  ╚══════════════════════════════════════════════════════════════╝${_C_RESET}"
    FINAL_STATUS="FAILED ($STEP_FAIL failures)"
fi

_rpt "> **Overall result: $FINAL_STATUS**"

finish_report "$FINAL_STATUS"
echo ""
print_report_path
echo ""

[[ $STEP_FAIL -gt 0 ]] && exit 1 || exit 0
