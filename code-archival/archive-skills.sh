#!/usr/bin/env bash
# =============================================================================
# archive-skills.sh — Wrapper to archive Agent/LLM Skills (GitHub repos + optional agentskills.io)
#
# Runs code-archival with registry-skills.yaml. Optionally mirrors agentskills.io.
#
# Usage:
#   bash archive-skills.sh                  # archive all skills repos to D5
#   bash archive-skills.sh --dry-run         # list only
#   bash archive-skills.sh --update          # refresh existing
#   bash archive-skills.sh --site            # also mirror agentskills.io (wget)
#   bash archive-skills.sh --output /path   # override output root (default /mnt/models/d5)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REGISTRY="$SCRIPT_DIR/registry-skills.yaml"
OUTPUT_ROOT="${OUTPUT_ROOT:-/mnt/models/d5}"
SKILLS_SITE_ROOT="${SKILLS_SITE_ROOT:-$OUTPUT_ROOT/skills-archives/agentskills.io}"

DO_SITE=false
PASSTHROUGH=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --site)
            DO_SITE=true
            shift
            ;;
        --output)
            OUTPUT_ROOT="$2"
            SKILLS_SITE_ROOT="$OUTPUT_ROOT/skills-archives/agentskills.io"
            PASSTHROUGH+=(--output "$OUTPUT_ROOT")
            shift 2
            ;;
        --output=*)
            OUTPUT_ROOT="${1#--output=}"
            SKILLS_SITE_ROOT="$OUTPUT_ROOT/skills-archives/agentskills.io"
            PASSTHROUGH+=("$1")
            shift
            ;;
        *)
            PASSTHROUGH+=("$1")
            shift
            ;;
    esac
done

echo "[archive-skills] Registry: $REGISTRY"
echo "[archive-skills] Output root: $OUTPUT_ROOT"
echo ""

# 1. GitHub repos via archive.sh
"$SCRIPT_DIR/archive.sh" --registry "$REGISTRY" "${PASSTHROUGH[@]}"

# 2. Optional: mirror agentskills.io
if $DO_SITE; then
    echo ""
    echo "[archive-skills] Mirroring agentskills.io to $SKILLS_SITE_ROOT"
    mkdir -p "$SKILLS_SITE_ROOT"
    cd "$SKILLS_SITE_ROOT"
    wget --mirror --convert-links --no-parent --no-host-directories \
        --adjust-extension --span-hosts --trust-server-names \
        --wait=1 --random-wait --limit-rate=500k \
        https://agentskills.io/ || { echo "[archive-skills] wget failed (non-fatal)" >&2; }
    echo "[archive-skills] Site mirror done."
fi
