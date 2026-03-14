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
#   --priority-only 1     Only download P1 (token-free) models
#   --tier A|B|C|D        Restrict downloads to one tier
#   --all                 Download all models (P1 + P2; token required for P2)  [default]
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

# Parent of scripts/ so deploy/, config/, src/ and pyproject.toml are under REPO_DIR
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_DIR/deploy/_common.sh"

# ---------------------------------------------------------------------------
# Graceful shutdown — trap SIGINT / SIGTERM and forward to the archiver child
# ---------------------------------------------------------------------------
_ARCHIVER_PID=""
_SHUTDOWN_REQUESTED=false

_graceful_shutdown() {
    if $_SHUTDOWN_REQUESTED; then return; fi
    _SHUTDOWN_REQUESTED=true
    echo ""
    warn "Shutdown signal received — waiting for archiver to finish current shard…"
    warn "  (send signal again to force-kill immediately)"
    if [[ -n "$_ARCHIVER_PID" ]] && kill -0 "$_ARCHIVER_PID" 2>/dev/null; then
        kill -SIGTERM "$_ARCHIVER_PID" 2>/dev/null || true
        # Give it up to 5 minutes to flush current shard + write state
        local deadline=$(( $(date +%s) + 300 ))
        while kill -0 "$_ARCHIVER_PID" 2>/dev/null; do
            if [[ $(date +%s) -ge $deadline ]]; then
                warn "Timeout — force-killing archiver (pid $_ARCHIVER_PID)"
                kill -SIGKILL "$_ARCHIVER_PID" 2>/dev/null || true
                break
            fi
            sleep 2
        done
    fi
    warn "Archiver stopped. Downloads are resumable — run again to continue."
    exit 130
}

trap '_graceful_shutdown' SIGINT SIGTERM

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DRY_RUN=false
PRIORITY_ONLY=""       # empty = download all priorities (P1 + P2)
TIER=""
DOWNLOAD_ALL=true      # default: download everything
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
_rpt "| Priority filter | ${PRIORITY_ONLY:-all (P1 + P2)} |"
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
# Guard: uv must exist, then ensure .venv is up to date
# ---------------------------------------------------------------------------
if ! command -v uv &>/dev/null; then
    error "uv not found in PATH. Run deploy/setup-mxlinux.sh or deploy/setup-artix.sh first."
fi

# Always run uv sync to ensure the venv is present and dependencies are current.
# This is fast (no-op) if nothing has changed.
info "Syncing Python environment (uv sync)…"
if uv sync --project "$REPO_DIR" 2>&1; then
    ok "uv sync — environment up to date"
else
    error "uv sync failed — check pyproject.toml and network access."
fi

# ---------------------------------------------------------------------------
# HF Token — load from ~/.hf_token if not already in environment
# ---------------------------------------------------------------------------
if [[ -z "${HF_TOKEN:-}" ]]; then
    if [[ -f "$HOME/.hf_token" ]]; then
        HF_TOKEN=$(cat "$HOME/.hf_token")
        export HF_TOKEN
        ok "HF_TOKEN loaded from ~/.hf_token"
    else
        warn "HF_TOKEN not set and ~/.hf_token not found."
        warn "Gated models (Priority 2) will be skipped."
        warn "Set token with:  bash deploy/sethfToken.sh hf_YOURTOKEN"
    fi
else
    ok "HF_TOKEN already set in environment"
fi

# Redact token in report — show only first 6 chars
TOKEN_DISPLAY="${HF_TOKEN:+${HF_TOKEN:0:6}…(redacted)}"
_rpt "| HF Token | ${TOKEN_DISPLAY:-not set} |"
_rpt ""
flush_report

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
    ENV_PASS=$(grep -c "PASS" "$ENV_OUT_FILE" 2>/dev/null || true); ENV_PASS=${ENV_PASS:-0}
    ENV_WARN=$(grep -c "WARN" "$ENV_OUT_FILE" 2>/dev/null || true); ENV_WARN=${ENV_WARN:-0}
    ENV_FAIL=$(grep -c "FAIL" "$ENV_OUT_FILE" 2>/dev/null || true); ENV_FAIL=${ENV_FAIL:-0}

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

    if [[ $ENV_FAIL -gt 0 ]]; then
        if $DRY_RUN; then
            # In dry-run: treat env failures as warnings — the VM will have everything installed
            record_step_warn "Environment check: $ENV_FAIL tool(s) missing (expected on dev machine — VM setup scripts install them)"
            warn "Environment check: $ENV_FAIL tool(s) missing — acceptable on dev machine, must be fixed on the VM before a real run"
        else
            record_step_fail "Environment check: $ENV_FAIL failure(s) — cannot proceed"
            error "Environment check failed — fix the issues above before running downloads."
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
# STEP 1b — Drive Mount Check  (fast, always run, blocks real downloads)
# ════════════════════════════════════════════════════════════════════════════
# ---------------------------------------------------------------------------
step "Step 1b — Drive Mount Check"
_rpt "## Step 1b — Drive Mount Check"
_rpt ""
_rpt "| Drive | Mount | Mounted | Writable | Free |"
_rpt "|-------|-------|---------|----------|------|"

DRIVES_FILE="$REPO_DIR/config/drives.yaml"
DRIVES_ALL_OK=true

while IFS= read -r line; do
    # Match lines like: "d1:", "d2:", etc.
    if [[ "$line" =~ ^(d[0-9]+): ]]; then
        CURRENT_LABEL="${BASH_REMATCH[1]}"
    fi
    if [[ "$line" =~ mount_point:\ *(.+) && -n "${CURRENT_LABEL:-}" ]]; then
        MP="${BASH_REMATCH[1]}"
        MP="${MP//\"/}"   # strip quotes

        # Check exists and is a real separate mount (not root fs)
        if [[ ! -d "$MP" ]]; then
            echo -e "      ${_C_RED}✗  FAIL${_C_RESET}  Drive $CURRENT_LABEL ($MP): NOT MOUNTED — directory does not exist"
            _rpt "| $CURRENT_LABEL | $MP | ✗ not mounted | — | — |"
            DRIVES_ALL_OK=false
        else
            MP_DEV=$(stat -c '%d' "$MP" 2>/dev/null || echo "0")
            ROOT_DEV=$(stat -c '%d' / 2>/dev/null || echo "1")
            if [[ "$MP_DEV" == "$ROOT_DEV" ]]; then
                warn "Drive $CURRENT_LABEL ($MP): on root filesystem — not a separate disk mount"
                _rpt "| $CURRENT_LABEL | $MP | ⚠ on root fs | — | — |"
                DRIVES_ALL_OK=false
            else
                # Writable?
                TEST_FILE="$MP/.run_write_test_$$"
                if touch "$TEST_FILE" 2>/dev/null; then
                    rm -f "$TEST_FILE"
                    WRITABLE="✔"
                else
                    WRITABLE="✗ not writable"
                    DRIVES_ALL_OK=false
                fi
                # Free space
                FREE_B=$(df -B1 "$MP" 2>/dev/null | tail -1 | awk '{print $4}' || echo "0")
                FREE_GB=$(echo "scale=1; $FREE_B/1073741824" | bc 2>/dev/null || echo "?")
                ok "Drive $CURRENT_LABEL: $MP  free=${FREE_GB} GB  writable=${WRITABLE}"
                _rpt "| $CURRENT_LABEL | $MP | ✔ mounted | $WRITABLE | ${FREE_GB} GB |"
            fi
        fi
        CURRENT_LABEL=""
    fi
done < "$DRIVES_FILE"

_rpt ""

if $DRIVES_ALL_OK; then
    record_step_pass "All drives mounted and writable"
else
    if ! $DRY_RUN; then
        record_step_fail "One or more drives not mounted/writable — cannot start downloads"
        error "Drive check failed. Run deploy/vm-mount-disks.sh on the VM first, then retry."
    else
        record_step_warn "Drive check: some drives not mounted (expected in dry-run on dev machine)"
        warn "Drive mount issues noted — must be resolved on the VM before real downloads."
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
DOWNLOAD_ARGS=("--all")   # always pass --all; filters narrow it down
[[ -n "$TIER" ]]          && DOWNLOAD_ARGS+=("--tier" "$TIER")
[[ -n "$PRIORITY_ONLY" ]] && DOWNLOAD_ARGS+=("--priority-only" "$PRIORITY_ONLY")
[[ -n "$BANDWIDTH_CAP" ]] && DOWNLOAD_ARGS+=("--bandwidth-cap" "$BANDWIDTH_CAP")
DOWNLOAD_ARGS+=("--max-parallel-drives" "$MAX_PARALLEL")

info "Running dry-run to capture download plan…"
PLAN_RC=0
PLAN_OUT=$(cd "$REPO_DIR" && uv run archiver download "${DOWNLOAD_ARGS[@]}" --dry-run 2>&1) || PLAN_RC=$?
echo "$PLAN_OUT"

_rpt "\`\`\`"
echo "$PLAN_OUT" | while IFS= read -r l; do _rpt "$l"; done
_rpt "\`\`\`"
_rpt ""

# A non-zero exit here means pre-flight caught a missing tool (e.g. aria2c on dev machine).
# That is expected and correct — it will pass on the VM. Only flag as failure if it's a
# Python traceback / config error (i.e. the plan output contains "Traceback" or "Error:").
if echo "$PLAN_OUT" | grep -q "Traceback\|Error: No such\|ImportError\|ModuleNotFoundError"; then
    record_step_fail "Download plan: Python/config error detected"
elif echo "$PLAN_OUT" | grep -qi "Pre-flight FAILED" && ! $DRY_RUN; then
    record_step_fail "Download plan: pre-flight failure (on the VM, not dry-run)"
else
    MODEL_COUNT=$(echo "$PLAN_OUT" | grep -c "│" 2>/dev/null || echo "?")
    if [[ $PLAN_RC -ne 0 ]]; then
        record_step_warn "Download plan shown (pre-flight noted missing tools — install on VM first)"
    else
        record_step_pass "Download plan generated ($MODEL_COUNT table rows shown above)"
    fi
fi

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
    # Resolve logs dir for display
    LOGS_DIR=$(cd "$REPO_DIR" && uv run python3 -c "
import sys; sys.path.insert(0,'src')
from archiver.models import load_registry
from pathlib import Path
reg = load_registry(Path('config/registry.yaml'), Path('config/drives.yaml'))
d5 = reg.drives.get('d5')
print(d5.mount_point / 'logs' if d5 else '/tmp/archiver/logs')
" 2>/dev/null || echo "/tmp/archiver/logs")

    info "Logs directory → $LOGS_DIR"
    _rpt "Download started at $(date '+%Y-%m-%d %H:%M:%S %Z')"
    _rpt "Logs: \`$LOGS_DIR\`"
    _rpt ""

    # ── screen detection ─────────────────────────────────────────────────────
    # If we are NOT already inside a screen/tmux session, warn loudly and offer
    # to launch inside screen.  Downloads run for many hours; an SSH disconnect
    # without screen will kill the process and waste progress.
    IN_SCREEN=false
    [[ -n "${STY:-}"  ]] && IN_SCREEN=true   # screen sets $STY
    [[ -n "${TMUX:-}" ]] && IN_SCREEN=true   # tmux sets $TMUX

    if ! $IN_SCREEN; then
        if command -v screen &>/dev/null; then
            echo ""
            echo -e "  ${_C_YELLOW}┌──────────────────────────────────────────────────────────────┐${_C_RESET}"
            echo -e "  ${_C_YELLOW}│  ⚠  WARNING: not running inside screen or tmux.              │${_C_RESET}"
            echo -e "  ${_C_YELLOW}│     An SSH disconnect will kill the download.                 │${_C_RESET}"
            echo -e "  ${_C_YELLOW}│     Recommended: run inside screen:                          │${_C_RESET}"
            echo -e "  ${_C_YELLOW}│       screen -S archiver                                     │${_C_RESET}"
            echo -e "  ${_C_YELLOW}│       bash run.sh [OPTIONS]                                  │${_C_RESET}"
            echo -e "  ${_C_YELLOW}│                                                              │${_C_RESET}"
            echo -e "  ${_C_YELLOW}│     Proceeding in foreground in 10 seconds...                │${_C_RESET}"
            echo -e "  ${_C_YELLOW}│     Press Ctrl+C to abort, then start inside screen.         │${_C_RESET}"
            echo -e "  ${_C_YELLOW}└──────────────────────────────────────────────────────────────┘${_C_RESET}"
            echo ""
            _rpt "> ⚠ Download started outside screen/tmux — SSH disconnect risk."
            sleep 10
        else
            warn "screen not installed — cannot protect against SSH disconnects."
            warn "Consider: sudo apt install screen  then: screen -S archiver"
            _rpt "> ⚠ screen not installed — SSH disconnect will kill the download."
        fi
    else
        ok "Running inside screen/tmux — safe from SSH disconnects."
        _rpt "> ✔ Running inside screen/tmux session."
    fi

    # ── Run download ──────────────────────────────────────────────────────────
    info "Starting download — this may run for hours."
    info "  To stop gracefully:  kill -SIGTERM \$\$  (or Ctrl+C in this terminal)"
    info "  Or run:              bash $REPO_DIR/stop.sh"
    DL_RC=0
    cd "$REPO_DIR" && uv run archiver download "${DOWNLOAD_ARGS[@]}" &
    _ARCHIVER_PID=$!
    echo "$_ARCHIVER_PID" > "$REPO_DIR/.archiver.pid"
    wait "$_ARCHIVER_PID" || DL_RC=$?
    rm -f "$REPO_DIR/.archiver.pid"
    _ARCHIVER_PID=""

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

    N_COMPLETE=$(echo "$STATUS_OUT" | grep -c "complete" 2>/dev/null || true); N_COMPLETE=${N_COMPLETE:-0}
    N_FAILED=$(echo "$STATUS_OUT"   | grep -c "failed"   2>/dev/null || true); N_FAILED=${N_FAILED:-0}
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
