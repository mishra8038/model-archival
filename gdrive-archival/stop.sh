#!/usr/bin/env bash
# Stop GDrive upload jobs: screen sessions + Python upload workers + rclone copies
# that source /mnt/models (registry upload). Safe when nothing is running.

set +e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

_quit_screen() {
  local name="$1"
  if screen -ls 2>/dev/null | grep -q "\.${name}[[:space:]]"; then
    screen -S "$name" -X quit 2>/dev/null
    echo "Stopped screen session: $name"
  fi
}

echo "GDrive stop — cleaning sessions and processes under $SCRIPT_DIR"

# Screen names we have used (old + new)
for s in gdrive-upload gdrive-registry gdrive-staging gdrive-backup; do
  _quit_screen "$s"
done

# Processes matching registry or staging upload (not other backup.py uses elsewhere)
_kill_pattern() {
  local pat="$1"
  local pids
  pids=$(pgrep -f "$pat" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    echo "Sending SIGTERM to PIDs: $pids ($pat)"
    kill $pids 2>/dev/null
    sleep 2
    pids=$(pgrep -f "$pat" 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
      echo "Sending SIGKILL to PIDs: $pids"
      kill -9 $pids 2>/dev/null
    fi
  fi
}

_kill_pattern "[Pp]ython3.*backup\.py backup-registry"
_kill_pattern "[Pp]ython3.*backup\.py backup-staging"
_kill_pattern "[Pp]ython3.*upload_registry\.py"
_kill_pattern "bash.*run-staging\.sh"
_kill_pattern "bash.*run-registry-upload\.sh"

# Registry uploads always use local path /mnt/models/... → gdrive:
# (Narrower than all rclone-to-gdrive so unrelated remotes are left alone.)
_kill_pattern "rclone copy /mnt/models"

echo "GDrive stop finished."
