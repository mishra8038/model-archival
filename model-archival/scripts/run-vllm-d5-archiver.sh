#!/usr/bin/env bash
# vLLM archiver slice: registry-vllm.yaml → /mnt/models/d5/vllm/{raw,uncensored}/… (d5_vllm in drives.yaml)
# Scratch remains on D1/.tmp. Infra (STATUS, run_state) stays on D3.
# Bandwidth: flat 2 MiB/s (aria2 global cap for LFS; XET/hf_hub not capped by aria2).
# --skip-drive-space-check: vLLM weights land on d5; d2/d3 may be below global preflight min while still safe.
#
# Usage (archive VM, from model-archival/):
#   bash scripts/run-vllm-d5-archiver.sh
#   bash scripts/run-vllm-d5-archiver.sh --dry-run
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$REPO_DIR/scripts/run.sh" \
  --registry config/registry-vllm.yaml \
  --drive d5_vllm \
  --all \
  --bandwidth-cap 2 \
  --no-scheduled-bandwidth-cap \
  --queue-mode adaptive \
  --max-parallel 2 \
  --max-per-drive 1 \
  --skip-drive-space-check \
  "$@"
