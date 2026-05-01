#!/usr/bin/env bash
# **Final registry only** — use config/final_registry.yaml (built by scripts/build_final_registry.py).
# Other registries are out of scope for this wrapper; archive / defer those workflows separately.
# Destinations: YAML uses drive d5 by default; up to 3 rows may stay on d1 when rebuild marks them
# pending/in_progress on D1 (see build_final_registry.py). Neighbor-friendly: 2 MB/s cap
# (trailing flag wins over "$@"), adaptive queue, skip drive preflight min.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BW="${FINAL_REGISTRY_BW_MBPS:-2}"
exec bash "$REPO_DIR/scripts/run.sh" \
  --registry config/final_registry.yaml \
  --all \
  --no-scheduled-bandwidth-cap \
  --queue-mode adaptive \
  --max-parallel 2 \
  --max-per-drive 1 \
  --skip-drive-space-check \
  "$@" \
  --bandwidth-cap "${BW}"
