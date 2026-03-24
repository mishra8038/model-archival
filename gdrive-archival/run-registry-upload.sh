#!/usr/bin/env bash
# Upload from gdrive-registry.yaml (verify + rclone --checksum, transfers=1).
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
  echo "rclone config not found. Set RCLONE_CONFIG or use ./rclone.conf / ~/Downloads/rclone.conf" >&2
  exit 1
fi

# -u: line-buffered stdout so logs/registry-upload.log updates live when redirected
exec python3 -u upload_registry.py "$@"
