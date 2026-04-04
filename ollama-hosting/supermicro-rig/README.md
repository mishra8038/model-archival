# supermicro-rig (host notes + symlinks)

**Canonical Ollama queue and tooling** live one level up, under **`../registry/`** and **`../scripts/`** (same **`ollama-hosting/`** tree).

- **`models/`** — symlinks to **`../registry/TARGET_QUEUE_ORDERED.txt`**, **`TARGET_PULL_HISTORY.csv`**, **`pull-queue-throttled.sh`**, and **`../docs/TARGET_MODEL_LIST.md`** for backward-compatible paths.
- **`scripts/`** — symlinks to **`../scripts/pull-ollama-stack.sh`**, **`pull-ollama-70b-stack.sh`**, **`ollama-cleanup-partials.sh`**.

**`SUPERMICRO-HOST-README.md`** mirrors **`~/z/env/dev-environment/supermicro/README.md`** (hardware / bootstrap). For Ollama operations, start with **`../README.md`**.
