# Model Archival — Documentation

This folder describes the **model-archival** repository: its mission, the sub-projects in each directory, the configuration we have decided upon, the artifacts we archive, and how they are distributed across the physical disks.

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

## What we have accomplished so far

- **Frontier-weight archival:** Downloaded and verified multiple generations of flagship open models (DeepSeek, Qwen 2.5/3, Llama 3.1/3.3, Gemma 3, Phi-4, Devstral, Dolphin, Tulu, Nemotron, Chocolatine/Rombo, etc.) across BF16/FP16 checkpoints and key GGUF quants. These are pinned in `local/config/registry.yaml` via `commit_sha` and tracked in `/mnt/models/d5/run_state.json`.
- **Uncensored / abliterated variants:** Archived a curated set of uncensored/abliterated instruction models (huihui-ai, mlabonne, CombinHorizon, FINGU-AI, failspy and others) for research and alignment studies, clearly tiered and segregated on the appropriate drives.
- **Research and specialist models:** Included reasoning, reward, vision, math, coding, and embedding models (e.g. QwQ, OlympicCoder, Skywork reward, bge/e5/gte-Qwen2, VL variants, diffusion-style code models like CoDA and DiffuCoder) with space-aware placement, primarily on D3.
- **Resilient downloader:** Built a resumable `aria2c`-backed downloader with per-drive concurrency caps, EWMA-based throughput accounting, and robust error handling (auth failures, expired URLs, partial files, DNS errors) that records every outcome in `run_state.json`.
- **Status and reporting:** Implemented a single authoritative `STATUS.md` dashboard plus incremental Markdown run reports, both driven from scheduler statistics, so we can see at a glance which models are pending, in progress, complete, failed, or skipped and why.
- **Checksum and code archival:** Brought up the fingerprints crawler and source-code archiver so that for many models we now have both SHA-256 fingerprints and snapshots of surrounding tooling (inference engines, trainers, agent frameworks) archived alongside weights.
- **Cloud backup path:** Added a gdrive archival toolchain that can verify per-model manifests and upload selected artifacts and configs to Google Drive, so the local archive can be mirrored off-site when desired.

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
|----------|----------|
| [PROJECTS.md](PROJECTS.md) | Summary of each project in its directory (local, fingerprints, code-archival, gdrive-archival). |
| [CONFIGURATION.md](CONFIGURATION.md) | Decided configuration: registry layout, drives, tiers, priorities, tooling list. |
| [ARTIFACTS.md](ARTIFACTS.md) | What we archive: model weights (tiers A–G), checksums, code snapshots, tooling mirrors. |
| [DISKS-AND-DISTRIBUTION.md](DISKS-AND-DISTRIBUTION.md) | Physical disk layout, roles, and distribution of artifacts per drive. |
| [CHAT-ARCHIVE.md](CHAT-ARCHIVE.md) | Index of Cursor agent chat transcripts (date, title, UUID) and how to refresh it. |

---

## Repository layout (high level)

| Directory | Purpose |
|-----------|---------|
| `local/` | **Weight downloader** — Python archiver; pulls full model weights from Hugging Face to local HDDs via aria2c. |
| `fingerprints/` | **Checksum crawler** — records SHA-256 LFS fingerprints and metadata for major model releases without downloading weights. |
| `code-archival/` | **Source archiver** — snapshots open-source AI project releases (inference, training, agents, UIs) from GitHub. |
| `gdrive-archival/` | **Cloud backup** — backs up key configs, metadata, and selected model IDs to Google Drive via rclone. |

For per-project details, entry points, and file locations, see [PROJECTS.md](PROJECTS.md).
