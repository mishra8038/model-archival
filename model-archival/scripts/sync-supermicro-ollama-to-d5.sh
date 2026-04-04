#!/usr/bin/env bash
# Back-compat wrapper — use ollama-sync.sh (Ollama sync).
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/ollama-sync.sh" "$@"
