# Ollama hosting (Supermicro + archival sync + pull registry)

Single folder for **Ollama operations** in the model-archival monorepo: **archival rsync**, **inventory/manifest**, **ordered pull queue**, **registry JSON**, and **operator scripts**.

## Layout

| Path | Role |
|------|------|
| **`registry/`** | **`OLLAMA_MODEL_REGISTRY.json`**, **`ollama_registry_tool.py`**, **`TARGET_QUEUE_ORDERED.txt`**, **`TARGET_PULL_HISTORY.csv`**, **`pull-queue-throttled.sh`** (wrapper → `scripts/ollama-pull-queue`) |
| **`scripts/`** | **`ollama-sync.sh`** (rsync Supermicro `~/.ollama` → archival VM), **`ollama-registry-sync`** (sync + merge manifest + CSV into JSON), **`ollama-pull-queue`**, **`ollama-clean-partials`**, **`pull-ollama-stack.sh`**, **`pull-ollama-70b-stack.sh`**, **`pull-ollama-uncensored.sh`**, … |
| **`docs/`** | **`OLLAMA-ARCHIVE-WORKFLOW.md`**, **`TARGET_MODEL_LIST.md`**, **`OLLAMA-CACHE-POLICY.md`**, **`OLLAMA-ARCHIVAL-MODEL-MAP.md`**, **`SPECIALIST-HF-PENDING-OLLAMA.md`**, **`docs/data/`** (manifest, inventory, rotation state) |
| **`config/`** | `ollama.service` example, Aider / Hermes / OpenClaw env examples |
| **`systemd/`** | User units for **`ollama-registry-sync`** (timer + oneshot service) |
| **`supermicro-rig/`** | Host notes; **`supermicro-rig/models/`** symlinks into **`registry/`** and **`docs/TARGET_MODEL_LIST.md`** for backward-compatible paths |

## Quick commands

```bash
cd ollama-hosting   # this directory

# Archival sync + refresh registry (from machine with SSH to Supermicro + VM)
./scripts/ollama-registry-sync

# On the GPU host (Ollama running); copy this repo or mount it
export OLLAMA_HOST=127.0.0.1:11434
./scripts/ollama-pull-queue --one

# Registry tool
cd registry && python3 ollama_registry_tool.py status
```

**Python env** (inventory / specialist helpers): `uv sync` once in **`ollama-hosting/`**.

## Expected operator flow (Supermicro + archive VM)

1. **Edit queue / registry** here (canonical), commit if needed.
2. **Deploy pull kit to the GPU host** at **`~/z/dev/ollama/`** (real files — Supermicro does not need the workstation’s `model-archival` stub layout):

   ```bash
   OLLAMA_SUPERMICRO_SSH=x@192.168.8.106 ./scripts/deploy-ollama-pull-kit-to-supermicro.sh
   ```

3. **Start pulls on Supermicro** (foreground or background):

   ```bash
   OLLAMA_SUPERMICRO_SSH=x@192.168.8.106 ./scripts/trigger-ollama-pull-on-supermicro.sh
   # or: ssh x@host 'cd ~/z/dev/ollama && ./scripts/ollama-pull-queue --one'
   ```

4. **Poll / copy completed cache to archival disks** — from a host with SSH to Supermicro **and** the archive VM, run **`./scripts/ollama-registry-sync`** (wraps **`ollama-sync.sh`** rsync of `~/.ollama` → rotation destinations, then merges manifest + pull history + **`sync-pull-from-archive`**). Schedule with **`systemd/`** user timer on the bridge/workstation if you want periodic polling.

So: **deploy queue → pull on Supermicro → registry-sync moves blobs to archive VM** (then verify manifest / **`ollama rm`** on Supermicro per **`docs/OLLAMA-ARCHIVE-WORKFLOW.md`**).

## Related monorepo docs

- **[`../docs/SUPERMICRO.md`](../docs/SUPERMICRO.md)** — Supermicro role in the archive story  
- **HF registries** used by specialist report generators: **`../model-archival/config/`**

## `~/z/dev/ollama` on different machines

- **Workstation** (next to `model-archival`): often a **stub** with symlinks + wrappers into this repo (see **`~/z/dev/ollama/README.md`**).
- **Supermicro**: expect a **deployed copy** of **`registry/`** + pull **`scripts/`** at **`~/z/dev/ollama/`** from **`deploy-ollama-pull-kit-to-supermicro.sh`** — no dependency on `model-archival` being cloned there.
