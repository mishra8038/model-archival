#!/usr/bin/env bash
# =============================================================================
# scripts/archive-tooling.sh
# Mirror all tooling projects from local/config/registry.yaml onto D5.
#
# This creates/updates bare git mirrors under /mnt/models/d5/tooling-archive.
# It is safe to re-run; existing mirrors are fetched and pruned.
# =============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

TOOLING_ARCHIVE_ROOT="/mnt/models/d5/tooling-archive"

echo "[archive-tooling] Using archive root: $TOOLING_ARCHIVE_ROOT"
mkdir -p "$TOOLING_ARCHIVE_ROOT"

echo "[archive-tooling] Reading tooling entries from local/config/registry.yaml..."

# Emit "id repo" pairs from the YAML tooling section.
mapfile -t TOOL_LINES < <(python - << 'PY'
import pathlib
import sys

try:
    import yaml  # type: ignore
except Exception as exc:  # pragma: no cover - defensive
    print(f"ERROR: PyYAML not available in this environment: {exc}", file=sys.stderr)
    sys.exit(1)

reg_path = pathlib.Path("config/registry.yaml")
data = yaml.safe_load(reg_path.read_text(encoding="utf-8"))

for entry in data.get("tooling", []) or []:
    tid = entry.get("id")
    repo = entry.get("repo")
    if not tid or not repo:
        continue
    print(f"{tid} {repo}")
PY
)

if ((${#TOOL_LINES[@]} == 0)); then
    echo "[archive-tooling] No tooling entries found; nothing to do."
    exit 0
fi

echo "[archive-tooling] Found ${#TOOL_LINES[@]} tooling projects to mirror."

for line in "${TOOL_LINES[@]}"; do
    # line format: "<id> <repo-url>"
    tid="${line%% *}"
    repo="${line#* }"

    mirror_dir="${TOOLING_ARCHIVE_ROOT}/${tid}.git"
    echo "[archive-tooling] Processing ${tid} -> ${repo}"

    if [[ -d "$mirror_dir" ]]; then
        echo "  - Updating existing mirror at $mirror_dir"
        git -C "$mirror_dir" remote set-url origin "$repo" || true
        git -C "$mirror_dir" fetch --all --prune
    else
        echo "  - Creating new mirror at $mirror_dir"
        git clone --mirror "$repo" "$mirror_dir"
    fi
done

echo "[archive-tooling] Done."

