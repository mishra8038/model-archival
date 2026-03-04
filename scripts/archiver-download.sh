#!/usr/bin/env bash
# =============================================================================
# scripts/archiver-download.sh
# Wrapper — run the archiver download command via uv.
#
# Usage:
#   bash archiver-download.sh [OPTIONS]
#
# All options are forwarded verbatim to:
#   uv run archiver download [OPTIONS]
#
# Common options:
#   --all                 Download every model in the registry
#   --priority-only 1     Only token-free (P1) models
#   --tier A              Only Tier A models
#   --dry-run             Print plan without downloading
#   --verbose             Debug logging
#   --bandwidth-cap N     Cap total bandwidth at N MB/s
#   --max-parallel-drives N  Parallel drive workers (default 4)
#
# Examples:
#   bash archiver-download.sh --all --priority-only 1
#   bash archiver-download.sh --all --dry-run
#   bash archiver-download.sh --tier B
# =============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

if ! command -v uv &>/dev/null; then
    echo "ERROR: uv not found. Run deploy/setup-mxlinux.sh or deploy/setup-artix.sh first." >&2
    exit 1
fi

if [[ ! -d "$REPO_DIR/.venv" ]]; then
    echo "ERROR: .venv not found at $REPO_DIR. Run: cd $REPO_DIR && uv sync" >&2
    exit 1
fi

exec uv run archiver download "$@"
