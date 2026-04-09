#!/usr/bin/env bash
# =============================================================================
# archive-mcp.sh — Wrapper to archive MCP servers (and related tools) from GitHub
#
# Runs code-archival with registry-mcp.yaml. See README-mcp.md for the
# full list of MCP servers: master lists, evaluation/observability, vector DBs,
# adapters, build/convert tools, official SDKs.
#
# Usage:
#   bash archive-mcp.sh                  # archive all MCP repos to D1
#   bash archive-mcp.sh --dry-run        # list only
#   bash archive-mcp.sh --update         # refresh existing
#   bash archive-mcp.sh --output /path   # override output root (default /mnt/models/d1)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REGISTRY="$SCRIPT_DIR/registry-mcp.yaml"
OUTPUT_ROOT="${OUTPUT_ROOT:-/mnt/models/d1}"
PASSTHROUGH=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output)
            OUTPUT_ROOT="$2"
            PASSTHROUGH+=(--output "$OUTPUT_ROOT")
            shift 2
            ;;
        --output=*)
            OUTPUT_ROOT="${1#--output=}"
            PASSTHROUGH+=("$1")
            shift
            ;;
        *)
            PASSTHROUGH+=("$1")
            shift
            ;;
    esac
done

echo "[archive-mcp] Registry: $REGISTRY"
echo "[archive-mcp] Output root: $OUTPUT_ROOT"
echo ""

"$SCRIPT_DIR/archive.sh" --registry "$REGISTRY" "${PASSTHROUGH[@]}"
