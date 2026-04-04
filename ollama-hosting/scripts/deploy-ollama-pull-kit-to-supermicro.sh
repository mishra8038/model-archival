#!/usr/bin/env bash
# Push canonical pull queue + registry + on-host pull scripts to Supermicro: ~/z/dev/ollama/
#
# Expected layout on the GPU host (after deploy):
#   ~/z/dev/ollama/registry/{OLLAMA_MODEL_REGISTRY.json,ollama_registry_tool.py,...}
#   ~/z/dev/ollama/scripts/{ollama-pull-queue,...}
#
# Then SSH in (or use trigger-ollama-pull-on-supermicro.sh) and run ollama-pull-queue.
# After pulls complete, run ollama-registry-sync (or ollama-sync.sh) from a host that can
# reach Supermicro + archival VM to copy ~/.ollama blobs onto archive disks.
#
# Environment:
#   OLLAMA_SUPERMICRO_SSH   e.g. x@192.168.8.106 (required unless passed as $1)
#   OLLAMA_SUPERMICRO_ROOT  remote path (default: ~/z/dev/ollama)
#   OLLAMA_HOSTING          local ollama-hosting root (default: parent of scripts/)
#   RSYNC_EXTRA             extra rsync args (e.g. --dry-run)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OLLAMA_HOSTING="${OLLAMA_HOSTING:-$(cd "$SCRIPT_DIR/.." && pwd)}"
REMOTE="${OLLAMA_SUPERMICRO_SSH:-${1:-}}"
if [[ -z "$REMOTE" ]]; then
  echo "Usage: OLLAMA_SUPERMICRO_SSH=user@host $0   or   $0 user@host" >&2
  exit 2
fi

ROOT="${OLLAMA_SUPERMICRO_ROOT:-~/z/dev/ollama}"
RSYNC=(rsync -avz)
# shellcheck disable=SC2206
[[ -n "${RSYNC_EXTRA:-}" ]] && RSYNC+=($RSYNC_EXTRA)

echo "Deploy pull kit → ${REMOTE}:${ROOT}" >&2
ssh -o BatchMode=yes "$REMOTE" "mkdir -p ${ROOT}/registry ${ROOT}/scripts ${ROOT}/logs"

"${RSYNC[@]}" --delete \
  "$OLLAMA_HOSTING/registry/" \
  "${REMOTE}:${ROOT}/registry/"

for f in \
  ollama-pull-queue \
  ollama-clean-partials \
  ollama-cleanup-partials.sh \
  pull-ollama-stack.sh \
  pull-ollama-70b-stack.sh \
  pull-ollama-uncensored.sh \
  ; do
  "${RSYNC[@]}" "$OLLAMA_HOSTING/scripts/$f" "${REMOTE}:${ROOT}/scripts/$f"
done

ssh -o BatchMode=yes "$REMOTE" "chmod +x ${ROOT}/scripts/"* 2>/dev/null || true

echo "Deployed. On Supermicro:" >&2
echo "  export OLLAMA_HOST=127.0.0.1:11434" >&2
echo "  ${ROOT}/scripts/ollama-pull-queue --one" >&2
