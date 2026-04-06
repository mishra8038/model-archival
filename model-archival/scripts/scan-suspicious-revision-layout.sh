#!/usr/bin/env bash
# Flag revision layouts that may double-count storage or indicate duplicate trees:
#   (A) "latest" exists but is not a symlink
#   (B) more than one 40-hex subdir (multiple pinned revisions)
# Usage: scan-suspicious-revision-layout.sh [/mnt/models/d1/raw] [more dirs...]
# Default: all /mnt/models/d{1,2,3,5}/{raw,quantized,uncensored}
set -euo pipefail
shopt -s nullglob

scan_base() {
  local base="$1"
  [[ -d "$base" ]] || return 0
  local orgdir repodir
  for orgdir in "$base"/*; do
    [[ -d "$orgdir" ]] || continue
    for repodir in "$orgdir"/*; do
      [[ -d "$repodir" ]] || continue
      local latest="$repodir/latest"
      local hexes=()
      local h
      for h in "$repodir"/[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]*; do
        [[ -d "$h" ]] || continue
        bn=$(basename "$h")
        [[ ${#bn} -eq 40 ]] && [[ "$bn" =~ ^[0-9a-f]{40}$ ]] && hexes+=("$bn")
      done
      local issue=""
      if [[ -e "$latest" && ! -L "$latest" ]]; then
        issue="${issue}non_symlink_latest;"
      fi
      if ((${#hexes[@]} > 1)); then
        issue="${issue}multi_sha:${#hexes[@]};"
      fi
      [[ -n "$issue" ]] || continue
      echo -e "$repodir\t$issue\t${hexes[*]}"
    done
  done
}

if (($# > 0)); then
  for b in "$@"; do
    scan_base "$b"
  done
else
  ROOT="${ROOT:-/mnt/models}"
  for d in d1 d2 d3 d5; do
    for sub in raw quantized uncensored; do
      scan_base "$ROOT/$d/$sub"
    done
  done
fi
