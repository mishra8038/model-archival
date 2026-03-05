# MODEL-ARCHIVAL — Project Prompt
**Version:** 1.0 — 2026-03-04  
**Purpose:** Portable AI context document. A future AI agent reading this file should be able to fully understand the project, its goals, its architecture, and resume work without the original transcript.

---

## 1. Project Mission

Build and operate a system to **systematically download, archive, verify, and manage the weights of major open-source LLMs and LRMs** from HuggingFace for permanent offline storage and future inference — completely unattended, resumable across interruptions, and cryptographically verified.

This is a long-running infrastructure project. The downloads total ~7 TB across ~40 models and take days to complete on a home internet connection.

---

## 2. Environment

### Target machine
- **Type:** Linux VM running inside Proxmox on a home server
- **OS:** [PLACEHOLDER: MX Linux 23 (Debian-based) or Artix Linux (Arch-based)]
- **IP:** `root@192.168.8.160` (local network)
- **Root SSD:** 256 GB — project code and Python venv only, no model data
- **Project path on VM:** `/opt/model-archival/`

### Development machine
- This repo is developed on a separate Linux workstation at `/home/x/dev/model-archival/`
- Code is pushed to GitHub (`github.com/mishra8038/model-archival`) and rsync'd / git-pulled to the VM

### Physical storage (mounted inside VM via Proxmox disk passthrough)
| Label | Mount | Raw Size | Post-format | Role |
|-------|-------|----------|-------------|------|
| D1 | `/mnt/models/d1` | 6 TB | ~5.5 TB | Raw BF16 giants (Tier A/B large); `.tmp` scratch dir |
| D2 | `/mnt/models/d2` | 3 TB | ~2.7 TB | Raw BF16 mid-size (Tier A/B small + Tier D uncensored) |
| D3 | `/mnt/models/d3` | 3 TB | ~2.7 TB | Quantized GGUF (Tier C + Tier D quants) |
| D5 | `/mnt/models/d5` | 1 TB | ~0.9 TB | Archive metadata, logs, state, STATUS.md |

D4 (2TB Seagate) was removed — hardware attachment issue with Proxmox passthrough. All models originally assigned to D4 were reassigned to D2.

All disks formatted ext4. Mounted via `/etc/fstab` by UUID. In-progress downloads go to `D1/.tmp/` (largest headroom). No model data ever touches the root SSD.

---

## 3. Model Tiers

Models are organised into four tiers. The canonical list lives in `config/registry.yaml`.

| Tier | Type | Format | Approx Size |
|------|------|--------|-------------|
| A | Major general/reasoning models | Raw BF16 safetensors | ~4.3 TB |
| B | Code-specialist models | Raw BF16 safetensors | ~0.9 TB |
| C | Quantized inference models | GGUF Q4_K_M / Q8_0 | ~0.4 TB |
| D | Uncensored / abliterated variants | Raw BF16 + GGUF | ~0.5 TB |

### Tier A — Key models
DeepSeek-V3 (~1340 GB), DeepSeek-R1 (~850 GB), DeepSeek-R1-Distill-Llama-70B, DeepSeek-R1-Distill-Qwen-32B, Qwen2.5-72B-Instruct, Qwen2.5-32B-Instruct, Qwen2.5-7B-Instruct, Mistral-7B-v0.3, Phi-4, Command-R+, Llama-3.1-405B-Instruct, Llama-3.1-70B-Instruct, Llama-3.3-70B-Instruct, Llama-3.1-8B-Instruct, Gemma-3-27B-IT/PT, Gemma-3-12B-IT, Mistral-Large-2407

### Tier B — Key models
DeepSeek-Coder-V2-Instruct, Qwen2.5-Coder-32B-Instruct, Qwen2.5-Coder-7B-Instruct, CodeLlama-70B-Instruct, Codestral-22B

### Priority system
- **Priority 1** — token-free, download immediately
- **Priority 2** — gated, require HF token (Meta Llama, Google Gemma, Mistral)

Full model list: `docs/REQUIREMENTS.md` sections 3–6. Token acquisition guide: `docs/HF-TOKEN-GUIDE.md`.

---

## 4. Architecture Overview

### Python project (`src/archiver/`)

Managed with `uv`. Entry point: `uv run archiver`. Installed as a script in `pyproject.toml`.

```
archiver/
├── cli.py           click CLI: download, verify, status, list, pin, drives, tokens, report
├── downloader.py    Per-model download orchestration
├── scheduler.py     Per-drive worker thread pool, bandwidth sampling, priority queue
├── verifier.py      SHA-256, .sha256 sidecars, manifest.json, DESCRIPTOR files, global index
├── status.py        Rich live console display + STATUS.md writer + RunReport class
├── state.py         run_state.json — persistent per-model status across restarts
├── preflight.py     Pre-flight checks: aria2c, registry, network, drives, HF token
├── models.py        ModelEntry, DriveConfig, Registry dataclasses + YAML loader
└── aria2_manager.py aria2c daemon lifecycle, aria2p wrapper, speed sampling
```

### Key dependencies
| Package | Role |
|---------|------|
| `huggingface_hub` | HF API, file metadata, LFS URLs, XET downloads |
| `aria2p` | Python wrapper around aria2c daemon (LFS downloads) |
| `aria2c` (system) | Primary HTTP download engine — resumable, multi-connection |
| `click` | CLI framework |
| `rich` | Console live display |
| `psutil` | Disk usage, throughput monitoring |
| `pyyaml` | Registry and drives config parsing |
| `httpx` | HTTP for pre-flight network checks |

### Bash scripts
```
run.sh                              Root orchestrator — entry point for all operations
deploy/_common.sh                   Shared bash library (logging, reporting, run_cmd, step/banner)
deploy/setup-mxlinux.sh             OS setup: apt packages + uv + project sync (MX Linux / Debian)
deploy/setup-artix.sh               OS setup: pacman packages + uv + project sync (Artix / Arch)
deploy/proxmox-attach-disks.sh      Run on Proxmox HOST: discover HDDs, attach to VM 106 via qm
deploy/vm-mount-disks.sh            Run in VM: identify, partition (GPT), format (ext4), mount disks
deploy/verify-environment.sh        Pre-execution environment check with timestamped report
deploy/fix-apparmor-cursor.sh       Fix Cursor Remote SSH AppArmor sandbox error on Debian kernel 6.2+
deploy/sethfToken.sh                Safely store HF token to ~/.hf_token (never in the repo)
scripts/archiver-download.sh        Thin wrapper: uv run archiver download [ARGS]
scripts/archiver-verify.sh          Thin wrapper: uv run archiver verify [ARGS]
scripts/archiver-status.sh          Thin wrapper: uv run archiver status
scripts/archiver-drives.sh          Thin wrapper: uv run archiver drives status
scripts/archiver-list.sh            Thin wrapper: uv run archiver list [ARGS]
scripts/check-environment.sh        Thin wrapper: deploy/verify-environment.sh
scripts/verify-archive.sh           Thin wrapper: verification/verify-archive.py (auto-reads drives.yaml)
verification/verify-archive.py      Standalone integrity verifier — no archiver import, stdlib only
```

---

## 5. Download Design

### Two download paths (per file)

HuggingFace uses two storage backends. The path is chosen per-file based on `sibling.lfs` metadata from the repo info API:

**LFS files** (legacy, most current models):
- Resolve CDN URL via `hf_hub_url()` immediately before submission (CDN pre-signed URLs expire in ~1 hour)
- Submit to `aria2c` daemon via `aria2p` with `--continue=true`
- `aria2c` writes a `<filename>.aria2` control file alongside the partial download in `D1/.tmp/<model_id>/`
- On restart, `aria2c` finds the control file and resumes from exact byte offset — nothing is re-fetched
- Authorization header sent only to HF resolve URL, not forwarded to CDN redirect (correct behaviour)

**XET files** (new backend, default since May 2025 — Llama 4, Qwen 3, future models):
- `aria2c` cannot speak the two-stage CAS reconstruction protocol
- Use `hf_hub_download()` which calls `hf_xet` internally
- `hf_xet` manages its own `.incomplete/` cache directory across restarts

### Resume / idempotency (four layers, outermost to innermost)

1. **`run_state.json`** — models marked `complete` are skipped by the scheduler before any work begins
2. **`_check_manifest_complete()`** — if `manifest.json` exists and every listed file has a `.sha256` sidecar, skip the model entirely without any HF API call (fast-path, handles lost `run_state.json`)
3. **`.sha256` sidecar** — if a file exists at its final path with a matching sidecar, skip that file unconditionally (file-level idempotency)
4. **`aria2c --continue=true`** — partial downloads in `.tmp/` are resumed byte-exactly via `.aria2` control files (handles mid-file interruption)

### Post-download verification

After every model download (and after fast-path skips), `_post_verify()` cross-checks every file's `.sha256` sidecar against the manifest. This is fast (no re-hash — sidecar existence + value check). Any mismatch raises `DownloadError` and marks the model failed for retry.

Full re-hash from disk is available via `archiver verify --all` or `verification/verify-archive.py --rehash`.

---

## 6. Integrity & Provenance

Per file:
- `<filename>.sha256` sidecar — written immediately after download, format: `<hex>  <filename>`

Per model version (in the model directory):
- `manifest.json` — all file paths, SHA-256, sizes, commit SHA, archived_at timestamp
- `DESCRIPTOR.json` — machine-readable provenance: model ID, HF repo, commit URL, tier, licence, requires_auth, total size, file summary
- `DESCRIPTOR.md` — human-readable version of the above, with verification instructions

Global:
- `D5/archive/checksums/global_index.jsonl` — append-only JSONL, one record per model, replicated to D1/D2/D3

Directory structure per model:
```
/mnt/models/d1/<hf_org>/<model_name>/<commit_sha>/
    model-00001-of-00014.safetensors
    model-00001-of-00014.safetensors.sha256
    ...
    config.json
    tokenizer.json
    manifest.json
    DESCRIPTOR.json
    DESCRIPTOR.md
/mnt/models/d1/<hf_org>/<model_name>/latest -> <commit_sha>/   (symlink)
```

---

## 7. Reporting

### During downloads (live)
- **Rich Live console** — overall progress bar (%, GB, speed, ETA), active downloads per drive, drive usage bars, pending queue, completed list
- **`STATUS.md`** — atomically updated every 60 seconds at `D5/STATUS.md`, readable via `watch -n 30 cat /mnt/models/d5/STATUS.md`
- **`RunReport`** — incremental Markdown written to `D5/logs/run-report-<ts>.md`, one append per event (model start, file download, verification result, model complete/fail, final summary)

### After downloads
- **`verify-report-<ts>.md`** — written by `verify-archive.py` to `D5/logs/` (or `verification/verification-reports/` locally), one section per model with per-file pass/fail table and summary

### run.sh orchestration report
- **`run-report-<ts>.md`** in repo root — covers all 5 steps: env check, drive check, download plan, download outcome, verification summary

---

## 8. CLI Reference

```bash
uv run archiver download --all --priority-only 1   # token-free models only
uv run archiver download --all                     # everything (needs HF_TOKEN for P2)
uv run archiver download --tier A                  # tier A only
uv run archiver download deepseek-ai/DeepSeek-R1   # single model
uv run archiver download --all --dry-run           # preview only

uv run archiver verify --all                       # verify all completed models (sidecar)
uv run archiver status                             # per-model status table
uv run archiver status --drive d1                  # filter by drive
uv run archiver list                               # registry table
uv run archiver list --tier A                      # filter by tier
uv run archiver drives status                      # drive usage
uv run archiver tokens check                       # test HF token against gated repos
uv run archiver pin <model_id> <commit_sha>        # pin a model to a commit
uv run archiver report                             # regenerate STATUS.md from state
```

Wrapper scripts in `scripts/` call these via `uv run` with correct working directory.

---

## 9. run.sh — Orchestrator

The single entry point for all operations on the VM. Always run from the repo root.

```bash
bash run.sh                         # download everything (P1 + P2)
bash run.sh --dry-run               # full pipeline simulation, no downloads
bash run.sh --priority-only 1       # P1 token-free only
bash run.sh --tier A                # tier A only
bash run.sh --rehash                # after download, full SHA-256 re-hash
bash run.sh --bandwidth-cap 200     # cap at 200 MB/s
bash run.sh --skip-env-check        # skip environment verification step
bash run.sh --skip-verify           # skip post-download integrity verification
```

**Pipeline steps:**
1. `uv sync` — ensure venv current
2. Step 1: `deploy/verify-environment.sh` — tools, Python, registry, network, HF token
3. Step 1b: Drive mount check — per drive: mounted, separate fs, writable, free space
4. Step 2: Download plan preview (`archiver download --dry-run`)
5. Step 3: Download — screen/tmux detection with 10s warning if absent
6. Step 4: `archiver status` snapshot
7. Step 5: `verify-archive.py` integrity check

**Token loading:** auto-loaded from `~/.hf_token` if `HF_TOKEN` not in environment.
**Screen detection:** checks `$STY` (screen) and `$TMUX`. Warns loudly if absent, waits 10s, then proceeds.
**Report:** `run-report-<timestamp>.md` written to repo root throughout execution.

---

## 10. Deployment Sequence (first time on a new VM)

```bash
# ── On the Proxmox HOST ────────────────────────────────────────────────────
# Identify and attach physical HDDs to VM 106:
bash deploy/proxmox-attach-disks.sh

# ── On the VM (SSH in) ────────────────────────────────────────────────────
# Copy project:
rsync -av --exclude='.venv' --exclude='__pycache__' --exclude='.git' \
  /home/x/dev/model-archival/ root@192.168.8.160:/opt/model-archival/

# Install OS dependencies (choose one):
bash /opt/model-archival/deploy/setup-mxlinux.sh   # Debian/MX Linux
bash /opt/model-archival/deploy/setup-artix.sh     # Artix/Arch

# Partition, format, mount disks:
bash /opt/model-archival/deploy/vm-mount-disks.sh --wipe

# Set HF token:
bash /opt/model-archival/deploy/sethfToken.sh hf_YOURTOKEN
source ~/.bashrc

# Sync Python environment:
cd /opt/model-archival && uv sync

# Verify everything is ready:
bash run.sh --dry-run              # must show 0 failures

# Start downloads inside screen:
screen -S archiver
bash run.sh
# Ctrl+A D to detach

# Monitor from anywhere:
watch -n 30 cat /mnt/models/d5/STATUS.md
screen -r archiver

# Post-download integrity check:
bash scripts/verify-archive.sh
```

---

## 11. HF Token Management

- Store with: `bash deploy/sethfToken.sh hf_YOURTOKEN`
- Written to: `~/.hf_token` (chmod 600) — never in the repo
- Persisted via: `export HF_TOKEN=$(cat ~/.hf_token)` appended to `~/.bashrc`
- `run.sh` auto-loads it from `~/.hf_token` if `HF_TOKEN` not already exported
- Token guide: `docs/HF-TOKEN-GUIDE.md`
- Tokens needed for: Meta Llama (llama.meta.com), Google Gemma (ai.google.dev), Mistral (mistral.ai)

**Security rule:** never put a token value in any file tracked by git. `sethfToken.sh` and `*.token` are in `.gitignore`.

---

## 12. Configuration Files

### `config/drives.yaml`
```yaml
d1:
  mount_point: /mnt/models/d1
  role: "Raw giants (Tier A large + Tier B large)"
  tmp_dir: /mnt/models/d1/.tmp

d2:
  mount_point: /mnt/models/d2
  role: "Raw mid-size (Tier A remainder + Tier B small + Tier D uncensored raw)"

d3:
  mount_point: /mnt/models/d3
  role: "Quantized GGUF (Tier C + Tier D quants)"

d5:
  mount_point: /mnt/models/d5
  role: "Primary archive/ + logs + .tmp scratch"
```

### `config/registry.yaml` structure (per model)
```yaml
models:
  - id: deepseek-ai/DeepSeek-R1
    hf_repo: deepseek-ai/DeepSeek-R1
    commit_sha: ""          # filled in by archiver pin after first download
    tier: A
    priority: 1
    drive: d1
    licence: MIT
    requires_auth: false
    notes: ""
    quant_levels: []        # non-empty for Tier C (e.g. ["Q4_K_M", "Q8_0"])
```

---

## 13. Known Issues & Constraints

| Issue | Status | Notes |
|-------|--------|-------|
| D4 (2TB Seagate) hardware | Removed | Proxmox passthrough failed; models reassigned to D2 |
| XET storage incompatibility with aria2c | Resolved | XET path uses `hf_hub_download()` |
| CDN pre-signed URL expiry | Resolved | URL re-fetched fresh before each aria2 submission |
| Root SSD space | Mitigated | All runtime paths forced to storage drives; pre-flight checks root SSD |
| AppArmor Cursor Remote SSH | Resolved | `deploy/fix-apparmor-cursor.sh` applies sysctl + profile fixes |
| HF token committed to git | Remediated | Commit amended; old token must be revoked; `.gitignore` updated |

---

## 14. Extension Points

When extending this project, an AI agent should:

1. **Add a new model** — edit `config/registry.yaml`, add entry with correct `tier`, `priority`, `drive`, `licence`, `requires_auth`
2. **Add a new drive** — edit `config/drives.yaml`, add mount point; update `REQUIREMENTS.md` allocation table
3. **Support a new download backend** — extend `downloader.py` `_resolve_files()` storage detection and add a new `_download_*` method
4. **Add a new CLI command** — add a `@cli.command()` function in `cli.py`
5. **Add a new pre-flight check** — add a function to `preflight.py` and call it from `run_all()`
6. **Update model allocation** — edit `drive:` field in `registry.yaml` entries; no code changes needed

Always run `bash run.sh --dry-run` after any configuration change to validate before a real run.
