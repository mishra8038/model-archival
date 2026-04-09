# vLLM archive workflow (archival VM)

**Source of truth:** this folder is **in the monorepo**. On the archive VM, **`git pull`** at the clone root (e.g. `/home/x/dev/model-archival`); scripts are **`./vllm-hosting/...`** from that root.

## Intent

- **Was:** pull quantized **Ollama** blobs to `d5/supermicro` (and related sync).
- **Now:** pull **Hugging Face** checkpoints that **vLLM** can load (typically **safetensors**, BF16/FP16-class), into **`/mnt/models/d1/vllm`** (override with `VLLM_ARCHIVE_ROOT`; **`/mnt/models/d5/vllm`** may symlink here).

## Immediate target queue (default for pulls)

**Operator default:** `config/vllm-immediate-targets.yaml` — **highly focused** list for **near-term** vLLM use:

| Rule | Value |
|------|--------|
| Parameters | **> 21B** total (dense or MoE **total** param count) |
| Disk (approx) | **< 120 GiB** per HF snapshot |
| Contents | **Causal** chat / code / VLM only — **no** small chat, embeddings, or encoder-only models |
| Roles | `general` \| `specialist` \| `uncensored` (`target_category` on each row) |

- **Regenerate** after edits: `uv run python vllm-hosting/scripts/_generate_vllm_immediate_targets.py`
- **Sequential pull** (`vllm-archive-pull-one.sh`) uses this file **by default**. For the older wide catalog:  
  `... vllm_archive_pull_one.py --manifest vllm-hosting/config/vllm-archive-manifest.yaml`

**Rough total** (~sum of `approx_disk_gib`): see `approx_total_disk_gib_sum` inside the YAML (order-of-magnitude).

### Archiver vs `huggingface-cli` (recommendation)

| Path | When to use |
|------|-------------|
| **`vllm_archive_pull_one.py` + `huggingface-cli download`** | Fast, simple drops into **`HF_HOME` / hub cache** under **`VLLM_ARCHIVE_ROOT`**; good when you only need weights for vLLM and accept **no** archiver `manifest.json` + `.sha256` fleet layout. |
| **`uv run archiver download`** + **`model-archival/config/registry-vllm.yaml`** | **Final vLLM list** (from **`vllm-target-list-2.yaml`**) with **`drive: d5_vllm`** → trees under **`/mnt/models/d1/vllm/raw/…`** and **`…/uncensored/…`** (logical label **`d5_vllm`**; separate from **`d5/raw`**). Run: **`bash model-archival/scripts/run-vllm-d5-archiver.sh`** (2 MiB/s cap). Scratch stays on **D1/.tmp**; infra on **D3**. |
| **`model-archival/config/registry-vllm-immediate.yaml`** | Older **16-repo** immediate slice; edit **`drive:`** if **ENOSPC** on a disk. |

Edit **`drive:`** fields if a host is **ENOSPC** (for **registry-vllm**, the canonical vLLM tree is **`d5_vllm`** only).

## Wide catalog (reference)

The manifest derived from the former Ollama queue + many specialists/encoders remains for **inventory / diffing**:

| Path | Role |
|------|------|
| `vllm-hosting/config/vllm-immediate-targets.yaml` | **Default pull queue** — >21B, <120 GiB, general/specialist/uncensored only |
| `vllm-hosting/config/vllm-archive-manifest.yaml` | Broad HF list + `target_category` + `covers_ollama_tags` + `approx_disk_gib` + policy block |
| `vllm-hosting/config/vllm-archive-manifest-pared-by-family.yaml` | One model per family (core/uncensored) + full specialist set; regen `_pare_vllm_manifest_by_family.py` |
| `vllm-hosting/config/vllm-target-list-2.yaml` | Pared list + prunes (incl. Gemma-4-26B) + no math + legal large-only + **drops rows whose `covers_ollama_tags` match `ollama-hosting/registry/TARGET_QUEUE_ORDERED.txt`** (no HF duplicate of Ollama queue); regen `_build_vllm_target_list_2.py`; use with `vllm_archive_pull_one.py --manifest …` |
| `model-archival/config/registry-vllm.yaml` | Archiver registry mirroring target-list **21**; **`d5_vllm`** → **`/mnt/models/d1/vllm/`** |
| `model-archival/scripts/run-vllm-d5-archiver.sh` | **`run.sh`** wrapper: **`--registry registry-vllm.yaml`**, **`--drive d5_vllm`**, **`--bandwidth-cap 2`** |
| `vllm-hosting/scripts/_generate_vllm_immediate_targets.py` | Regenerates **immediate** YAML from the curated Python table |
| `vllm-hosting/config/env-archive-vm-vllm.sh` | `HF_HOME`, `VLLM_ARCHIVE_ROOT`, optional `HF_TOKEN` from `~/.hf_token` |
| `vllm-hosting/scripts/vllm-archive-setup-dirs.sh` | Creates **`VLLM_ARCHIVE_ROOT`** tree once (default **`d1/vllm`**) |
| `vllm-hosting/scripts/vllm-archive-pull-one.sh` | Wrapper: **one** `huggingface-cli download` per invocation |
| `vllm-hosting/scripts/vllm_archive_pull_one.py` | Queue + lock + `completed_repos.txt` |
| `vllm-hosting/scripts/_generate_vllm_manifest.py` | Regenerates the YAML from the Python table |

## Disk estimate

- **Immediate queue** (`vllm-immediate-targets.yaml`): **~948 GiB** summed (16 models, regenerate after edits) — still **> D5** alone; plan **D2** `VLLM_ARCHIVE_ROOT` or **subset pulls**.
- **Wide manifest** (`vllm-archive-manifest.yaml`): see **`approx_total_disk_gib_sum`** there; **70B+** and **122B** class sit under **`policy.excluded_over_limit`** when over cap.

Figures are **order-of-magnitude** (shard counts, MoE totals, and HF revisions change). Check `df -h` before large pulls (e.g. Mixtral‑class ~87 GiB, Gemma‑4‑26B MoE ~56 GiB).

## Bandwidth

- Default **`THROTTLE_KBPS=2048`** → **2048 KiB/s ≈ 2 MiB/s** download via **`trickle`** (same convention as `ollama-pull-queue`).
- **`USE_TRICKLE=0`** disables the cap (use if `trickle` is not installed yet — on Artix: `sudo pacman -S trickle`, or Debian-style: `sudo apt install trickle`).

## Gated / licence

Several repos need **HF access + licence acceptance** and **`HF_TOKEN`**:

- `meta-llama/*` (in-manifest: 8B, 3B, 11B vision)
- `google/gemma-*`, `google/medgemma-*`, `google/embeddinggemma-*`

Use `huggingface-cli login` or `~/.hf_token` (the env script exports it when present).

## Operational commands (VM)

```bash
ssh x@192.168.8.65
cd /home/x/dev/model-archival
git pull
./vllm-hosting/scripts/vllm-archive-setup-dirs.sh
source vllm-hosting/config/env-archive-vm-vllm.sh
export MODEL_ARCHIVAL_UV_ROOT=/home/x/dev/model-archival/model-archiver   # optional

./vllm-hosting/scripts/vllm-archive-pull-one.sh --list
./vllm-hosting/scripts/vllm-archive-pull-one.sh --dry-run
# when ready:
./vllm-hosting/scripts/vllm-archive-pull-one.sh
```

## Mapping notes

- **Ollama Q4/Q8 tags** are **not** downloaded; the **full HF snapshot** replaces them for vLLM.
- **`deepseek-r1:8b-0528-qwen3-q4_K_M`** maps to specialist **`deepseek-ai/DeepSeek-R1-0528-Qwen3-8B`**; **`deepseek-r1:8b-llama-distill-q4_K_M`** stays on **`deepseek-ai/DeepSeek-R1-Distill-Llama-8B`** (core).
- **Specialist** rows come from **`registry-specialists`** / `model-archival/docs/SPECIALIST-HF-PENDING-OLLAMA.md` style coverage (embeddings, code, math, VLM).
- **Uncensored** rows are **abliterated / merge** checkpoints under 120 GiB (huihui-ai, FINGU-AI), distinct from censored base instruct weights where both exist.
- **Immediate vLLM slice:** edit **`scripts/_generate_vllm_immediate_targets.py`** (ordering, adds/removals); wide catalog: **`scripts/_generate_vllm_manifest.py`**.
