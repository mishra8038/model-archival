#!/usr/bin/env bash
# List Hugging Face-style raw trees that appear on more than one model disk (d1–d5).
# Usage: scan-cross-drive-raw-duplicates.sh [/mnt/models]
# Output: TSV columns: hf_repo<TAB>drives (sorted)<TAB>paths (one per line in third col via |)
set -euo pipefail
ROOT="${1:-/mnt/models}"
declare -A SEEN
for d in d1 d2 d3 d5; do
  base="$ROOT/$d/raw"
  [[ -d "$base" ]] || continue
  while IFS= read -r -d '' dir; do
    rel="${dir#"$base"/}"
    [[ "$rel" == *"/"*"/"* ]] || continue
    org="${rel%%/*}"
    rest="${rel#*/}"
    name="${rest%%/*}"
    id="$org/$name"
    SEEN["$id"]="${SEEN[$id]:+${SEEN[$id]} }$d:$dir"
  done < <(find "$base" -mindepth 2 -maxdepth 2 -type d -print0 2>/dev/null)
done
for id in "${!SEEN[@]}"; do
  paths=(${SEEN[$id]})
  n=${#paths[@]}
  (( n > 1 )) || continue
  drives=""
  for p in "${paths[@]}"; do
    dr="${p%%:*}"
    drives="$drives $dr"
  done
  drives=$(echo $drives | tr ' ' '\n' | sort -u | tr '\n' ' ')
  echo -e "$id\t$drives"
done | sort
