#!/usr/bin/env bash
# =============================================================================
# scripts/archiver-verify.sh
# Wrapper — run the archiver verify command via uv.
#
# Usage:
#   bash archiver-verify.sh [OPTIONS] [MODEL_ID]
#
# All options are forwarded verbatim to:
#   uv run archiver verify [OPTIONS]
#
# Common options:
#   --all              Verify every completed model
#   --tier A           Only tier A models
#   --drive d1         Only models on drive d1
#
# Examples:
#   bash archiver-verify.sh --all
#   bash archiver-verify.sh deepseek-ai/DeepSeek-R1
#   bash archiver-verify.sh --tier A
# =============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

if ! command -v uv &>/dev/null; then
    echo "ERROR: uv not found." >&2; exit 1
fi
if [[ ! -d "$REPO_DIR/.venv" ]]; then
    echo "ERROR: .venv not found. Run: cd $REPO_DIR && uv sync" >&2; exit 1
fi

exec uv run archiver verify "$@"
