#!/usr/bin/env bash
# Start staging-only GDrive upload in screen. Usage: bash gdrive-archival/start-staging-screen.sh
# Attach: screen -r gdrive-staging

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
cd "$SCRIPT_DIR"

if screen -ls 2>/dev/null | grep -q '\.gdrive-staging\s'; then
  echo "Screen session 'gdrive-staging' already exists. Attach with: screen -r gdrive-staging"
  exit 0
fi

if [[ -z "$RCLONE_CONFIG" ]]; then
  if [[ -f "$SCRIPT_DIR/rclone.conf" ]]; then
    export RCLONE_CONFIG="$SCRIPT_DIR/rclone.conf"
  elif [[ -f "$HOME/Downloads/rclone.conf" ]]; then
    export RCLONE_CONFIG="$HOME/Downloads/rclone.conf"
  fi
fi

screen -S gdrive-staging -dm bash -c "cd '$SCRIPT_DIR' && export RCLONE_CONFIG='${RCLONE_CONFIG:-}' && exec bash run-staging.sh"
echo "Started GDrive staging upload in screen 'gdrive-staging'. Attach with: screen -r gdrive-staging"
