# Projects — Summary by Directory

Each sub-project lives in its own directory. This document gives a coherent
per-project map: purpose, entry points, authoritative files, and outputs.

---

## model-archival/ — Model weight downloader (archiver)

**Purpose:** Unattended, resumable, cryptographically verified offline archival of open-source LLM/LRM weights from Hugging Face onto a fleet of physical drives. Downloads raw BF16/FP16 weights, quantized GGUF, and uncensored variants; verifies SHA-256; produces manifests and provenance descriptors.

**Entry points:**

- `bash run.sh --all` — full run (default). Use inside `screen` for long runs.
- `bash run.sh --dry-run` — simulate pipeline, no downloads.
- `bash run.sh --priority-only 1` — token-free models only.
- `bash run.sh --tier A` — single tier.
- `bash stop.sh` — graceful shutdown (always use before reboot).
- `uv run archiver download|verify|status|list|drives|tokens|pin|report` — CLI.

**Authoritative files:**

- `model-archival/config/registry.yaml` — master model list (tiers, drive, priority, licence, `requires_auth`).
- `model-archival/config/drives.yaml` — drive mount points and roles.
- `/mnt/models/d5/run_state.json` — per-model download state (source of truth).
- `/mnt/models/d5/STATUS.md` — live dashboard (refreshed ~60s).
- `/mnt/models/d5/archive/` — replicated metadata archive across drives.

**Output:** Model weights and manifests live on D1, D2, D3 per drive assignment in the registry. State, logs, and STATUS live on D5. In-progress downloads use `D1/.tmp/` only.

**Docs:** `model-archival/docs/` — **[`AI_CONTEXT.md`](../model-archival/docs/AI_CONTEXT.md)** (compact agent map), REQUIREMENTS.md, DEPLOYMENT.md, ARCHITECTURE.md, OPERATIONS.md, HF-TOKEN-GUIDE.md, PROJECT_PROMPT.md. **`model-archival/AGENTS.md`** — pointer for AI tools. **Agent session changelog (use instead of Cursor transcripts):** [`AGENT_TRANSCRIPT_SUMMARY.md`](AGENT_TRANSCRIPT_SUMMARY.md). Repository-level model inventory: [ARCHIVED-MODELS.md](ARCHIVED-MODELS.md).

---

## fingerprints/ — Checksum crawler

**Purpose:** Lightweight SHA-256 fingerprint harvester for open-source LLM releases on Hugging Face. **No weights are downloaded.** Only LFS pointer files are fetched; these contain the authoritative SHA-256 for every weight shard. The result is an audit trail and integrity reference so any copy of a model can be verified against the original HF checksums.

**Entry points:**

- `bash run.sh` — crawl all models in config (resumable).
- `bash run.sh --output /mnt/models/d1` — custom output root.
- `bash run.sh --importance critical --tier A` — subset.
- `fingerprints status` — progress.
- `fingerprints show <model-id>` — inspect one model.
- `fingerprints verify <model-id> <path>` — verify a local file against stored fingerprints.

**Authoritative files:**

- `fingerprints/config/registry.yaml` — models to fingerprint (families, tiers, importance).
- `fingerprints/scripts/build_registry.py` — regenerate registry from leaderboard data.
- `fingerprints/scripts/snapshot_leaderboard.py` — archive Open LLM Leaderboard snapshots.

**Output:** By default, `model-checksums/` is created under the given output root (default `/mnt/models/d1`), so full path is `/mnt/models/d1/model-checksums/`. Contains `index.jsonl`, per-repo `fingerprint.json` / `fingerprint.md`, and `commits/<sha>.json`. Leaderboard snapshots go under `model-checksums/leaderboard-snapshots/`.

**Agents:** `fingerprints/AGENTS.md`

---

## code-archival/ — Source code archiver

**Purpose:** Snapshots the latest release tarballs and shallow git clones of critical open-source AI projects (inference engines, UIs, training tools, agents, quantization, evaluation) so they survive regulatory or maintainer takedowns.

**Entry points:**

- `bash archive.sh` — archive all projects in registry.
- `bash archive.sh --category inference` — one category.
- `bash archive.sh --risk high` — high-risk projects only.

**Authoritative files:**

- `code-archival/registry.yaml` — ~150 projects across categories (inference, training, agents, quantization, etc.) with risk levels (critical, high, medium, low).
- `code-archival/.secrets` — `GITHUB_TOKEN` (git-ignored).

**Output:** `/mnt/models/d1/code-archival/` (or as configured).

**Agents:** `code-archival/AGENTS.md`

---

## gdrive-archival/ — Cloud backup

**Purpose:** Upload selected model trees to Google Drive via rclone. Default workflow is **registry-driven** (`gdrive-registry.yaml` + `upload_registry.py`) with upload-only semantics. Optional staging mode can be used when explicitly curating per-dir uploads.

**Authoritative files:**

- `gdrive-archival/gdrive-registry.yaml` — upload roots (relative to `/mnt/models`) → `models/<root>/...` on Drive.
- `gdrive-archival/upload_registry.py` — registry uploader (local verify + `rclone copy --checksum`, optional `rclone check`).
- `gdrive-archival/config.yaml` — `models_mount`, `archiver_root`, `gdrive.*` and remote-verify toggles.
- `gdrive-archival/run-registry-upload.sh` — wrapper exporting `RCLONE_CONFIG` then running the uploader.

**Output:** Writes under the configured Drive folder (see `config.yaml`; folder ID must match `rclone.conf` if `root_folder_id` is set).

Operational note: registry uploads (`backup-registry`) are the default automation
path; staging uploads (`backup-staging`) are used when curation happens through
explicit staging directories.

**Agents:** `gdrive-archival/AGENTS.md`

---

## Tooling mirror (from local registry)

Tooling projects listed under `tooling:` in `model-archival/config/registry.yaml` (Continue, Aider, Tabby, OpenHands, vLLM, llama.cpp, Ollama, etc.) are mirrored as **bare git repos** on D5 by a separate script:

- **Script:** `model-archival/scripts/archive-tooling.sh`
- **Output:** `/mnt/models/d5/tooling-archive/<id>.git`

This keeps a copy of the code for IDE assistants, agent platforms, and serving backends on the metadata drive without duplicating weight data.

---

## full-stack/ — Full-stack archive utilities

**Purpose:** End-to-end archive utilities and helpers (see `full-stack/README.md`).

**Agents:** `full-stack/AGENTS.md`

---

## integrity_tools/ — Integrity helpers

**Purpose:** Misc integrity/verification tooling.

**Agents:** `integrity_tools/AGENTS.md`
