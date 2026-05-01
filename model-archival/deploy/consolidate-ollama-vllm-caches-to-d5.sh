#!/usr/bin/env bash
# Merge scattered Ollama + vLLM (HF) caches onto D5 on the archival VM (192.168.8.65).
#
# Run ON the VM as user x (or set SSH jump). Stop Ollama first — both caches use dense small files.
#
#   dinitctl stop ollama   # Artix; adjust if your unit name differs
#   bash /home/x/dev/model-archival/model-archival/deploy/consolidate-ollama-vllm-caches-to-d5.sh
#   # review output, then without dry-run:
#   CONSOLIDATE_DRY_RUN=0 bash .../consolidate-ollama-vllm-caches-to-d5.sh
#
# Does NOT merge /mnt/models/d5/supermicro (Supermicro rsync mirror) into OLLAMA_HOME — that stays
# a separate tree unless you explicitly unify layouts yourself.
#
# Environment:
#   CONSOLIDATE_DRY_RUN=1  (default) — rsync -n only
#   CONSOLIDATE_DRY_RUN=0 — perform merges
#   OLLAMA_DEST   default /mnt/models/d5/ollama
#   VLLM_DEST     default /mnt/models/d5/vllm
#   OLLAMA_SOURCES  space-separated extra roots (after defaults)
#   VLLM_SOURCES    space-separated extra roots (after defaults)
#
set -euo pipefail

DRY="${CONSOLIDATE_DRY_RUN:-1}"
OLLAMA_DEST="${OLLAMA_DEST:-/mnt/models/d5/ollama}"
VLLM_DEST="${VLLM_DEST:-/mnt/models/d5/vllm}"

DEFAULT_OLLAMA_SRCS=(/mnt/models/d2/ollama /mnt/models/d3/ollama /mnt/models/d1/ollama)
DEFAULT_VLLM_SRCS=(/mnt/models/d1/vllm /mnt/models/d2/vllm /mnt/models/d3/vllm)

read -r -a USER_OLLAMA <<<"${OLLAMA_SOURCES:-}"
read -r -a USER_VLLM <<<"${VLLM_SOURCES:-}"

RSYNC_BASE=(rsync -aHAX --numeric-ids)
if [[ "$DRY" != "0" ]]; then
  RSYNC_BASE+=(--dry-run)
fi

banner() { printf '\n=== %s ===\n' "$*"; }

need_rw_dest() {
  local d="$1"
  mkdir -p "$d"
  touch "$d/.consolidate-write-test.$$" && rm -f "$d/.consolidate-write-test.$$"
}

df_warn() {
  banner "D5 free space"
  df -hP /mnt/models/d5 2>/dev/null || df -hP "${OLLAMA_DEST%/ollama}" 2>/dev/null || true
}

merge_tree() {
  local label="$1" dest="$2"
  shift 2
  local -a srcs=("$@")
  banner "$label → $dest"
  need_rw_dest "$dest"
  local s
  for s in "${srcs[@]}"; do
    [[ -n "$s" ]] || continue
    [[ "$s" == "$dest" ]] && continue
    if [[ ! -d "$s" ]]; then
      echo "  skip (missing): $s"
      continue
    fi
    echo "  merge: $s/"
    "${RSYNC_BASE[@]}" --info=stats2 "$s/" "$dest/"
  done
}

dedupe_paths() {
  local -a out=()
  local p seen
  for p in "$@"; do
    [[ -z "$p" ]] && continue
    seen=0
    for q in "${out[@]}"; do
      [[ "$p" == "$q" ]] && { seen=1; break; }
    done
    [[ "$seen" -eq 0 ]] && out+=("$p")
  done
  printf '%s\n' "${out[@]}"
}

mapfile -t OLLAMA_SRCS < <(dedupe_paths "${DEFAULT_OLLAMA_SRCS[@]}" "${USER_OLLAMA[@]}")
mapfile -t VLLM_SRCS < <(dedupe_paths "${DEFAULT_VLLM_SRCS[@]}" "${USER_VLLM[@]}")

echo "CONSOLIDATE_DRY_RUN=$DRY (set to 0 to apply)"
df_warn

if pgrep -x ollama >/dev/null 2>&1; then
  echo "WARN: ollama process is running — stop it before CONSOLIDATE_DRY_RUN=0 to avoid corruption." >&2
fi

merge_tree "Ollama live caches" "$OLLAMA_DEST" "${OLLAMA_SRCS[@]}"
merge_tree "vLLM / HF hub caches" "$VLLM_DEST" "${VLLM_SRCS[@]}"

banner "Next steps (manual)"
cat <<EOF
1. Update shell env / login:
     source ollama-hosting/config/env-archive-vm.sh      # OLLAMA_HOME → $OLLAMA_DEST
     source vllm-hosting/config/env-archive-vm-vllm.sh    # VLLM_ARCHIVE_ROOT → $VLLM_DEST
2. Point your Ollama service / dinit unit at OLLAMA_HOME=$OLLAMA_DEST (and restart).
3. After verifying workloads, reclaim space:
     mv /mnt/models/d2/ollama /mnt/models/d2/ollama.bak.\$(date +%Y%m%d)   # then delete when happy
     ln -s "$OLLAMA_DEST" /mnt/models/d2/ollama   # optional compat symlink
   Same pattern for old vLLM roots → symlink to $VLLM_DEST if needed.
4. D5 is ~916 GiB — confirm total cache size fits:  du -sh $OLLAMA_DEST $VLLM_DEST /mnt/models/d1/vllm ...
EOF
