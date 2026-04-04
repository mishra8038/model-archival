#!/usr/bin/env bash
# SSH to Supermicro and start ollama-pull-queue under nohup → ~/logs/ollama-pull-queue.log
#
# Prerequisite: deploy-ollama-pull-kit-to-supermicro.sh
#
#   OLLAMA_SUPERMICRO_SSH=user@host ./trigger-ollama-pull-on-supermicro.sh
#
# Environment:
#   OLLAMA_SUPERMICRO_SSH   required unless passed as first argument
#   OLLAMA_PULL_ONE         1 = --one (default), 0 = background full queue drain
#
# Remote env (e.g. USE_TRICKLE=0): use ssh manually — see script comments in ollama-pull-queue.
#
set -euo pipefail

REMOTE="${OLLAMA_SUPERMICRO_SSH:-${1:-}}"
if [[ -z "$REMOTE" ]]; then
  echo "Usage: OLLAMA_SUPERMICRO_SSH=user@host $0" >&2
  exit 2
fi

ONE_STR=""
if [[ "${OLLAMA_PULL_ONE:-1}" == "1" ]]; then
  ONE_STR="--one"
fi

ssh -o BatchMode=yes "$REMOTE" \
  "mkdir -p \"\$HOME/logs\"; export OLLAMA_HOST=\"\${OLLAMA_HOST:-127.0.0.1:11434}\"; cd \"\$HOME/z/dev/ollama\" || exit 1; nohup ./scripts/ollama-pull-queue ${ONE_STR} >>\"\$HOME/logs/ollama-pull-queue.log\" 2>&1 & echo pid=\$!"
