#!/usr/bin/env bash
# Create layout on archival VM under D5. Run once (or anytime after new mount).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "${ROOT}/config/env-archive-vm-vllm.sh"
mkdir -p "${VLLM_ARCHIVE_ROOT}/state" "${VLLM_ARCHIVE_ROOT}/logs" "${HF_HUB_CACHE}" "${TRANSFORMERS_CACHE}"
touch "${VLLM_ARCHIVE_ROOT}/state/.gitkeep"
echo "OK: ${VLLM_ARCHIVE_ROOT} ready (HF_HOME=${HF_HOME})"
