#!/usr/bin/env bash
# =============================================================================
# scripts/check-environment.sh
# Wrapper — run the pre-execution environment verifier.
#
# Usage:
#   bash check-environment.sh [OPTIONS]
#
# All options are forwarded to deploy/verify-environment.sh:
#   --skip-network    Skip network / HF reachability checks
#   --skip-token      Skip HuggingFace token access checks
#   --skip-hf-api     Skip per-model HF API token checks
#   --min-free-gb N   Minimum free GB per drive (default 50)
#
# Examples:
#   bash check-environment.sh
#   bash check-environment.sh --skip-network
# =============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

exec bash "$REPO_DIR/deploy/verify-environment.sh" --repo-dir "$REPO_DIR" "$@"
