#!/usr/bin/env bash
# Remove Ollama *partial* blobs and .rsync-partial dirs on all configured archival roots; verify
# manifest↔blob integrity. Run from a workstation with SSH to the archival VM (same as ollama-sync).
#
#   ARCHIVAL_VM=ubuntu@192.168.8.32 ./scripts/ollama-archive-vm-maintain.sh
#   ARCHIVAL_VM_SITE_CYCLE='d5=/mnt/models/d5/foo,...' ./scripts/ollama-archive-vm-maintain.sh
#
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
ARCHIVAL_VM="${ARCHIVAL_VM:-ubuntu@192.168.8.32}"

vm_ssh=(ssh -o ConnectTimeout=20 -o BatchMode=yes)
if [[ -n "${VM_SSHPASS:-}" ]]; then
  vm_ssh=(sshpass -e ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20)
fi

mapfile -t _roots < <(python3 "$REPO/scripts/ollama_archival_rotation.py" print-archive-roots \
  ${ARCHIVAL_VM_SITE_CYCLE:+--cycle "$ARCHIVAL_VM_SITE_CYCLE"})
if [[ "${#_roots[@]}" -eq 0 ]]; then
  echo "error: no archive roots (print-archive-roots empty)" >&2
  exit 1
fi
_maint_args=()
if [[ "${OLLAMA_MAINTAIN_KEEP_PARTIALS:-0}" == "1" ]]; then
  _maint_args+=(--keep-ollama-partials)
  echo "Maintaining (preserving Ollama *partial* blobs) …" >&2
else
  echo "Maintaining ${#_roots[@]} root(s) on $ARCHIVAL_VM …" >&2
fi
cat "$REPO/scripts/ollama_archive_vm_maintain.py" | "${vm_ssh[@]}" "$ARCHIVAL_VM" python3 - "${_maint_args[@]}" "${_roots[@]}"
