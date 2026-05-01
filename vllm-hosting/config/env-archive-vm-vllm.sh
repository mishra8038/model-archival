#!/usr/bin/env bash
# Source on archival VM (192.168.8.65) before vLLM weight downloads.
# Usage: source /path/to/model-archival/vllm-hosting/config/env-archive-vm-vllm.sh

export VLLM_ARCHIVE_ROOT="${VLLM_ARCHIVE_ROOT:-/mnt/models/d5/vllm}"
export VLLM_HF_HOME="${VLLM_HF_HOME:-${VLLM_ARCHIVE_ROOT}/hf_hub}"
export HF_HOME="${HF_HOME:-${VLLM_HF_HOME}}"
export HF_HUB_CACHE="${HF_HUB_CACHE:-${HF_HOME}/hub}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-${HF_HOME}/transformers}"
# Prepend venv on this root when huggingface-cli exists there.
export VLLM_VENV="${VLLM_VENV:-${VLLM_ARCHIVE_ROOT}/venv}"
if [[ -x "${VLLM_VENV}/bin/huggingface-cli" ]]; then
  export PATH="${VLLM_VENV}/bin:${PATH}"
fi
export PATH="${HOME}/.local/bin:${PATH}"

if [[ -f "${HOME}/.hf_token" ]]; then
  # shellcheck disable=SC2155
  export HF_TOKEN="$(tr -d ' \t\n\r' <"${HOME}/.hf_token")"
fi

mkdir -p "${VLLM_ARCHIVE_ROOT}/state" "${VLLM_ARCHIVE_ROOT}/logs" "${HF_HUB_CACHE}" "${TRANSFORMERS_CACHE}"
