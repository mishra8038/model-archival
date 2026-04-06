#!/usr/bin/env bash
# Run SHA verification (verify-archive.py) on each revision tree, then create PAR2
# under .parity/ for D1+D2+D3. Execute on the archive VM with disks mounted.
#
# Default: sidecar/manifest check only (fast). Pass --rehash for full byte read.
#
# Usage:
#   bash scripts/par2-verify-then-backfill-all-drives.sh
#   bash scripts/par2-verify-then-backfill-all-drives.sh -- --redundancy-pct 5 --max-models 3
#   bash scripts/par2-verify-then-backfill-all-drives.sh --rehash -- --reserve-gib 4

set -euo pipefail
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

REHASH=()
if [[ "${1:-}" == "--rehash" ]]; then
  REHASH=(--verify-rehash)
  shift
fi
# Optional "--" before passthrough args
if [[ "${1:-}" == "--" ]]; then
  shift
fi

exec python3 "$REPO_DIR/scripts/par2_backfill_d2_d3.py" \
  --all-d123 \
  --verify-before-par2 \
  "${REHASH[@]}" \
  "$@"
