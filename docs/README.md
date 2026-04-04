# Model Archival — Documentation

This folder describes the **model-archival** repository as one system: mission,
sub-project roles, configuration policy, archived artifacts, and physical disk
distribution.

**AI agents:** Curated session outcomes (use instead of raw Cursor transcripts): [`AGENT_TRANSCRIPT_SUMMARY.md`](AGENT_TRANSCRIPT_SUMMARY.md). Compact archiver map: [`model-archival/docs/AI_CONTEXT.md`](../model-archival/docs/AI_CONTEXT.md).

---

## Mission and objectives

**Mission:** Insurance-first archival of open-source AI artifacts so that models and tooling survive deletion, restriction, or regulatory takedown. We preserve weights, checksums, and source code on local storage with cryptographic verification and resumable, unattended operation.

**Objectives:**

- **Weights:** Download full open-source LLM/LRM weights from Hugging Face (raw BF16/FP16 and selected GGUF) to a fleet of local HDDs, with SHA-256 verification and structured manifests.
- **Checksums:** Record SHA-256 LFS fingerprints for every major model release without downloading weights, providing a lightweight audit trail and integrity reference.
- **Source code:** Snapshot critical open-source AI projects (inference engines, training tools, agents, UIs) from GitHub so they survive potential takedowns.
- **Tooling:** Mirror IDE assistants, agent frameworks, and serving backends listed in the registry as bare git repos on the metadata drive.
- **Safety:** Never write model data to the root SSD; use atomic writes for state and reports; always stop gracefully before reboot to avoid filesystem corruption.

---

## Operating model (canonical)

Think of the repository as a **multi-artifact preservation system** (not only HF downloads):

1. **`model-archival/`** downloads and verifies model weight trees onto D1–D3, while D5
   holds state/reporting control-plane files. **AI/agent bootstrap:** [`model-archival/docs/AI_CONTEXT.md`](../model-archival/docs/AI_CONTEXT.md) · [`model-archival/AGENTS.md`](../model-archival/AGENTS.md).
2. **`fingerprints/`** records upstream HF checksum metadata for independent
   verification without storing weights.
3. **`code-archival/`** snapshots surrounding OSS tooling (inference/training/UI/agents).
4. **`gdrive-archival/`** uploads selected local archive trees to Google Drive.
5. **`gh-archival/`** snapshots **GitHub repos you own** (tarballs + manifest + optional rclone).
6. **`ollama-hosting/`** holds **Supermicro Ollama** rig material (pull queues, scripts, systemd) and **rsync archival sync** of `~/.ollama` to the disk VM (rotation, inventory, prune planning). **Operator overview:** [`SUPERMICRO.md`](SUPERMICRO.md).

**Agents:** Monorepo entrypoint [`AGENTS.md`](../AGENTS.md). **Cross-project prompt + requirements:** [`PROJECT-PROMPT-AND-REQUIREMENTS.md`](PROJECT-PROMPT-AND-REQUIREMENTS.md). Per-subproject bootstraps: `gdrive-archival/AGENTS.md`, `fingerprints/AGENTS.md`, `code-archival/AGENTS.md`, `full-stack/AGENTS.md`, `integrity_tools/AGENTS.md`, `ollama-hosting/README.md`.

`model-archival/config/registry.yaml` is the canonical model selection source; related
registries in other subprojects mirror that intent for their own artifact types.

---

## What we have accomplished so far

- **Frontier-weight archival:** Downloaded and verified multiple generations of flagship open models (DeepSeek, Qwen 2.5/3, Llama 3.1/3.3, Gemma 3, Phi-4, Devstral, Dolphin, Tulu, Nemotron, Chocolatine/Rombo, etc.) across BF16/FP16 checkpoints and key GGUF quants. These are pinned in `model-archival/config/registry.yaml` via `commit_sha` and tracked in `/mnt/models/d5/run_state.json`.
- **Uncensored / abliterated variants:** Archived a curated set of uncensored/abliterated instruction models (huihui-ai, mlabonne, CombinHorizon, FINGU-AI, failspy and others) for research and alignment studies, clearly tiered and segregated on the appropriate drives.
- **Research and specialist models:** Included reasoning, reward, vision, math, coding, and embedding models (e.g. QwQ, OlympicCoder, Skywork reward, bge/e5/gte-Qwen2, VL variants, diffusion-style code models like CoDA and DiffuCoder) with space-aware placement, primarily on D3.
- **Resilient downloader:** Built a resumable `aria2c`-backed downloader with per-drive concurrency caps, EWMA-based throughput accounting, and robust error handling (auth failures, expired URLs, partial files, DNS errors) that records every outcome in `run_state.json`.
- **Status and reporting:** Implemented a single authoritative `STATUS.md` dashboard plus incremental Markdown run reports, both driven from scheduler statistics, so we can see at a glance which models are pending, in progress, complete, failed, or skipped and why.
- **Checksum and code archival:** Brought up the fingerprints crawler and source-code archiver so that for many models we now have both SHA-256 fingerprints and snapshots of surrounding tooling (inference engines, trainers, agent frameworks) archived alongside weights.
- **Cloud backup path:** GDrive uploads via rclone; default workflow uses **staging dirs** on D3/D5 (`gdrive-archival/README.md`), with optional legacy registry/extra_paths modes.
- **GitHub-owned-repo snapshots:** `gh-archival/` produces versioned tarballs and can push runs to Google Drive via rclone.
- **Ollama on Supermicro + VM archive:** `ollama-hosting/` consolidates pull scripts, service layout, **additive** rsync to the archival VM (disk rotation), inventory maps, and safe supermicro prune workflows (`docs/SUPERMICRO.md`, `ollama-hosting/docs/SYNC-JOB.md`).
- **Published archive index:** `docs/archive-inventory/` JSON/MD snapshots for GitHub-facing navigation (regenerate via `generate-archive-inventory.py`; see `archive-inventory/README.md`).
- **Final-queue artifacts:** `MODEL-ARCHIVE-FINAL-STATUS.md`, `final_downloads.yaml`, and `final_pending_registry.yaml` unify registry + run_state views for operational closure.

---

## End-state vision for this project

- **Frontier snapshot coverage:** Maintain a continuously updated, space-aware snapshot of the open frontier: all major base models, key instruct/abliterated variants, and practical GGUF quants across code, chat, reasoning, math, and vision — enough to recreate or study today’s systems even if they vanish from the web.
- **Cryptographically provable integrity:** Every archived artifact (weights, LFS blobs, source tarballs, configs) is covered by SHA-256 manifests and global indices, with repeatable verification tooling so we can prove what we have and detect any silent corruption.
- **Operationally boring downloads:** The archiver should be something we can leave running unattended: resumable, idempotent, and scheduler-driven, with dynamic priority overrides, robust handling of gated/404’d repos, and clear logs that explain exactly what happened.
- **Rich historical record:** Beyond raw bits, the project aims to preserve the surrounding ecosystem: leaderboards, registries, and key open-source tooling, plus a human-readable Markdown history of runs and configuration choices that explains why certain models were kept, skipped, or moved to legacy.
- **Safe, space-aware storage:** Model data permanently lives on the HDD pool (D1–D3) with explicit tiering and per-drive policies, while D5 remains the canonical home for metadata, reports, registries, and run state — all written atomically so a crash or reboot never corrupts the control plane.

---

## Documentation index

| Document | Contents |
| -------- | -------- |
| [PROJECT-PROMPT-AND-REQUIREMENTS.md](PROJECT-PROMPT-AND-REQUIREMENTS.md) | **Consolidated** mission, subprojects, cross-cutting requirements, accomplishments, agent read order, pasteable prompt. |
| [SUPERMICRO.md](SUPERMICRO.md) | Supermicro GPU host role, network anchors, checklist; points to `ollama-hosting/`. |
| [PROJECTS.md](PROJECTS.md) | Summary of each project in its directory (model-archival, fingerprints, code-archival, gdrive-archival, gh-archival, ollama-hosting, etc.). |
| [DERIVED-REQUIREMENTS-ANALYSIS.md](DERIVED-REQUIREMENTS-ANALYSIS.md) | Requirements derived from monorepo structure, docs, and transcript sampling. |
| [ARCHIVED-MODELS.md](ARCHIVED-MODELS.md) | Full inventory + **paths on disk**, optional **download** (`run_state.json`) and **GDrive** (`registry-upload-state.json`) columns when those files exist. Regenerate: `uv run --directory model-archival python3 ../scripts/generate-archived-models-doc.py` (optional `ARCHIVER_RUN_STATE`, `ARCHIVER_MODELS_MOUNT`). |
| [CONFIGURATION.md](CONFIGURATION.md) | Decided configuration: registry layout, drives, tiers, priorities, tooling list. |
| [ARTIFACTS.md](ARTIFACTS.md) | What we archive: model weights (tiers A–G), checksums, code snapshots, tooling mirrors. |
| [DISKS-AND-DISTRIBUTION.md](DISKS-AND-DISTRIBUTION.md) | Physical disk layout, roles, and distribution of artifacts per drive. |
| [CHAT-ARCHIVE.md](CHAT-ARCHIVE.md) | Index of Cursor agent chat transcripts (date, title, UUID) and how to refresh it. |
| [GRAPHCORE-2.4-COMPATIBILITY.md](GRAPHCORE-2.4-COMPATIBILITY.md) | Practical compatibility matrix and action plan for Graphcore Poplar 2.4.0 on C2/Ubuntu 18.04. |
| [GRAPHCORE-2.4-SOURCES-BACKUP.md](GRAPHCORE-2.4-SOURCES-BACKUP.md) | Preserved source snapshot/extracts from Graphcore 2.4.0 release notes and Docker docs. |
| [GRAPHCORE-2.4-INSTALL-PLAYBOOK.md](GRAPHCORE-2.4-INSTALL-PLAYBOOK.md) | Command-driven runbook for side-by-side installation, validation, and rollback of Graphcore 2.4.x. |

Start with:

- **Whole-repo orientation:** [PROJECT-PROMPT-AND-REQUIREMENTS.md](PROJECT-PROMPT-AND-REQUIREMENTS.md) then `README.md` (repo root) and [PROJECTS.md](PROJECTS.md)
- **Supermicro / Ollama:** [SUPERMICRO.md](SUPERMICRO.md) and [`../ollama-hosting/README.md`](../ollama-hosting/README.md)
- **Policy and constraints:** [CONFIGURATION.md](CONFIGURATION.md), [DISKS-AND-DISTRIBUTION.md](DISKS-AND-DISTRIBUTION.md)
- **Artifact scope:** [ARTIFACTS.md](ARTIFACTS.md)

---

## Repository layout (high level)

| Directory | Purpose |
| --------- | ------- |
| `model-archival/` | **Weight downloader** — Python archiver; pulls full model weights from Hugging Face to local HDDs via aria2c. |
| `fingerprints/` | **Checksum crawler** — records SHA-256 LFS fingerprints and metadata for major model releases without downloading weights. |
| `code-archival/` | **Source archiver** — snapshots open-source AI project releases (inference, training, agents, UIs) from GitHub. |
| `gdrive-archival/` | **Cloud backup** — staging-folder uploads (and optional configs / registry-driven lists) to Google Drive via rclone. |
| `gh-archival/` | **GitHub tarball archiver** — owned repos → `git archive` + manifest + optional rclone upload. |
| `ollama-hosting/` | **Supermicro Ollama + VM sync** — rig mirror, `ollama-sync.sh`, rotation state, inventory, prune planner. |
| `multidisk-downloader/` | **Design docs** — selector / downloader / uploader boundary contracts (documentation-first). |

For per-project details, entry points, and file locations, see [PROJECTS.md](PROJECTS.md).
