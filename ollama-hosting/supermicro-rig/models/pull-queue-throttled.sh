#!/usr/bin/env bash
# Sequential Ollama pulls from TARGET_QUEUE_ORDERED.txt with a download cap (~4 MiB/s by default).
# Policy: one pull at a time (do not run two copies of this script). Max 1–2 concurrent pulls total
# across the host — prefer only this job.
#
# Throttle: uses `trickle` (apt: trickle) in KB/s. 4 MiB/s ≈ 4096 KiB/s → trickle -d 4096
# If trickle is missing, runs unthrottled and prints a warning.
#
# On success, appends a CSV row to TARGET_PULL_HISTORY.csv next to this script.
#
# Usage (on Ollama host, after copying repo files):
#   export OLLAMA_HOST=127.0.0.1:11434
#   ./pull-queue-throttled.sh                    # all remaining lines in queue
#   ./pull-queue-throttled.sh --one              # single next model (first line not in history optional)
#   THROTTLE_KBPS=2048 ./pull-queue-throttled.sh # 2 MiB/s cap
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QUEUE_FILE="${QUEUE_FILE:-${ROOT}/TARGET_QUEUE_ORDERED.txt}"
HISTORY_CSV="${HISTORY_CSV:-${ROOT}/TARGET_PULL_HISTORY.csv}"
LOCK_FILE="${LOCK_FILE:-/tmp/ollama-target-pull.lock}"
export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
# Download cap: KiB/s for trickle -d (4 MiB/s)
THROTTLE_KBPS="${THROTTLE_KBPS:-4096}"
THROTTLE_UPLOAD_KBPS="${THROTTLE_UPLOAD_KBPS:-512}"
# After you clear ~/.ollama, set IGNORE_PULL_HISTORY=1 so completed tags are pulled again.
IGNORE_PULL_HISTORY="${IGNORE_PULL_HISTORY:-}"

log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*"; }

tag_marked_completed() {
  local model="$1"
  [[ ! -f "$HISTORY_CSV" ]] && return 1
  grep -F "$model" "$HISTORY_CSV" 2>/dev/null | grep -q ',completed,' || return 1
}

append_history() {
  local tag="$1" size="$2" status="$3" note="$4"
  local esc_note="${note//,/ }"
  printf '%s,%s,%s,%s,%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$tag" "$size" "$status" "$esc_note" >>"$HISTORY_CSV"
}

run_pull() {
  local model="$1"
  if command -v trickle >/dev/null 2>&1; then
    log "pull (throttled ${THROTTLE_KBPS} KiB/s down): $model"
    trickle -s -d "${THROTTLE_KBPS}" -u "${THROTTLE_UPLOAD_KBPS}" ollama pull "$model"
  else
    log "WARN: trickle not installed — pull UNTHROTTLED. Install: sudo apt install trickle"
    log "pull: $model"
    ollama pull "$model"
  fi
}

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  log "Another pull-queue-throttled.sh holds $LOCK_FILE — exit."
  exit 1
fi

ONE_MODE=0
if [[ "${1:-}" == "--one" ]]; then
  ONE_MODE=1
fi

if ! command -v ollama >/dev/null 2>&1; then
  log "ERROR: ollama not in PATH"
  exit 1
fi

if [[ ! -f "$QUEUE_FILE" ]]; then
  log "ERROR: queue file not found: $QUEUE_FILE"
  exit 1
fi

touch "$HISTORY_CSV"

pulled_this_run=0
while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line#"${line%%[![:space:]]*}"}"
  line="${line%"${line##*[![:space:]]}"}"
  [[ -z "$line" || "$line" == \#* ]] && continue

  model="$line"
  log ">>> queue item: $model"
  if [[ -z "$IGNORE_PULL_HISTORY" ]] && tag_marked_completed "$model"; then
    log "SKIP (history shows completed): $model — set IGNORE_PULL_HISTORY=1 to re-pull after cache clear"
    continue
  fi

  if run_pull "$model"; then
    append_history "$model" "?" "completed" "throttle_KiB_s=${THROTTLE_KBPS}"
    log "OK $model"
  else
    append_history "$model" "?" "failed" "throttle_KiB_s=${THROTTLE_KBPS}"
    log "FAIL $model (stopping queue — fix and re-run)"
    exit 1
  fi
  pulled_this_run=$((pulled_this_run + 1))
  if [[ "$ONE_MODE" -eq 1 ]]; then
    log "--one: stopping after single pull."
    break
  fi
done <"$QUEUE_FILE"

log "Finished pass: $pulled_this_run pull(s). ollama list:"
ollama list || true
