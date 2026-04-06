#!/usr/bin/env bash
# Run ON the Ollama host. Pulls ~70B dense (Q4 instruct) + ~70B abliterated/uncensored stacks.
#
# Hardware: 4× P100 16GB can run these Q4 blobs via multi-GPU, but latency and context are heavy;
# keep power/thermal headroom in mind.
#
# Disk: each line is on the order of ~40–45 GB. Five models ≈ 200 GB+ — ensure free space on the
# filesystem that holds ~/.ollama (check: df -h ~ && du -sh ~/.ollama/models).
#
#   chmod +x pull-ollama-70b-stack.sh
#   OLLAMA_HOST=127.0.0.1:11434 ./pull-ollama-70b-stack.sh
#   nohup env OLLAMA_HOST=127.0.0.1:11434 ./pull-ollama-70b-stack.sh >> ~/logs/ollama-70b-pull.log 2>&1 &

set -u
export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
THROTTLE_KBPS="${THROTTLE_KBPS:-4096}"
THROTTLE_UPLOAD_KBPS="${THROTTLE_UPLOAD_KBPS:-512}"
USE_TRICKLE="${USE_TRICKLE:-1}"

log() { printf '%s %s\n' "$(date -Iseconds)" "$*"; }

run_pull() {
  local m="$1"
  if [[ "$USE_TRICKLE" != "0" && "$USE_TRICKLE" != "false" ]] && command -v trickle >/dev/null 2>&1; then
    trickle -s -d "${THROTTLE_KBPS}" -u "${THROTTLE_UPLOAD_KBPS}" ollama pull "$m"
  else
    [[ "$USE_TRICKLE" != "0" && "$USE_TRICKLE" != "false" ]] && log "WARN: trickle not installed — unthrottled pull: $m"
    ollama pull "$m"
  fi
}

MODELS=(
  # --- Dense instruct (70B-class, Q4_K_M) ---
  llama3.3:70b-instruct-q4_K_M
  llama3.1:70b-instruct-q4_K_M
  qwen2.5:72b-instruct-q4_K_M

  # --- Abliterated / uncensored ~70B (Q4) ---
  dolphin-llama3:70b-v2.9-q4_K_M
  huihui_ai/llama3.3-abliterated:70b
)

main() {
  if ! command -v ollama >/dev/null 2>&1; then
    log "ERROR: ollama not in PATH"
    exit 1
  fi
  log "OLLAMA_HOST=$OLLAMA_HOST"
  log "Pulling ${#MODELS[@]} large models (sequential, ${THROTTLE_KBPS} KiB/s down if trickle)…"
  local ok=0 fail=0
  for m in "${MODELS[@]}"; do
    log ">>> pull $m"
    if run_pull "$m"; then
      log "OK   $m"
      ok=$((ok + 1))
    else
      log "FAIL $m (continuing)"
      fail=$((fail + 1))
    fi
  done
  log "Done. OK=$ok FAIL=$fail"
  ollama list || true
}

main "$@"
