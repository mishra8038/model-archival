# vLLM archive workflow (archival VM)

**Source of truth:** this folder is **in the monorepo**. On the archive VM, **`git pull`** at the clone root (e.g. `/home/x/dev/model-archival`); scripts are **`./vllm-hosting/...`** from that root.

## Intent

- **Was:** pull quantized **Ollama** blobs to `d5/supermicro` (and related sync).
- **Now:** pull **Hugging Face** checkpoints that **vLLM** can load (typically **safetensors**, BF16/FP16-class), into **`/mnt/models/d5/vllm`** (override with `VLLM_ARCHIVE_ROOT`).

The ordered target set is the same *intent* as `ollama-hosting/registry/TARGET_QUEUE_ORDERED.txt`, but **deduplicated by HF repo** (one download covers multiple Ollama tags when weights are the same snapshot).

## Files

| Path | Role |
|------|------|
| `vllm-hosting/config/vllm-archive-manifest.yaml` | Canonical **57** HF repos + `covers_ollama_tags` + rough `approx_disk_gib` |
| `vllm-hosting/config/env-archive-vm-vllm.sh` | `HF_HOME`, `VLLM_ARCHIVE_ROOT`, optional `HF_TOKEN` from `~/.hf_token` |
| `vllm-hosting/scripts/vllm-archive-setup-dirs.sh` | Creates `d5/vllm` tree once |
| `vllm-hosting/scripts/vllm-archive-pull-one.sh` | Wrapper: **one** `huggingface-cli download` per invocation |
| `vllm-hosting/scripts/vllm_archive_pull_one.py` | Queue + lock + `completed_repos.txt` |
| `vllm-hosting/scripts/_generate_vllm_manifest.py` | Regenerates the YAML from the Python table |

## Disk estimate

- **Summed `approx_disk_gib` (manifest):** **`~2827 GiB` (~2.76 TiB)** before overhead.
- **D5 (~916 GiB)** is only enough for an **early subset** unless you redirect `VLLM_ARCHIVE_ROOT` (for example **`/mnt/models/d2/vllm`**) or archive in waves.

Figures are **order-of-magnitude** (shard counts, MoE totals, and HF revisions change). Check `df -h` before large pulls (Gemma‑4 31B, Qwen3.5‑122B, 70B class, etc.).

## Bandwidth

- Default **`THROTTLE_KBPS=2048`** → **2048 KiB/s ≈ 2 MiB/s** download via **`trickle`** (same convention as `ollama-pull-queue`).
- **`USE_TRICKLE=0`** disables the cap (use if `trickle` is not installed yet — on Artix: `sudo pacman -S trickle`, or Debian-style: `sudo apt install trickle`).

## Gated / licence

Several repos need **HF access + licence acceptance** and **`HF_TOKEN`**:

- `meta-llama/*`
- `google/gemma-*`, `google/medgemma-*`, `google/embeddinggemma-*`
- `nvidia/Llama-3.1-Nemotron-70B-Instruct-HF`

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
- A few rows are **best-effort** mappings (see `notes` in YAML), e.g. Ollama naming vs HF (`deepseek-r1:8b-0528-qwen3-*` → `DeepSeek-R1-Distill-Llama-8B`, `dolphin-mixtral` tags → one `dphn/dolphin-2.7-mixtral-8x7b` snapshot). Adjust the generator table if you need exact parity.
