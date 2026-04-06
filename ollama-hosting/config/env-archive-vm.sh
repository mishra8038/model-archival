#!/usr/bin/env bash
# Source on archival VM before `ollama serve` / `ollama-pull-queue`.
# Default: store Ollama data on /mnt/models/d2/ollama (change OLLAMA_HOME for d3).
# Usage: source ~/z/env/ai/ollama/env-archive-vm.sh

export PATH="${HOME}/.local/bin:${PATH}"
export OLLAMA_HOME="${OLLAMA_HOME:-/mnt/models/d2/ollama}"
export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"

mkdir -p "${OLLAMA_HOME}"
