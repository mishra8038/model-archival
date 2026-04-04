# Ollama archival model map

_Generated from inventory snapshot **1970-01-01T00:00:00Z**._

**Supermicro retention (after VM sync):** keep **Gemma 4** (MoE + dense + edge) and **Qwen Coder** only; see `ollama-hosting/scripts/ollama-supermicro-prune-plan.sh` and `ollama-hosting/docs/OLLAMA-CACHE-POLICY.md`. Other tags should exist on the archival VM below before you `ollama rm` them on the Supermicro.

**VM scan host:** `—`

## Roots scanned for inventory

- **d5** → `/mnt/models/d5/supermicro`
- **d2** → `/mnt/models/d2/supermicro`
- **d3** → `/mnt/models/d3/supermicro`
- **d1** → `/mnt/models/d1/supermicro`

## Model → disk(s)

| Ollama `model:tag` | Disk | Archive root | ~Size | `supermicro_cleared` |
|---|---:|---|---:|---|

## Machine-readable source

Canonical data: [`docs/data/ollama-vm-models-inventory.yaml`](data/ollama-vm-models-inventory.yaml). Rotation log: [`docs/data/ollama-sync-rotation.state`](data/ollama-sync-rotation.state).

