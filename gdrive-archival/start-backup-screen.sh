#!/usr/bin/env bash
# Start GDrive backup in a screen session. Run from repo root or from gdrive-archival/.
# Usage: bash gdrive-archival/start-backup-screen.sh
# Attach later: screen -r gdrive-backup

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
cd "$SCRIPT_DIR"

if screen -ls 2>/dev/null | grep -q '\.gdrive-backup\s'; then
  echo "Screen session 'gdrive-backup' already exists. Attach with: screen -r gdrive-backup"
  exit 0
fi

# Ensure rclone config is findable (run.sh will use RCLONE_CONFIG or default paths)
if [[ -z "$RCLONE_CONFIG" ]]; then
  if [[ -f "$SCRIPT_DIR/rclone.conf" ]]; then
    export RCLONE_CONFIG="$SCRIPT_DIR/rclone.conf"
  elif [[ -f "$HOME/Downloads/rclone.conf" ]]; then
    export RCLONE_CONFIG="$HOME/Downloads/rclone.conf"
  fi
fi

screen -S gdrive-backup -dm bash -c "cd '$SCRIPT_DIR' && export RCLONE_CONFIG='${RCLONE_CONFIG:-}' && exec bash run.sh"
echo "Started GDrive backup in screen 'gdrive-backup'. Attach with: screen -r gdrive-backup"
