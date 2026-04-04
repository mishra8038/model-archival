#!/usr/bin/env bash
# Remove incomplete Ollama download shards (*partial* blobs). Safe when no finished
# models need those layers (re-pull with `ollama pull <tag>` after).
#
# Run ON the server as user x (needs sudo for systemctl if ollama is a service).
#
# Do NOT run while a download is in progress (e.g. pull-ollama-stack.sh): this
# stops ollama.service and deletes *partial* files, which aborts active pulls.

set -euo pipefail

if pgrep -f "${HOME}/pull-ollama-stack.sh" >/dev/null 2>&1 \
  || pgrep -f '[o]llama pull' >/dev/null 2>&1; then
  echo "Abort: an ollama pull (or pull-ollama-stack.sh) appears to be running."
  echo "Wait for it to finish, or stop it, then re-run this script."
  exit 1
fi

BLOBS="${HOME}/.ollama/models/blobs"
if [[ ! -d "$BLOBS" ]]; then
  echo "No blobs dir: $BLOBS"
  exit 0
fi
count=$(find "$BLOBS" -maxdepth 1 -name '*partial*' -type f 2>/dev/null | wc -l)
if [[ "$count" -eq 0 ]]; then
  echo "No partial blobs. Nothing to do."
  exit 0
fi
if systemctl is-active --quiet ollama 2>/dev/null; then
  echo "Stopping ollama.service…"
  sudo systemctl stop ollama
  STOPPED=1
else
  STOPPED=0
fi
echo "Removing $count partial shard file(s)…"
find "$BLOBS" -maxdepth 1 -name '*partial*' -type f -print -delete
if [[ "$STOPPED" -eq 1 ]]; then
  echo "Starting ollama.service…"
  sudo systemctl start ollama
fi
du -sh "${HOME}/.ollama/models" 2>/dev/null || true
echo "Done."
