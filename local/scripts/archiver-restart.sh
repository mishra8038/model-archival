#!/usr/bin/env bash
# =============================================================================
# scripts/archiver-restart.sh
# Gracefully restart the archiver screen session.
#
# Usage:
#   bash scripts/archiver-restart.sh
#
# This will:
#   1) Change to the project root
#   2) Run stop.sh to halt the current archiver run cleanly (resumable)
#   3) Kill any leftover 'archiver' screen sessions (and their child PIDs)
#   4) Start a fresh screen session named "archiver" running run.sh --all
# =============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

echo "[archiver-restart] Stopping existing archiver run (if any)..."
bash stop.sh || true

echo "[archiver-restart] Killing leftover 'archiver' screen sessions (if any)..."
if screen -ls 2>/dev/null | grep -q "\.archiver"; then
    # Extract all screen IDs with name 'archiver' and kill them
    screen -ls | awk '/\.archiver[[:space:]]/ {print $1}' | while read -r sid; do
        echo "  - Killing screen session: $sid"
        screen -S "${sid%%.*}" -X quit || true
    done
fi

echo "[archiver-restart] Starting new screen session: archiver"
screen -S archiver -dm bash run.sh --all

echo "[archiver-restart] Done. Attach with:  screen -r archiver"

