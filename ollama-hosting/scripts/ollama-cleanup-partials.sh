#!/usr/bin/env bash
# Ollama *partial* blob files under models/blobs — inspect by default; delete only when you ask.
#
# Ollama reuses *partial* shards when you run `ollama pull <tag>` again, so removing them
# discards download progress. Default is **summary only** — partials stay for resume.
#
# Run ON the Ollama host. `--delete` needs sudo for systemctl when ollama is a systemd unit.
#
# Do NOT use --delete while a pull is in progress (script exits if it detects one).
#
# Canonical entrypoint: ollama-clean-partials (wrapper in the same directory).
#
# Environment:
#   OLLAMA_DATA_DIR      Data root (default: $HOME/.ollama)
#   OLLAMA_SYSTEMD_UNIT  Unit to stop/start (default: ollama); empty string skips systemctl
#
# Usage:
#   ./ollama-clean-partials              # counts + advice — nothing deleted
#   ./ollama-clean-partials --dry-run    # print every partial path — nothing deleted
#   ./ollama-clean-partials --delete     # remove ALL *partial* files (abandon resume)
#   ./ollama-clean-partials --delete --older-than 14   # remove only partials idle 14+ days

set -euo pipefail

OLLAMA_DATA_DIR="${OLLAMA_DATA_DIR:-$HOME/.ollama}"
BLOBS="${OLLAMA_DATA_DIR}/models/blobs"
UNIT="${OLLAMA_SYSTEMD_UNIT-ollama}"

DRY_RUN=0
DO_DELETE=0
OLDER_THAN_DAYS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --delete) DO_DELETE=1 ;;
    --older-than)
      shift
      OLDER_THAN_DAYS="${1:?--older-than requires a number of days}"
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: $0 [--dry-run] | [--delete [--older-than DAYS]]" >&2
      exit 2
      ;;
  esac
  shift
done

if [[ "$DO_DELETE" -eq 1 && "$DRY_RUN" -eq 1 ]]; then
  echo "Use only one of --delete or --dry-run." >&2
  exit 2
fi

if [[ -n "$OLDER_THAN_DAYS" && "$DO_DELETE" -ne 1 ]]; then
  echo "--older-than only applies with --delete." >&2
  exit 2
fi

_pull_or_queue_running() {
  pgrep -f "${HOME}/pull-ollama-stack.sh" >/dev/null 2>&1 \
    || pgrep -f '[o]llama-pull-queue' >/dev/null 2>&1 \
    || pgrep -f '[p]ull-queue-throttled.sh' >/dev/null 2>&1 \
    || pgrep -f '[o]llama pull' >/dev/null 2>&1
}

if [[ ! -d "$BLOBS" ]]; then
  echo "No blobs dir: $BLOBS"
  exit 0
fi

mapfile -t ALL_PARTIALS < <(find "$BLOBS" -maxdepth 1 -name '*partial*' -type f 2>/dev/null || true)
all_count=${#ALL_PARTIALS[@]}

if [[ "$all_count" -eq 0 ]]; then
  echo "No partial blobs under $BLOBS."
  exit 0
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  printf '%s\n' "${ALL_PARTIALS[@]}"
  echo "($all_count file(s); dry-run — nothing deleted)"
  exit 0
fi

# Delete path: optional mtime filter
if [[ "$DO_DELETE" -eq 1 ]]; then
  if _pull_or_queue_running; then
    echo "Abort: an ollama pull or ollama-pull-queue appears to be running." >&2
    exit 1
  fi

  if [[ -n "$OLDER_THAN_DAYS" ]]; then
    mapfile -t PARTIALS < <(find "$BLOBS" -maxdepth 1 -name '*partial*' -type f -mtime "+${OLDER_THAN_DAYS}" 2>/dev/null || true)
    filter_note=" (not modified in ${OLDER_THAN_DAYS}+ days)"
  else
    PARTIALS=("${ALL_PARTIALS[@]}")
    filter_note=""
  fi

  count=${#PARTIALS[@]}
  if [[ "$count" -eq 0 ]]; then
    echo "No partial blobs match delete criteria under $BLOBS${filter_note}."
    exit 0
  fi

  bytes=0
  for f in "${PARTIALS[@]}"; do
    [[ -f "$f" ]] || continue
    s=$(stat -c '%s' "$f" 2>/dev/null || echo 0)
    bytes=$((bytes + s))
  done
  echo "Deleting $count partial shard file(s) (~$((bytes / 1024 / 1024)) MiB)${filter_note} — resume data for these shards will be lost."

  STOPPED=0
  if [[ -n "$UNIT" ]] && command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet "$UNIT" 2>/dev/null; then
    echo "Stopping ${UNIT}.service…"
    sudo systemctl stop "$UNIT"
    STOPPED=1
  fi

  for f in "${PARTIALS[@]}"; do
    [[ -f "$f" ]] || continue
    rm -f -- "$f" && echo "removed $f"
  done

  if [[ "$STOPPED" -eq 1 ]]; then
    echo "Starting ${UNIT}.service…"
    sudo systemctl start "$UNIT"
  fi

  du -sh "${OLLAMA_DATA_DIR}/models" 2>/dev/null || true
  echo "Done."
  exit 0
fi

# Default: report all partials, do not delete
bytes=0
for f in "${ALL_PARTIALS[@]}"; do
  [[ -f "$f" ]] || continue
  s=$(stat -c '%s' "$f" 2>/dev/null || echo 0)
  bytes=$((bytes + s))
done

echo "Found $all_count partial shard file(s) (~$((bytes / 1024 / 1024)) MiB) under $BLOBS."
echo ""
echo "Ollama usually **resumes** these when you run \`ollama pull <tag>\` again — leaving them is the right default."
echo "  List paths:     $0 --dry-run"
echo "  Remove all:     $0 --delete"
echo "  Remove stale:   $0 --delete --older-than <days>   # e.g. abandoned pulls"
