#!/usr/bin/env bash
# =============================================================================
# scripts/archiver-status.sh
# Wrapper — show per-model download status via uv.
#
# Usage:
#   bash archiver-status.sh [--drive LABEL]
#
# Examples:
#   bash archiver-status.sh
#   bash archiver-status.sh --drive d1
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

exec uv run archiver status "$@"
