# vLLM archive workflow (archival VM)

**Source of truth:** this folder is **in the monorepo**. On the archive VM, **`git pull`** at the clone root (e.g. `/home/x/dev/model-archival`); scripts are **`./vllm-hosting/...`** from that root.

## Intent

- **Was:** pull quantized **Ollama** blobs to `d5/supermicro` (and related sync).
- **Now:** pull **Hugging Face** checkpoints that **vLLM** can load (typically **safetensors**, BF16/FP16-class), into **`/mnt/models/d5/vllm`** (override with `VLLM_ARCHIVE_ROOT`).

The manifest starts from the same *intent* as `ollama-hosting/registry/TARGET_QUEUE_ORDERED.txt` (**deduped by HF repo**), then applies a **120 GiB cap per model** (`policy.max_approx_disk_gib_per_model`), documents **excluded** larger checkpoints under `policy.excluded_over_limit`, and appends **specialist** + **uncensored** hostable rows (`target_category` on each entry).

## Files

| Path | Role |
|------|------|
| `vllm-hosting/config/vllm-archive-manifest.yaml` | Canonical HF repos + `target_category` + `covers_ollama_tags` + `approx_disk_gib` + policy block |
| `vllm-hosting/config/env-archive-vm-vllm.sh` | `HF_HOME`, `VLLM_ARCHIVE_ROOT`, optional `HF_TOKEN` from `~/.hf_token` |
| `vllm-hosting/scripts/vllm-archive-setup-dirs.sh` | Creates `d5/vllm` tree once |
| `vllm-hosting/scripts/vllm-archive-pull-one.sh` | Wrapper: **one** `huggingface-cli download` per invocation |
| `vllm-hosting/scripts/vllm_archive_pull_one.py` | Queue + lock + `completed_repos.txt` |
| `vllm-hosting/scripts/_generate_vllm_manifest.py` | Regenerates the YAML from the Python table |

## Disk estimate

- **Summed `approx_disk_gib` (manifest):** see **`approx_total_disk_gib_sum`** in the YAML (regenerate after edits). With the **120 GiB cap**, totals are **much lower** than the pre-cap queue; **70B+ class** and **Gemma‑4 31B**, **Qwen3.5‑122B**, **72B VL**, etc. are listed only under **`policy.excluded_over_limit`**.
- **D5 (~916 GiB)** may still require **subsets** or **`VLLM_ARCHIVE_ROOT`** on **D2** for the full capped list.

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
- Adjust **`scripts/_generate_vllm_manifest.py`** if you need different ordering or more rows.
