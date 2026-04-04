# Models queue (symlinks)

**Canonical files** live under **`ollama-hosting/registry/`**:

- `TARGET_QUEUE_ORDERED.txt`
- `TARGET_PULL_HISTORY.csv`
- `pull-queue-throttled.sh` → runs **`../scripts/ollama-pull-queue`** (registry-aware)

**Human doc:** **`../../docs/TARGET_MODEL_LIST.md`** (also linked here as `TARGET_MODEL_LIST.md`).

On the Supermicro, prefer **`cd …/ollama-hosting`**, **`./scripts/ollama-pull-queue --one`**, so paths and JSON stay consistent.
