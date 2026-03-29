#!/usr/bin/env bash
# Regenerate scratch (.tmp) audit JSON + Markdown on D3 infra.
# Usage: bash scripts/audit_tmp_status.sh [--delete-reclaimable] [--apply]
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
cd "$REPO_DIR"
exec uv run archiver audit-tmp "$@"
