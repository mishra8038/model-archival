# vLLM-oriented weight archival

Hugging Face downloads for models that were previously targeted via **Ollama** (`ollama-hosting/registry/TARGET_QUEUE_ORDERED.txt`), reformatted as **HF repo IDs** suitable for **vLLM** (safetensors / BF16-class checkpoints, not GGUF).

This directory lives in the **same monorepo** as `model-archival/` and `ollama-hosting/`. On the **archive VM**, run **`git pull`** in your clone, then use paths below from the **repository root** (no separate rsync tree).

## Layout (archival VM)

- **Root:** `/mnt/models/d5/vllm` (`VLLM_ARCHIVE_ROOT`)
- **HF cache:** `$VLLM_ARCHIVE_ROOT/hf_hub` → `HF_HOME`
- **State:** `$VLLM_ARCHIVE_ROOT/state/completed_repos.txt` (one `org/repo` per line)

**Space:** Each model is capped at **~120 GiB** (`approx_disk_gib`); see **`approx_total_disk_gib_sum`** in `config/vllm-archive-manifest.yaml` after regeneration. A **~916 GiB D5** may still need **subsets** or **`VLLM_ARCHIVE_ROOT=/mnt/models/d2/vllm`**. See `docs/VLLM-ARCHIVE.md`.

## One-time setup on the VM

```bash
cd /home/x/dev/model-archival          # archive VM clone root (typical)
git pull
chmod +x vllm-hosting/scripts/*.sh
./vllm-hosting/scripts/vllm-archive-setup-dirs.sh
```

If `huggingface-cli` is not on `PATH`, either install **`pip install --user 'huggingface_hub[cli]' pyyaml`** or use the existing **`/mnt/models/d5/vllm/venv`** (the env script prepends that `bin/` when present). **Bandwidth cap:** `trickle` — Debian/Ubuntu: `sudo apt install trickle`; Artix: `sudo pacman -S trickle`.

Ensure `~/.hf_token` exists for gated models (Meta Llama, Gemma, Nemotron, MedGemma, …).

## Pull one model (when you are ready)

```bash
cd /home/x/dev/model-archival
source vllm-hosting/config/env-archive-vm-vllm.sh
export MODEL_ARCHIVAL_UV_ROOT=/home/x/dev/model-archival/model-archiver   # optional: uv + PyYAML from archiver project
./vllm-hosting/scripts/vllm-archive-pull-one.sh
```

Dry-run / queue inspection:

```bash
./vllm-hosting/scripts/vllm-archive-pull-one.sh --dry-run
./vllm-hosting/scripts/vllm-archive-pull-one.sh --list
```

## Regenerate manifest YAML

After editing `scripts/_generate_vllm_manifest.py`:

```bash
# Workstation (nested clone):
uv run --directory model-archival python ../vllm-hosting/scripts/_generate_vllm_manifest.py

# Archive VM (flat clone + model-archiver):
uv run --directory model-archiver python vllm-hosting/scripts/_generate_vllm_manifest.py
```
