#!/usr/bin/env bash
# Source on archival VM before `ollama serve` / `ollama-pull-queue`.
# Default: single live tree on D5 (after consolidate-ollama-vllm-caches-to-d5.sh). Override if needed.
# Usage: source ~/z/env/ai/ollama/env-archive-vm.sh

export PATH="${HOME}/.local/bin:${PATH}"
export OLLAMA_HOME="${OLLAMA_HOME:-/mnt/models-d5/ollama}"
export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"

mkdir -p "${OLLAMA_HOME}"
