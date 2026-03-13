#!/usr/bin/env bash
# =============================================================================
# stop.sh — Gracefully stop a running archiver session
#
# Sends SIGTERM to the archiver process. The archiver will finish the current
# shard in progress, flush run_state.json, and exit cleanly. Downloads are
# fully resumable — run `bash run.sh --all` again to continue from where it
# left off.
#
# Usage:
#   bash stop.sh              # stop gracefully (finish current shard)
#   bash stop.sh --force      # force-kill immediately (partial shard lost, but
#                             #   aria2 .control files preserve byte offsets)
#   bash stop.sh --status     # show current archiver PID and state
# =============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$REPO_DIR/.archiver.pid"

FORCE=false
STATUS_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --force)  FORCE=true ;;
        --status) STATUS_ONLY=true ;;
        *) echo "Unknown option: $arg"; exit 1 ;;
    esac
done

# ── Find the archiver PID ────────────────────────────────────────────────────
ARCHIVER_PID=""

if [[ -f "$PID_FILE" ]]; then
    ARCHIVER_PID=$(cat "$PID_FILE" 2>/dev/null || true)
fi

# Fall back to process search if PID file is stale or missing
if [[ -z "$ARCHIVER_PID" ]] || ! kill -0 "$ARCHIVER_PID" 2>/dev/null; then
    ARCHIVER_PID=$(pgrep -f "archiver download" 2>/dev/null | head -1 || true)
fi

if [[ -z "$ARCHIVER_PID" ]]; then
    echo "No running archiver process found."
    exit 0
fi

# ── Status mode ──────────────────────────────────────────────────────────────
if $STATUS_ONLY; then
    echo "Archiver running: PID $ARCHIVER_PID"
    ps -p "$ARCHIVER_PID" -o pid,stat,etime,cmd 2>/dev/null || true
    exit 0
fi

# ── Send signal ──────────────────────────────────────────────────────────────
if $FORCE; then
    echo "Force-killing archiver (PID $ARCHIVER_PID)…"
    kill -SIGKILL "$ARCHIVER_PID" 2>/dev/null || true
    rm -f "$PID_FILE"
    echo "Done. Partial shards are preserved — aria2 control files intact."
else
    echo "Sending SIGTERM to archiver (PID $ARCHIVER_PID)…"
    echo "  The archiver will finish the current shard then exit cleanly."
    echo "  To force-kill immediately:  bash stop.sh --force"
    kill -SIGTERM "$ARCHIVER_PID" 2>/dev/null || true

    # Wait for process to exit (up to 5 minutes for a large shard)
    echo -n "  Waiting for clean exit"
    deadline=$(( $(date +%s) + 300 ))
    while kill -0 "$ARCHIVER_PID" 2>/dev/null; do
        if [[ $(date +%s) -ge $deadline ]]; then
            echo ""
            echo "Timeout waiting for clean exit. Use --force to kill immediately."
            exit 1
        fi
        echo -n "."
        sleep 3
    done
    echo " done."
    rm -f "$PID_FILE"
    echo "Archiver stopped cleanly. Run 'bash run.sh --all' to resume."
fi
