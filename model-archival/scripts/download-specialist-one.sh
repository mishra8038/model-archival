#!/usr/bin/env bash
# Restart / run a single specialist model download with a flat bandwidth cap.
# Uses registry-specialists.yaml, serial queue (one model at a time), resumable HF state.
#
# Usage:
#   bash scripts/download-specialist-one.sh '<hf-model-id>'
#
# Examples:
#   bash scripts/download-specialist-one.sh 'seyonec/ChemBERTa-zinc-base-v1'
#   bash scripts/download-specialist-one.sh 'AI4Chem/ChemLLM-7B-Chat'
#
# Env:
#   BANDWIDTH_CAP_MBPS   Total cap in MB/s (mebibytes/s). Default: 1
#                        For ~1 megabit/s line rate use:  export BANDWIDTH_CAP_MBPS=0.125
#   REGISTRY             Registry path (default: config/registry-specialists.yaml)
#
# Run from repo root on the download host (screen/tmux recommended). Same as run.sh: resumable.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

REG="${REGISTRY:-config/registry-specialists.yaml}"
CAP="${BANDWIDTH_CAP_MBPS:-1}"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 '<model-id>'"
    echo "  Registry: $REG"
    echo "  Cap:      \${BANDWIDTH_CAP_MBPS:-$CAP} MB/s (tool uses MB/s; 0.125 ≈ 1 Mbps)"
    exit 1
fi

MID="$1"
exec uv run archiver --registry "$REG" download "$MID" \
    --bandwidth-cap "$CAP" \
    --queue-mode serial \
    --max-parallel-drives 1
