#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/x/dev/model-archival/full-stack"

uv run --project "$ROOT" full-stack-archive bootstrap-d5
uv run --project "$ROOT" full-stack-archive download-direct \
  --group ubuntu-isos \
  --group python-sources \
  --group language-toolchains \
  --group container-orchestration \
  --group nvidia-drivers-core \
  --group nvidia-drivers-legacy
