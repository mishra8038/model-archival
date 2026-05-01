#!/usr/bin/env bash
# vLLM archiver slice — **registry only:** config/registry-vllm.yaml (do not substitute
# registry.yaml, final_registry.yaml, or specialists registries for this job).
# Weights: registry-vllm.yaml → /mnt/models/d5/vllm/{raw,uncensored}/… (d5_vllm in drives.yaml)
# Scratch remains on D1/.tmp. Infra (STATUS, run_state) stays on D3.
# Bandwidth: flat 2 MB/s (mebibytes/s; aria2 global cap for LFS; XET/hf_hub not capped by aria2).
# Trailing --bandwidth-cap 2 wins over any --bandwidth-cap in "$@" so this slice stays neighbor-safe.
# --skip-drive-space-check: vLLM weights land on d5; d2/d3 may be below global preflight min while still safe.
#
# Usage (archive VM, from model-archival/):
#   bash scripts/run-vllm-d5-archiver.sh
#   bash scripts/run-vllm-d5-archiver.sh --dry-run
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VLLM_BW_CAP_MBPS="${VLLM_BW_CAP_MBPS:-2}"
exec bash "$REPO_DIR/scripts/run.sh" \
  --registry config/registry-vllm.yaml \
  --drive d5_vllm \
  --all \
  --no-scheduled-bandwidth-cap \
  --queue-mode adaptive \
  --max-parallel 2 \
  --max-per-drive 1 \
  --skip-drive-space-check \
  "$@" \
  --bandwidth-cap "${VLLM_BW_CAP_MBPS}"
