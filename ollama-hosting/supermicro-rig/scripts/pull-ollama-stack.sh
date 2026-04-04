#!/usr/bin/env bash
# Run ON the Supermicro host (Ollama installed, `ollama serve` running).
# Pulls Gemma 4 (Q4/Q8, P100-friendly) + recommended coding / reasoning models.
# Order: smaller first. Idempotent: `ollama pull` reuses layers.
# Rough total size ~250+ GB — ensure enough free space on the volume holding ~/.ollama.
#
#   chmod +x pull-ollama-stack.sh
#   OLLAMA_HOST=127.0.0.1:11434 ./pull-ollama-stack.sh
#   nohup env OLLAMA_HOST=127.0.0.1:11434 ./pull-ollama-stack.sh >> ~/logs/ollama-stack-pull.log 2>&1 &

set -u
export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"

log() { printf '%s %s\n' "$(date -Iseconds)" "$*"; }

MODELS=(
  # --- Small / fast (single P100 friendly) ---
  deepseek-coder:6.7b
  qwen2.5-coder:7b
  llama3.1:8b-instruct-q4_K_M
  deepseek-r1:8b-0528-qwen3-q4_K_M
  gemma4:e2b-it-q4_K_M
  deepseek-coder-v2:16b
  deepseek-r1:14b-qwen-distill-q4_K_M
  qwen2.5-coder:14b-instruct-q4_K_M
  starcoder2:15b-instruct-q4_K_M
  gemma4:e2b-it-q8_0
  gemma4:e4b-it-q4_K_M
  gemma4:e4b-it-q8_0

  # --- ~18–21 GB (multi-GPU or tight single) ---
  gemma4:26b-a4b-it-q4_K_M
  gemma4:31b-it-q4_K_M
  qwen2.5-coder:32b-instruct-q4_K_M
  deepseek-coder:33b-instruct-q4_K_M
  gemma4:26b-a4b-it-q8_0
  gemma4:31b-it-q8_0

  # --- MoE generalist (large) ---
  mixtral:8x7b-instruct-v0.1-q4_K_M
)

main() {
  if ! command -v ollama >/dev/null 2>&1; then
    log "ERROR: ollama not in PATH"
    exit 1
  fi
  log "OLLAMA_HOST=$OLLAMA_HOST"
  log "Starting pulls (${#MODELS[@]} models)…"
  local ok=0 fail=0
  for m in "${MODELS[@]}"; do
    log ">>> pull $m"
    if ollama pull "$m"; then
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
