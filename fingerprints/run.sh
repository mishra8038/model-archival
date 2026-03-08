#!/usr/bin/env bash
# =============================================================================
# run.sh — Run the fingerprint crawler
#
# Usage:
#   bash run.sh                        # crawl all repos (1 worker, respects HF rate limits)
#   bash run.sh --output /mnt/models/d1 # write to a different drive
#   bash run.sh --tier A               # only Tier A (flagship) models
#   bash run.sh --importance critical  # only critical-importance models
#   bash run.sh --force                # re-crawl already-complete repos
#   bash run.sh --dry-run              # list what would run, don't crawl
#
# The tool is fully resumable — interrupted runs pick up where they left off.
# =============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Activate venv ─────────────────────────────────────────────────────────────
if [[ ! -d "$REPO_DIR/.venv" ]]; then
    echo "No .venv found — running: uv sync"
    cd "$REPO_DIR" && uv sync
fi

source "$REPO_DIR/.venv/bin/activate"

# ── HF token ──────────────────────────────────────────────────────────────────
if [[ -z "${HF_TOKEN:-}" ]] && [[ -f "$HOME/.hf_token" ]]; then
    export HF_TOKEN
    HF_TOKEN=$(cat "$HOME/.hf_token")
fi

# ── Run ───────────────────────────────────────────────────────────────────────
exec fingerprints --output "${OUTPUT:-/mnt/models/d1}" run --workers 1 "$@"
