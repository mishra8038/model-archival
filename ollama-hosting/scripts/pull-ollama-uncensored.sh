#!/usr/bin/env bash
# Uncensored pulls only — thin wrapper over ollama-pull-queue + registry group "uncensored".
# Canonical list: OLLAMA_MODEL_REGISTRY.json (group) + TARGET_QUEUE_ORDERED.txt.
#
#   OLLAMA_HOST=127.0.0.1:11434 ./pull-ollama-uncensored.sh
#   ./pull-ollama-uncensored.sh --one
#
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export USE_TRICKLE="${USE_TRICKLE:-0}"
export OLLAMA_PULL_GROUP=uncensored
exec "$SCRIPT_DIR/ollama-pull-queue" "$@"
