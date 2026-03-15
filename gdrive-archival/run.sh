#!/usr/bin/env bash
# Run GDrive backup (extra paths + curated models). Uses rclone; config via RCLONE_CONFIG or default location.
set -e
cd "$(dirname "$0")"

# Prefer explicit config so we don't touch default ~/.config/rclone/rclone.conf
if [[ -n "$RCLONE_CONFIG" ]]; then
  export RCLONE_CONFIG
elif [[ -f "$HOME/Downloads/rclone.conf" ]]; then
  export RCLONE_CONFIG="$HOME/Downloads/rclone.conf"
elif [[ -f ./rclone.conf ]]; then
  export RCLONE_CONFIG="$(pwd)/rclone.conf"
fi

if [[ -z "$RCLONE_CONFIG" || ! -f "$RCLONE_CONFIG" ]]; then
  echo "rclone config not found. Set RCLONE_CONFIG to your rclone.conf path, or put rclone.conf in this dir or ~/Downloads." >&2
  exit 1
fi

# If the archiver has queued a metadata upload (run_state or archive changed), run extra first.
python3 backup.py backup-extra-if-pending
python3 backup.py backup-gguf
python3 backup.py backup-full
