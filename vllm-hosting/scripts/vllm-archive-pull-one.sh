#!/usr/bin/env bash
# Pull the next single HF repo from vllm-archive-manifest.yaml (sequential queue).
# Run on archival VM after: source vllm-hosting/config/env-archive-vm-vllm.sh
#
# Default: trickle 2048 KiB/s down (~2 MiB/s). Override: THROTTLE_KBPS=4096 USE_TRICKLE=1
# Disable cap: USE_TRICKLE=0
#
set -euo pipefail
VLLM_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "${VLLM_ROOT}/config/env-archive-vm-vllm.sh"

THROTTLE_KBPS="${THROTTLE_KBPS:-2048}"
export THROTTLE_KBPS

if [[ -n "${MODEL_ARCHIVAL_UV_ROOT:-}" && -f "${MODEL_ARCHIVAL_UV_ROOT}/pyproject.toml" ]]; then
  exec uv run --directory "${MODEL_ARCHIVAL_UV_ROOT}" python "${VLLM_ROOT}/scripts/vllm_archive_pull_one.py" "$@"
fi
exec python3 "${VLLM_ROOT}/scripts/vllm_archive_pull_one.py" "$@"
