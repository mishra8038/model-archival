#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/x/dev/model-archival/full-stack"
FULL_STACK_BANDWIDTH_CAP="${FULL_STACK_BANDWIDTH_CAP:-0.75}"  # 6 Mbps ~= 0.75 MB/s
FULL_STACK_QUEUE_MODE="${FULL_STACK_QUEUE_MODE:-serial}"

uv run --project "$ROOT" full-stack-archive bootstrap-d5
uv run --project "$ROOT" full-stack-archive download-direct \
  --bandwidth-cap "$FULL_STACK_BANDWIDTH_CAP" \
  --queue-mode "$FULL_STACK_QUEUE_MODE" \
  --group ubuntu-isos \
  --group python-sources \
  --group language-toolchains \
  --group container-orchestration \
  --group nvidia-drivers-core \
  --group nvidia-drivers-legacy
