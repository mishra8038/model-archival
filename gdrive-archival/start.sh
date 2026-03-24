#!/usr/bin/env bash
# Start GDrive upload in a detached screen session.
# Always runs stop.sh first so stray screen sessions, Python upload workers, and
# matching rclone jobs are torn down before a new upload starts.
#
# Usage:
#   bash start.sh              # registry upload (gdrive-registry.yaml)
#   bash start.sh registry     # same
#   bash start.sh staging      # upload_staging dirs only (backup-staging)
#
# Attach: screen -r gdrive-upload   or   screen -r gdrive-staging
# Stop:   bash stop.sh
#
# Set START_SKIP_STOP=1 to skip the initial stop (not recommended).

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
cd "$SCRIPT_DIR"

MODE="${1:-registry}"

if [[ -z "$RCLONE_CONFIG" ]]; then
  if [[ -f "$SCRIPT_DIR/rclone.conf" ]]; then
    export RCLONE_CONFIG="$SCRIPT_DIR/rclone.conf"
  elif [[ -f "$HOME/Downloads/rclone.conf" ]]; then
    export RCLONE_CONFIG="$HOME/Downloads/rclone.conf"
  fi
fi

if [[ -z "$RCLONE_CONFIG" || ! -f "$RCLONE_CONFIG" ]]; then
  echo "rclone config not found. Set RCLONE_CONFIG or add ./rclone.conf / ~/Downloads/rclone.conf" >&2
  exit 1
fi

mkdir -p "$SCRIPT_DIR/logs"

if [[ "${START_SKIP_STOP:-0}" != "1" ]]; then
  echo "Cleaning previous GDrive upload processes (stop.sh)…"
  bash "$SCRIPT_DIR/stop.sh" || true
  sleep 1
fi

case "$MODE" in
  registry)
    SESSION=gdrive-upload
    if screen -ls 2>/dev/null | grep -q "\.${SESSION}[[:space:]]"; then
      echo "Screen '$SESSION' still present after stop. Quit manually: screen -S $SESSION -X quit" >&2
      exit 1
    fi
    LOG="$SCRIPT_DIR/logs/registry-upload.log"
    screen -S "$SESSION" -dm bash -c "cd '$SCRIPT_DIR' && export RCLONE_CONFIG='${RCLONE_CONFIG}' && exec python3 -u backup.py backup-registry >>'$LOG' 2>&1"
    echo "Started GDrive registry upload in screen '$SESSION'."
    echo "  log: tail -f $LOG"
    echo "  attach: screen -r $SESSION"
    echo "  progress: logs/registry-upload-state.json + logs/GDRIVE-REGISTRY-UPLOAD-STATUS.md"
    ;;
  staging)
    SESSION=gdrive-staging
    if screen -ls 2>/dev/null | grep -q "\.${SESSION}[[:space:]]"; then
      echo "Screen '$SESSION' still present after stop. Quit manually: screen -S $SESSION -X quit" >&2
      exit 1
    fi
    LOG="$SCRIPT_DIR/logs/staging-upload.log"
    screen -S "$SESSION" -dm bash -c "cd '$SCRIPT_DIR' && export RCLONE_CONFIG='${RCLONE_CONFIG}' && exec python3 -u backup.py backup-staging >>'$LOG' 2>&1"
    echo "Started GDrive staging upload in screen '$SESSION'."
    echo "  log: tail -f $LOG"
    echo "  attach: screen -r $SESSION"
    ;;
  *)
    echo "Usage: bash start.sh [registry|staging]" >&2
    exit 2
    ;;
esac
