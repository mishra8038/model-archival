# Project prompt and requirements — model-archival monorepo

**Purpose:** Single entry for humans and agents: **mission**, **subprojects**, **what has been built**, and **requirements** that cut across directories. For the weight-archiver alone, see also [`model-archival/docs/PROJECT_PROMPT.md`](../model-archival/docs/PROJECT_PROMPT.md) and [`model-archival/docs/AI_CONTEXT.md`](../model-archival/docs/AI_CONTEXT.md).

**Curated session history (prefer over raw Cursor transcripts):** [`AGENT_TRANSCRIPT_SUMMARY.md`](AGENT_TRANSCRIPT_SUMMARY.md).  
**Deeper “what the project became” analysis:** [`DERIVED-REQUIREMENTS-ANALYSIS.md`](DERIVED-REQUIREMENTS-ANALYSIS.md).

---

## 1. Mission

**Insurance-first preservation** of open-source AI artifacts: model weights, checksum metadata, source/tooling snapshots, optional cloud copies, and (on the Supermicro) **Ollama-served GGUF-class weights** with an **additive rsync archive** on the disk VM.

Success means unattended, resumable operations, cryptographic verification where applicable, and documentation that survives handoffs between operators and agents.

---

## 2. Subprojects and high-level tasks

Each row is a **coherent subsystem** in this repository. “High-level tasks” summarize work the monorepo is designed to support (not a single sprint changelog).

| Subproject | Primary task | Authoritative inputs / outputs |
|------------|--------------|--------------------------------|
| **`model-archival/`** | Download, verify, and manifest **Hugging Face** weight trees onto **D1–D3**; scheduler, STATUS, run reports; registries (main, legacy, specialists, high-risk, final queues) | `config/registry.yaml`, `drives.yaml`, `/mnt/models/d5/run_state.json`, `STATUS.md`, `manifest.json` per model |
| **`fingerprints/`** | **SHA-256 LFS fingerprints** without downloading weights; leaderboard snapshots | `fingerprints/config/registry.yaml`, `model-checksums/` on disk |
| **`code-archival/`** | **GitHub release / clone snapshots** of inference, training, agent, and UI tooling | `code-archival/registry.yaml` → `/mnt/models/d1/code-archival/` (typical) |
| **`gdrive-archival/`** | **rclone** upload of selected archive roots to Google Drive (registry-driven and/or staging) | `gdrive-registry.yaml`, `config.yaml`, upload logs under `gdrive-archival/logs/` |
| **`gh-archival/`** | **Owned GitHub repos** → shallow clone, `git archive` tarballs, manifest, optional rclone to Drive | `uv run gh-archival`, separate from HF weight layout |
| **`ollama-hosting/`** | **Supermicro Ollama** mirror (scripts, queues, systemd), **rsync** Supermicro `~/.ollama` → archival VM with **disk rotation**, VM **integrity maintain**, **prune planner**, **VM inventory** + **archival model map**; specialist↔Ollama pending report (reads `model-archival/config/`) | `ollama-hosting/scripts/`, `ollama-hosting/docs/data/`, `supermicro-rig/` |
| **`integrity_tools/`** | Misc **verification / integrity** helpers | `integrity_tools/AGENTS.md`, tools per folder |
| **`full-stack/`** | **End-to-end archive utilities** (see sub-README) | `full-stack/README.md` |
| **`multidisk-downloader/`** | **Design contracts** (documentation-first): selector vs downloader vs uploader boundaries | `REQUIREMENTS.md`, `ARCHITECTURE-BOUNDARIES.md` |
| **`docs/archive-inventory/`** | **Published JSON/MD index** of registries, on-disk manifests, code-archival and gdrive lists | Regenerate via `model-archival` script `generate-archive-inventory.py` (see `archive-inventory/README.md`) |
| **Repo `scripts/`** | **Cross-cutting generators** (e.g. archived models doc, archive inventory) | `scripts/generate-archived-models-doc.py`, etc. |

**Supermicro (physical host)** is documented at repo level in **[`SUPERMICRO.md`](SUPERMICRO.md)**; technical detail lives under **`ollama-hosting/`** and the dev-environment tree.

---

## 3. Operating requirements (cross-cutting)

1. **Root SSD:** No model payload data; code + venv + small logs only (see [`DISKS-AND-DISTRIBUTION.md`](DISKS-AND-DISTRIBUTION.md)).  
2. **D5:** Metadata, `run_state.json`, `STATUS.md`, archive index replication — **atomic writes** (tmp + rename) for state and reports.  
3. **Graceful stop:** Before reboot or disk maintenance on the archiver host, use **`model-archival/scripts/stop.sh`** and wait for a clean stop.  
4. **Registries:** `model-archival/config/registry.yaml` is the **master** HF model list; specialists, legacy, and final queues are documented in [`CONFIGURATION.md`](CONFIGURATION.md) and [`ARCHIVED-MODELS.md`](ARCHIVED-MODELS.md).  
5. **Ollama sync:** **Additive only** — no `rsync --delete` on archive destinations; completed weights only by default (`*partial*` excluded). See **`ollama-hosting/docs/SYNC-JOB.md`**.  
6. **Remote ops:** Prefer logging to **`docs/remote/REMOTE_ACTIVITY_LOG.<host>.md`** when work happens on a remote machine (see [`AGENTS.md`](AGENTS.md)).

---

## 4. Consolidated accomplishments (what the monorepo delivers)

These are the **capabilities** the tree implements, aligned with [`docs/README.md`](README.md) and extended for newer subprojects:

- **Resumable HF archiver** with per-drive caps, bandwidth-aware scheduling, auth-gated models, failed-model registry workflows, and final-queue artifacts (`final_downloads.yaml`, `final_pending_registry.yaml`, `MODEL-ARCHIVE-FINAL-STATUS.md`).  
- **Tiered coverage:** frontier weights, uncensored/abliterated lines, GGUF, specialists (math, code, embeddings, vision, etc.).  
- **Fingerprints + code archival + tooling mirrors** so integrity and surrounding software are preserved, not only tensors.  
- **GDrive and gh-archival** paths for off-site and GitHub-owned-repo preservation.  
- **Ollama hosting + archival sync** for the Supermicro rig, including rotation across VM disks and operator docs for safe supermicro prune.  
- **Published inventories** under `docs/archive-inventory/` and the large **ARCHIVED-MODELS** / **FINAL-STATUS** documents for human and machine navigation.

---

## 5. Agent bootstrap (read order)

1. [`AGENTS.md`](AGENTS.md) — monorepo entry, compaction rules.  
2. [`PROJECTS.md`](PROJECTS.md) — per-directory entry points.  
3. Task-specific: subproject `AGENTS.md` or `README.md` (e.g. `ollama-hosting/README.md`, `gdrive-archival/AGENTS.md`).  
4. Deep archiver context: [`model-archival/docs/AI_CONTEXT.md`](../model-archival/docs/AI_CONTEXT.md).  
5. This file when the task spans **multiple** directories or needs **requirements** without opening every README.

---

## 6. Key repository documents (index)

| Document | Use |
|----------|-----|
| [`README.md`](../README.md) | Repo root layout and quick commands |
| [`docs/README.md`](README.md) | Mission, objectives, doc index |
| [`PROJECTS.md`](PROJECTS.md) | Subproject map |
| [`SUPERMICRO.md`](SUPERMICRO.md) | Supermicro role and pointers |
| [`CONFIGURATION.md`](CONFIGURATION.md) | Registry and policy |
| [`ARCHIVED-MODELS.md`](ARCHIVED-MODELS.md) | Full model inventory |
| [`MODEL-ARCHIVE-FINAL-STATUS.md`](MODEL-ARCHIVE-FINAL-STATUS.md) | Union registry + run_state snapshot |
| [`GDRIVE-UPLOAD-RUNBOOK.md`](GDRIVE-UPLOAD-RUNBOOK.md) | Drive upload operations |
| [`DERIVED-REQUIREMENTS-ANALYSIS.md`](DERIVED-REQUIREMENTS-ANALYSIS.md) | Requirements derived from structure + transcripts |

---

## 7. Prompt snippet (paste for new sessions)

Use or adapt:

> You are working in the **model-archival** monorepo: HF weight archiver (`model-archival/`), fingerprints, code-archival, gdrive-archival, gh-archival, ollama-hosting (Supermicro Ollama + VM rsync archive), integrity_tools, full-stack, and published docs under `docs/`. Respect drive rules: no model data on root SSD; D5 for state/reports; graceful `stop.sh` before reboot. For multi-subsystem tasks, read `docs/PROJECT-PROMPT-AND-REQUIREMENTS.md` and `docs/PROJECTS.md` first, then the relevant `AGENTS.md`. Ollama sync is additive-only; supermicro prune only after VM verification. Prefer `docs/AGENT_TRANSCRIPT_SUMMARY.md` over raw transcripts.

---

_Last updated: 2026-04-04 — aligns with `ollama-hosting/` and expanded monorepo layout._
