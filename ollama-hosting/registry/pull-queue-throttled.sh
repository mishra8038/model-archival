#!/usr/bin/env bash
# Back-compat: sequential pulls with trickle — delegates to ../scripts/ollama-pull-queue
# (registry-aware, merges JSON after each pull). Override paths with OLLAMA_DEV_ROOT / OLLAMA_MODELS.
set -euo pipefail
# Resolve symlinks so callers can link this file from supermicro-rig/models/
ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
export OLLAMA_DEV_ROOT="${OLLAMA_DEV_ROOT:-$(cd "$ROOT/.." && pwd)}"
export OLLAMA_MODELS="${OLLAMA_MODELS:-$OLLAMA_DEV_ROOT/registry}"
export QUEUE_FILE="${QUEUE_FILE:-$OLLAMA_MODELS/TARGET_QUEUE_ORDERED.txt}"
export HISTORY_CSV="${HISTORY_CSV:-$OLLAMA_MODELS/TARGET_PULL_HISTORY.csv}"
exec "$OLLAMA_DEV_ROOT/scripts/ollama-pull-queue" "$@"
