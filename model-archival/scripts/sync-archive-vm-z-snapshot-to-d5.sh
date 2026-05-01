#!/usr/bin/env bash
# Copy ~/z on the archival VM to /mnt/models/d5/<SNAP_NAME> (one rsync pass; additive).
#
# From a machine that can SSH to the VM (LAN / VPN):
#   SNAP_NAME=z05012026 ./scripts/sync-archive-vm-z-snapshot-to-d5.sh
#   ARCHIVAL_VM=x@192.168.8.65 SNAP_NAME=z05012026 ./scripts/sync-archive-vm-z-snapshot-to-d5.sh --dry-run
#
# Optional: VM_SSHPASS in env for sshpass (same pattern as ollama-sync / ollama-archive-vm-maintain).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO"

ARCHIVAL_VM="${ARCHIVAL_VM:-x@192.168.8.65}"
SNAP_NAME="${SNAP_NAME:-z05012026}"
DEST_PARENT="${DEST_PARENT:-/mnt/models/d5}"

_remote_args=("$SNAP_NAME" "$DEST_PARENT")
if [[ "${1:-}" == "--dry-run" ]]; then
  _remote_args+=(--dry-run)
fi

vm_ssh=(ssh -o ConnectTimeout=30 -o BatchMode=yes)
if [[ -n "${VM_SSHPASS:-}" ]]; then
  vm_ssh=(sshpass -e ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30)
fi

echo "Archival VM: $ARCHIVAL_VM  snap: $SNAP_NAME  dest: $DEST_PARENT/$SNAP_NAME" >&2
# Remote: mirror contents of $HOME/z into dated dir on D5 (/mnt/models/d5 per vm-operations.mdc).
"${vm_ssh[@]}" "$ARCHIVAL_VM" bash -s "${_remote_args[@]}" <<'REMOTE'
set -euo pipefail
snap="${1:?snap name}"
parent="${2:?dest parent}"
shift 2 || true
dry=()
[[ "${1:-}" == "--dry-run" ]] && dry=(--dry-run)
src="${HOME}/z"
dst="${parent}/${snap}"
if [[ ! -d "$src" ]]; then
  echo "error: missing source dir: $src" >&2
  exit 1
fi
mkdir -p "$dst"
# -a archive, -H hardlinks as hardlinks
rsync -aH "${dry[@]}" --info=progress2 "${src}/" "${dst}/"
echo "done: ${dst}" >&2
REMOTE
