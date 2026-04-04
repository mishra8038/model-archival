# Ollama hosting (Supermicro + archival sync)

This directory is the **home for Ollama-on-Supermicro operations** in the model-archival monorepo: pull queues, systemd unit, client env examples, and **rsync archival sync** to the disk VM (`x@192.168.8.65`) with rotating destinations.

## Layout

| Path | Role |
|------|------|
| **`supermicro-rig/`** | Mirror of Ollama-related material from **`~/z/env/dev-environment/supermicro/`** (host `x@192.168.8.106`): model lists, pull scripts, `ollama.service`, Aider/Hermes/OpenClaw examples. Refresh from that tree when the live rig changes. |
| **`scripts/`** | **`ollama-sync.sh`** (Supermicro `~/.ollama` → VM, rotation, inventory), VM maintain, prune planner, inventory/map generators. |
| **`docs/`** | Cache policy, archival model map, specialist↔Ollama pending report, **`docs/SYNC-JOB.md`** (operator spec). |
| **`docs/data/`** | Rotation state, VM inventory YAML, cache inventory, Ollama registry size cache. |

## Quick commands

From repo root (`model-archival/model-archival`):

```bash
cd ollama-hosting
uv sync   # once, for inventory / specialist report helpers

# Sync Ollama cache to archival VM (default: rotate d5 → d2 → d3 → d1)
./scripts/ollama-sync.sh

# Same with supermicro_cleared inference (SSH to both hosts)
OLLAMA_VM_INVENTORY_EXTRA='--infer-supermicro-cleared --supermicro-ssh x@192.168.8.106' ./scripts/ollama-sync.sh

# VM-only maintenance (no rsync)
./scripts/ollama-archive-vm-maintain.sh
```

**Canonical source for the GPU host** (bootstrap notes, Gemma tags, power limits) still lives in the dev-environment tree: **`~/z/env/dev-environment/supermicro/`**. Copy updates into `supermicro-rig/` when you change pull lists or service layout there.

## Related monorepo pieces

- **HF archiver** configs referenced by `generate_specialist_ollama_pending_report.py`: `../model-archival/config/` (`registry-specialists.yaml`, `registry.yaml`, `failed-models-registry.yaml`). Outputs and cache stay under **`ollama-hosting/docs/`**.
- **Fingerprints:** `../fingerprints/scripts/snapshot_ollama_library.py` (not duplicated here).

## Split state (until you migrate)

`model-archival/docs/data/ollama-sync-rotation.state` and related files still exist. After you confirm **`ollama-hosting`** workflows, either **copy the latest state** into `ollama-hosting/docs/data/` or **symlink** the old paths here so rotation does not fork.

## Documentation

- **`docs/SYNC-JOB.md`** — job specification (strategies, env vars, rotation, safety).
- **`docs/OLLAMA-CACHE-POLICY.md`** — retention, prune policy, inventory files.
- **`supermicro-rig/SUPERMICRO-HOST-README.md`** — full Supermicro 1028GQ-TXR host notes (copied from dev-environment).
- **Repo-level overview:** [`../docs/SUPERMICRO.md`](../docs/SUPERMICRO.md) — how the Supermicro fits the monorepo (anchors, checklist, links).
- **Consolidated monorepo prompt:** [`../docs/PROJECT-PROMPT-AND-REQUIREMENTS.md`](../docs/PROJECT-PROMPT-AND-REQUIREMENTS.md).
