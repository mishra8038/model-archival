#!/usr/bin/env bash
# =============================================================================
# scripts/archiver-list.sh
# Wrapper — list all models in the registry via uv.
#
# Usage:
#   bash archiver-list.sh [--tier A|B|C|D] [--json]
#
# Examples:
#   bash archiver-list.sh
#   bash archiver-list.sh --tier A
#   bash archiver-list.sh --json
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

exec uv run archiver list "$@"
