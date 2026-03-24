#!/usr/bin/env bash
# Upload only from upload_staging dirs (D3/D5) → GDrive folder in config.yaml.
set -e
cd "$(dirname "$0")"

if [[ -n "$RCLONE_CONFIG" ]]; then
  export RCLONE_CONFIG
elif [[ -f "$HOME/Downloads/rclone.conf" ]]; then
  export RCLONE_CONFIG="$HOME/Downloads/rclone.conf"
elif [[ -f ./rclone.conf ]]; then
  export RCLONE_CONFIG="$(pwd)/rclone.conf"
fi

if [[ -z "$RCLONE_CONFIG" || ! -f "$RCLONE_CONFIG" ]]; then
  echo "rclone config not found. Set RCLONE_CONFIG, or use ./rclone.conf or ~/Downloads/rclone.conf" >&2
  exit 1
fi

exec python3 backup.py backup-staging
