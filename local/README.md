# local/ — VM Archiver

Unattended, resumable, cryptographically-verified offline archival of open-source LLM and LRM weights from HuggingFace.

Downloads raw BF16/FP16 weights, quantized GGUFs, and uncensored variants across a fleet of physical drives — verifying SHA-256 integrity at every stage, producing structured manifests and provenance descriptors, and running fully unattended inside a `screen` session.

---

## What it archives

| Tier | Models | Format | ~Size |
|------|--------|--------|-------|
| A — Major models | DeepSeek-V3, DeepSeek-R1, Llama 3.x, Qwen2.5, Gemma 3, Mistral Large, Phi-4, Command-R+ | Raw BF16 safetensors | 4.3 TB |
| B — Code models | DeepSeek-Coder-V2, Qwen2.5-Coder, Codestral, Devstral | Raw BF16 safetensors | 0.9 TB |
| C — Quantized | Top models in GGUF Q4_K_M / Q8_0 | GGUF | 0.4 TB |
| D — Uncensored | Dolphin, abliterated Llama/Qwen/Mistral variants | Raw BF16 + GGUF | 0.5 TB |

Full model list: [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md)

---

## Quick start (on the VM)

```bash
# 1. Clone the project
git clone https://github.com/mishra8038/model-archival
cd model-archival/local

# 2. Install OS dependencies
bash deploy/setup-artix.sh      # Artix / Arch Linux
# or: bash deploy/setup-mxlinux.sh  # Debian / MX Linux

# 3. Mount storage drives (first time only — destructive)
sudo bash deploy/vm-mount-disks.sh --wipe

# 4. Set your HuggingFace token (needed for gated models)
bash deploy/sethfToken.sh hf_YOURTOKEN
source ~/.bashrc

# 5. Dry run
bash run.sh --dry-run

# 6. Start downloads inside screen (survives SSH disconnect)
screen -S archiver bash run.sh --all
# Ctrl+A D  → detach   |   screen -r archiver  → reattach
```

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the complete first-time setup guide.

---

## Entry points

### `run.sh` — universal orchestrator

```bash
bash run.sh --all                  # download everything (P1 + P2, all tiers)  [default]
bash run.sh --dry-run              # simulate full pipeline, no downloads
bash run.sh --priority-only 1      # token-free models only (no HF token needed)
bash run.sh --tier A               # Tier A only
bash run.sh --bandwidth-cap 200    # cap at 200 MB/s
bash run.sh --rehash               # full SHA-256 re-hash after download
bash run.sh --skip-env-check       # skip environment verification step
```

### `stop.sh` — graceful shutdown

```bash
bash stop.sh                # stop after current shard finishes (fully resumable)
bash stop.sh --force        # force-kill immediately
bash stop.sh --status       # show PID and process info
```

Always use `stop.sh` before rebooting to avoid filesystem corruption.

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

---

## Monitoring

```bash
# Snapshot current screen output without attaching:
screen -S archiver -X hardcopy /tmp/status.txt && cat /tmp/status.txt

# Live status file (updated every ~60s):
watch -n 30 cat /mnt/models/d5/STATUS.md

# Reattach to running session:
screen -r archiver

# Per-model status:
uv run archiver status

# Drive usage:
uv run archiver drives status
```

The live screen GUI shows bandwidth (MB/s and Mbps) in the Active Downloads panel, per-drive speed, elapsed time, and ETA.

---

## Storage layout

| Drive | Mount | Size | Role |
|-------|-------|------|------|
| D1 | `/mnt/models/d1` | 6 TB | Tier A/B large models + `.tmp/` scratch |
| D2 | `/mnt/models/d2` | 3 TB | Tier A/B mid-size + Tier D uncensored |
| D3 | `/mnt/models/d3` | 3 TB | Tier C/D quantized GGUF |
| D5 | `/mnt/models/d5` | 1 TB | Metadata, logs, state, STATUS.md |

All in-progress downloads use `D1/.tmp/`. No data ever touches the root SSD.

In addition, `config/drives.yaml` should record the **physical disk identifiers**
for each logical drive (D1, D2, D3, D5) using `by_id` and/or `serial` fields.
Fill these from `ls -l /dev/disk/by-id` and `lsblk -o NAME,SERIAL` on the VM.
This lets you re-establish which disk is which if Proxmox/VM mappings change.

---

## Registry evolution, topology, and future GC

Over time the **model list will change** as the leaderboard evolves and new releases appear. The archiver is designed so that future runs can:

- **Snapshot registries:** when you materially change `config/registry.yaml`, copy it to a dated snapshot such as `config/registry-2026-03-09.yaml` and commit it. This gives you a full history of what was “in scope” for each archival run.
- **Describe disk topology explicitly:** keep a small `config/topology.yaml` (planned) that records drives, capacities, and which tiers are allowed on each drive. Example:

  ```yaml
  drives:
    d1: { mount: /mnt/models/d1, capacity_tb: 5543.9, tiers: [A, B] }
    d2: { mount: /mnt/models/d2, capacity_tb: 2749.6, tiers: [A, B, D] }
    d3: { mount: /mnt/models/d3, capacity_tb: 2749.6, tiers: [C, D, G] }
  ```

- **Reconcile old vs new registries (future `archiver reconcile` mode):**
  - Compare an old snapshot (`registry-YYYYMMDD.yaml`) to the current `registry.yaml`.
  - Classify models as **kept** (in both), **dropped** (only in old), or **new** (only in current).
  - For kept models, verify that weights still exist on disk and optionally cross-check against fingerprints.
  - For dropped models, generate a **GC plan** listing which model directories could be safely deleted to reclaim space.
  - For new models, use live drive usage + `topology.yaml` to propose **drive assignments** and update `registry.yaml` accordingly.

- **Garbage collection as an explicit step (future `archiver gc` mode):**
  - GC will never delete automatically. Instead it will read a GC plan (for example from `/mnt/models/d5/GC_PLAN.md`), delete only those listed model directories, and mark their entries in `run_state.json` as `deleted`.

Until those commands are implemented, you can still follow the same pattern manually: snapshot the registry before changes, use `MANIFEST.md` + `run_state.json` to see what is on disk, and delete old models by hand if you want to free space for newly added ones.

---

## Documentation

| File | Contents |
|------|---------|
| [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) | Full model list, storage allocation, all requirements |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Step-by-step VM setup from scratch |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Design decisions, module breakdown, data flows |
| [`docs/OPERATIONS.md`](docs/OPERATIONS.md) | Day-to-day operations, monitoring, troubleshooting |
| [`docs/HF-TOKEN-GUIDE.md`](docs/HF-TOKEN-GUIDE.md) | How to obtain HF tokens for gated models |
