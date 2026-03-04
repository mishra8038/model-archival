#!/usr/bin/env bash
# =============================================================================
# scripts/verify-archive.sh
# Wrapper — run the standalone archive integrity verifier.
#
# Usage:
#   bash verify-archive.sh [OPTIONS]
#
# All options are forwarded to verification/verify-archive.py:
#   --drives PATH ...     Drive mount points to scan
#   --model-dir PATH      Single model directory
#   --rehash              Full SHA-256 re-hash from disk (slow, thorough)
#   --tier A|B|C|D        Only verify this tier
#   --failures-only       Only show/report failures
#   --report-dir PATH     Where to write the Markdown report
#   --no-report           Console only, no report file
#
# Default behaviour (no --drives or --model-dir):
#   Reads drives.yaml and scans all configured mount points.
#
# Examples:
#   bash verify-archive.sh --drives /mnt/models/d1 /mnt/models/d2
#   bash verify-archive.sh --drives /mnt/models/d1 --rehash
#   bash verify-archive.sh --model-dir /mnt/models/d1/deepseek-ai/DeepSeek-R1/abc123
#   bash verify-archive.sh --tier A --failures-only
# =============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_DIR/verification/verify-archive.py"

if ! command -v python3 &>/dev/null && ! command -v uv &>/dev/null; then
    echo "ERROR: Neither python3 nor uv found in PATH." >&2; exit 1
fi

# If no --drives or --model-dir is supplied, auto-read all mount points from drives.yaml
HAS_TARGET=false
for arg in "$@"; do
    [[ "$arg" == "--drives" || "$arg" == "--model-dir" ]] && HAS_TARGET=true
done

if ! $HAS_TARGET; then
    DRIVES_FILE="$REPO_DIR/config/drives.yaml"
    if [[ ! -f "$DRIVES_FILE" ]]; then
        echo "ERROR: No --drives / --model-dir given and $DRIVES_FILE not found." >&2
        exit 1
    fi
    # Extract mount_point values from drives.yaml
    MOUNT_POINTS=()
    while IFS= read -r line; do
        mp=$(echo "$line" | grep "mount_point:" | awk '{print $2}' | tr -d '"')
        [[ -n "$mp" ]] && MOUNT_POINTS+=("$mp")
    done < "$DRIVES_FILE"

    if [[ ${#MOUNT_POINTS[@]} -eq 0 ]]; then
        echo "ERROR: Could not parse any mount_point entries from $DRIVES_FILE." >&2
        exit 1
    fi

    echo "Auto-detected drives from drives.yaml: ${MOUNT_POINTS[*]}"
    set -- --drives "${MOUNT_POINTS[@]}" "$@"
fi

# Prefer uv run (uses project venv), fall back to system python3
if command -v uv &>/dev/null && [[ -d "$REPO_DIR/.venv" ]]; then
    exec uv run --project "$REPO_DIR" python3 "$SCRIPT" "$@"
else
    exec python3 "$SCRIPT" "$@"
fi
