#!/usr/bin/env bash
# Focused D1 download: only the three ids in config/registry-d1-manifest-incomplete.yaml
# (IntervitensInc/internlm2_5-20b-llamafied, meta-llama/Llama-3.3-70B-Instruct,
# deepseek-ai/DeepSeek-V3-0324), with a flat 4 MB/s bandwidth cap in aria2.
#
# --no-max-model-download: DeepSeek-V3-0324 HF total exceeds default 80 GiB checkpoint cap.
# --drive d1: restrict to registry rows with drive: d1 (all three are d1).
# Serial queue + one active model per drive keeps D1/.tmp churn predictable at low bandwidth.
#
# Run from anywhere; delegates to scripts/run.sh (expects repo layout under model-archival/).
#
# Examples:
#   bash scripts/run-d1-focused-incomplete.sh
#   bash scripts/run-d1-focused-incomplete.sh --dry-run
#   screen -S d1focused bash scripts/run-d1-focused-incomplete.sh
#
# After all three are complete and verified, run PAR2 (see reports/PAR2-BACKFILL-D2-D3.md):
#   bash scripts/par2-verify-then-backfill-all-drives.sh
#
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$REPO_DIR/scripts/run.sh" \
  --registry config/registry-d1-manifest-incomplete.yaml \
  --drive d1 \
  --bandwidth-cap 4 \
  --no-max-model-download \
  --queue-mode serial \
  --max-parallel 1 \
  --max-per-drive 1 \
  "$@"
