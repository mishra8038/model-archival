#!/usr/bin/env bash
# =============================================================================
# scripts/archiver-drives.sh
# Wrapper — show drive usage via uv.
#
# Usage:
#   bash archiver-drives.sh
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

exec uv run archiver drives status
