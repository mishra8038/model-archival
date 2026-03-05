# model-archival

Unattended, resumable, cryptographically-verified offline archival of open-source LLM and LRM weights from HuggingFace.

Downloads raw BF16/FP16 weights, quantized GGUFs, and uncensored variants across a fleet of physical drives — verifying SHA-256 integrity at every stage, producing structured manifests and provenance descriptors, and running fully unattended inside a `screen` session.

---

## What it archives

| Tier | Models | Format | ~Size |
|------|--------|--------|-------|
| A — Major models | DeepSeek-V3, DeepSeek-R1, Llama 3.x, Qwen2.5, Gemma 3, Mistral Large, Phi-4, Command-R+ | Raw BF16 safetensors | 4.3 TB |
| B — Code models | DeepSeek-Coder-V2, Qwen2.5-Coder, CodeLlama, Codestral | Raw BF16 safetensors | 0.9 TB |
| C — Quantized | Top models in GGUF Q4_K_M / Q8_0 | GGUF | 0.4 TB |
| D — Uncensored | Dolphin, WizardLM, abliterated Llama variants | Raw BF16 + GGUF | 0.5 TB |

Full model list: [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md)

---

## Quick start (on the VM)

```bash
# 1. Clone or rsync the project
git clone https://github.com/mishra8038/model-archival /opt/model-archival
cd /opt/model-archival

# 2. Install OS dependencies and Python env
bash deploy/setup-mxlinux.sh      # Debian / MX Linux
# or: bash deploy/setup-artix.sh  # Artix / Arch Linux

# 3. Mount storage drives (first time only)
bash deploy/vm-mount-disks.sh --wipe

# 4. Set your HuggingFace token (needed for Meta/Google/Mistral gated models)
bash deploy/sethfToken.sh hf_YOURTOKEN
source ~/.bashrc

# 5. Verify the environment
bash run.sh --dry-run

# 6. Start downloads inside screen (survives SSH disconnect)
screen -S archiver
bash run.sh
# Ctrl+A D  → detach   |   screen -r archiver  → reattach
```

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the complete first-time setup guide.

---

## Entry points

### `run.sh` — universal orchestrator

```bash
bash run.sh                        # download everything (P1 + P2, all tiers)
bash run.sh --dry-run              # simulate full pipeline, no downloads
bash run.sh --priority-only 1      # token-free models only (no HF token needed)
bash run.sh --tier A               # Tier A only
bash run.sh --bandwidth-cap 200    # cap at 200 MB/s
bash run.sh --rehash               # full SHA-256 re-hash after download
bash run.sh --skip-env-check       # skip environment verification step
```

Runs 5 steps in order: environment check → drive check → download plan → download → verify.  
Generates a timestamped Markdown report in the repo root.

### `scripts/` — thin wrappers

```bash
bash scripts/archiver-download.sh  --all --priority-only 1
bash scripts/archiver-verify.sh    --all
bash scripts/archiver-status.sh
bash scripts/archiver-drives.sh
bash scripts/archiver-list.sh      --tier A
bash scripts/check-environment.sh
bash scripts/verify-archive.sh     --failures-only
```

### `archiver` CLI (direct)

```bash
uv run archiver download  --all [--tier X] [--priority-only N] [--dry-run]
uv run archiver verify    --all [--tier X] [--drive dN]
uv run archiver status    [--drive dN]
uv run archiver list      [--tier X] [--json]
uv run archiver drives    status
uv run archiver tokens    check
uv run archiver pin       <model-id> <commit-sha>
uv run archiver report
```

### `verification/verify-archive.py` — standalone integrity verifier

```bash
# Fast sidecar cross-check (seconds):
python3 verification/verify-archive.py --drives /mnt/models/d1 /mnt/models/d2

# Full SHA-256 re-hash from disk (hours):
python3 verification/verify-archive.py --drives /mnt/models/d1 --rehash

# Single model:
python3 verification/verify-archive.py --model-dir /mnt/models/d1/deepseek-ai/DeepSeek-R1/abc123

# Failures only, tier A:
python3 verification/verify-archive.py --drives /mnt/models/d1 --tier A --failures-only
```

No archiver import required — runs with stdlib only.

---

## Monitoring

```bash
# Live status file (updated every ~60s):
watch -n 30 cat /mnt/models/d5/STATUS.md

# Reattach to running download session:
screen -r archiver

# Current model status table:
bash scripts/archiver-status.sh

# Drive usage:
bash scripts/archiver-drives.sh
```

All run reports land in `/mnt/models/d5/logs/`.

---

## Storage layout

| Drive | Mount | Size | Role |
|-------|-------|------|------|
| D1 | `/mnt/models/d1` | 6 TB | Tier A/B large models + `.tmp` scratch |
| D2 | `/mnt/models/d2` | 3 TB | Tier A/B mid-size + Tier D uncensored |
| D3 | `/mnt/models/d3` | 3 TB | Tier C/D quantized GGUF |
| D5 | `/mnt/models/d5` | 1 TB | Metadata, logs, state, STATUS.md |

All in-progress downloads use `D1/.tmp/` (largest headroom). No data ever touches the root SSD.

---

## Requirements

- Python ≥ 3.11 (managed by `uv`)
- `aria2c` in PATH — `sudo apt install aria2`
- `screen` — `sudo apt install screen`
- Drives mounted at paths in `config/drives.yaml`
- HF token for gated models — see [`docs/HF-TOKEN-GUIDE.md`](docs/HF-TOKEN-GUIDE.md)

---

## Documentation

| File | Contents |
|------|---------|
| [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) | Full model list, storage allocation, all requirements |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Step-by-step VM setup from scratch |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Design decisions, module breakdown, data flows |
| [`docs/OPERATIONS.md`](docs/OPERATIONS.md) | Day-to-day operations, monitoring, troubleshooting |
| [`docs/HF-TOKEN-GUIDE.md`](docs/HF-TOKEN-GUIDE.md) | How to obtain HF tokens for gated models |
| [`docs/PROJECT_PROMPT.md`](docs/PROJECT_PROMPT.md) | AI regeneration prompt — full project context |
