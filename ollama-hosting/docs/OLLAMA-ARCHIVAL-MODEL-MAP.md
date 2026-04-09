# Ollama archival model map

_Generated from inventory snapshot **2026-04-09T15:30:03Z**._

**Supermicro retention (after VM sync):** keep **Gemma 4** (MoE + dense + edge) and **Qwen Coder** only; see `ollama-hosting/scripts/ollama-supermicro-prune-plan.sh` and `ollama-hosting/docs/OLLAMA-CACHE-POLICY.md`. Other tags should exist on the archival VM below before you `ollama rm` them on the Supermicro.

**VM scan host:** `x@192.168.8.65`

## Roots scanned for inventory

- **d5** → `/mnt/models/d5/supermicro`

## Model → disk(s)

| Ollama `model:tag` | Disk | Archive root | ~Size | `supermicro_cleared` |
|---|---:|---|---:|---|
| deepseek-coder-v2-16b-ctx8k:latest | d5 | `/mnt/models/d5/supermicro` | 8.29 GiB | unknown |
| deepseek-coder-v2:16b | d5 | `/mnt/models/d5/supermicro` | 8.29 GiB | no |
| deepseek-coder:33b-instruct-q4_K_M | d5 | `/mnt/models/d5/supermicro` | 18.57 GiB | unknown |
| deepseek-coder:6.7b | d5 | `/mnt/models/d5/supermicro` | 3.56 GiB | no |
| deepseek-r1:14b-qwen-distill-q4_K_M | d5 | `/mnt/models/d5/supermicro` | 8.37 GiB | no |
| deepseek-r1:8b-0528-qwen3-q4_K_M | d5 | `/mnt/models/d5/supermicro` | 4.87 GiB | no |
| dolphin-llama3:8b | d5 | `/mnt/models/d5/supermicro` | 4.34 GiB | no |
| dolphin-mistral:latest | d5 | `/mnt/models/d5/supermicro` | 3.83 GiB | no |
| gemma4-26b-a4b-q4-ctx8k:latest | d5 | `/mnt/models/d5/supermicro` | 16.75 GiB | unknown |
| gemma4:26b-a4b-it-q4_K_M | d5 | `/mnt/models/d5/supermicro` | 16.75 GiB | no |
| gemma4:31b-it-q4_K_M | d5 | `/mnt/models/d5/supermicro` | 18.50 GiB | unknown |
| gemma4:e2b-it-q4_K_M | d5 | `/mnt/models/d5/supermicro` | 6.67 GiB | no |
| gemma4:e2b-it-q8_0 | d5 | `/mnt/models/d5/supermicro` | 7.58 GiB | no |
| gemma4:e4b-it-q4_K_M | d5 | `/mnt/models/d5/supermicro` | 8.95 GiB | no |
| gemma4:e4b-it-q8_0 | d5 | `/mnt/models/d5/supermicro` | 10.84 GiB | no |
| llama3.1:8b-instruct-q4_K_M | d5 | `/mnt/models/d5/supermicro` | 4.58 GiB | no |
| nomic-embed-text:latest | d5 | `/mnt/models/d5/supermicro` | 261.60 MiB | unknown |
| qwen2.5-coder:14b-instruct-q4_K_M | d5 | `/mnt/models/d5/supermicro` | 8.37 GiB | no |
| qwen2.5-coder:32b-instruct-q3_K_M | d5 | `/mnt/models/d5/supermicro` | 14.84 GiB | unknown |
| qwen2.5-coder:32b-instruct-q4_K_M | d5 | `/mnt/models/d5/supermicro` | 18.49 GiB | unknown |
| qwen2.5-coder:7b | d5 | `/mnt/models/d5/supermicro` | 4.36 GiB | no |
| starcoder2:15b | d5 | `/mnt/models/d5/supermicro` | 8.44 GiB | unknown |

## Canonical location (deduplicated)

One row per `model:tag`. **Canonical** is the preferred disk copy; **Replicas** are additional full mirrors on other disks.

| Ollama `model:tag` | Canonical disk | Archive root | Replicas | ~Size | `supermicro_cleared` |
|---|---:|---|---|---:|---|
| deepseek-coder-v2-16b-ctx8k:latest | d5 | `/mnt/models/d5/supermicro` | — | 8.29 GiB | unknown |
| deepseek-coder-v2:16b | d5 | `/mnt/models/d5/supermicro` | — | 8.29 GiB | no |
| deepseek-coder:33b-instruct-q4_K_M | d5 | `/mnt/models/d5/supermicro` | — | 18.57 GiB | unknown |
| deepseek-coder:6.7b | d5 | `/mnt/models/d5/supermicro` | — | 3.56 GiB | no |
| deepseek-r1:14b-qwen-distill-q4_K_M | d5 | `/mnt/models/d5/supermicro` | — | 8.37 GiB | no |
| deepseek-r1:8b-0528-qwen3-q4_K_M | d5 | `/mnt/models/d5/supermicro` | — | 4.87 GiB | no |
| dolphin-llama3:8b | d5 | `/mnt/models/d5/supermicro` | — | 4.34 GiB | no |
| dolphin-mistral:latest | d5 | `/mnt/models/d5/supermicro` | — | 3.83 GiB | no |
| gemma4-26b-a4b-q4-ctx8k:latest | d5 | `/mnt/models/d5/supermicro` | — | 16.75 GiB | unknown |
| gemma4:26b-a4b-it-q4_K_M | d5 | `/mnt/models/d5/supermicro` | — | 16.75 GiB | no |
| gemma4:31b-it-q4_K_M | d5 | `/mnt/models/d5/supermicro` | — | 18.50 GiB | unknown |
| gemma4:e2b-it-q4_K_M | d5 | `/mnt/models/d5/supermicro` | — | 6.67 GiB | no |
| gemma4:e2b-it-q8_0 | d5 | `/mnt/models/d5/supermicro` | — | 7.58 GiB | no |
| gemma4:e4b-it-q4_K_M | d5 | `/mnt/models/d5/supermicro` | — | 8.95 GiB | no |
| gemma4:e4b-it-q8_0 | d5 | `/mnt/models/d5/supermicro` | — | 10.84 GiB | no |
| llama3.1:8b-instruct-q4_K_M | d5 | `/mnt/models/d5/supermicro` | — | 4.58 GiB | no |
| nomic-embed-text:latest | d5 | `/mnt/models/d5/supermicro` | — | 261.60 MiB | unknown |
| qwen2.5-coder:14b-instruct-q4_K_M | d5 | `/mnt/models/d5/supermicro` | — | 8.37 GiB | no |
| qwen2.5-coder:32b-instruct-q3_K_M | d5 | `/mnt/models/d5/supermicro` | — | 14.84 GiB | unknown |
| qwen2.5-coder:32b-instruct-q4_K_M | d5 | `/mnt/models/d5/supermicro` | — | 18.49 GiB | unknown |
| qwen2.5-coder:7b | d5 | `/mnt/models/d5/supermicro` | — | 4.36 GiB | no |
| starcoder2:15b | d5 | `/mnt/models/d5/supermicro` | — | 8.44 GiB | unknown |

## Machine-readable source

- Full scan (one row per model × disk): [`docs/data/ollama-vm-models-inventory.yaml`](data/ollama-vm-models-inventory.yaml).
- **Deduplicated global manifest** (one row per model): [`docs/data/ollama-archival-global-manifest.yaml`](data/ollama-archival-global-manifest.yaml).
- Rotation log: [`docs/data/ollama-sync-rotation.state`](data/ollama-sync-rotation.state).

