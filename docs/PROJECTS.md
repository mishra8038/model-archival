# Projects — Summary by Directory

Each sub-project lives in its own directory. This document summarizes each one: purpose, entry points, key files, and where outputs go.

---

## local/ — Model weight downloader (archiver)

**Purpose:** Unattended, resumable, cryptographically verified offline archival of open-source LLM/LRM weights from Hugging Face onto a fleet of physical drives. Downloads raw BF16/FP16 weights, quantized GGUF, and uncensored variants; verifies SHA-256; produces manifests and provenance descriptors.

**Entry points:**

- `bash run.sh --all` — full run (default). Use inside `screen` for long runs.
- `bash run.sh --dry-run` — simulate pipeline, no downloads.
- `bash run.sh --priority-only 1` — token-free models only.
- `bash run.sh --tier A` — single tier.
- `bash stop.sh` — graceful shutdown (always use before reboot).
- `uv run archiver download|verify|status|list|drives|tokens|pin|report` — CLI.

**Key files:**

- `local/config/registry.yaml` — master model list (tiers, drive, priority, licence, `requires_auth`).
- `local/config/drives.yaml` — drive mount points and roles.
- `/mnt/models/d5/run_state.json` — per-model download state (source of truth).
- `/mnt/models/d5/STATUS.md` — live dashboard (refreshed ~60s).
- `/mnt/models/d5/archive/` — replicated metadata archive across drives.

**Output:** Model weights and manifests live on D1, D2, D3 per drive assignment in the registry. State, logs, and STATUS live on D5. In-progress downloads use `D1/.tmp/` only.

**Docs:** `local/docs/` — REQUIREMENTS.md, DEPLOYMENT.md, ARCHITECTURE.md, OPERATIONS.md, HF-TOKEN-GUIDE.md.

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

**Key files:**

- `fingerprints/config/registry.yaml` — models to fingerprint (families, tiers, importance).
- `fingerprints/scripts/build_registry.py` — regenerate registry from leaderboard data.
- `fingerprints/scripts/snapshot_leaderboard.py` — archive Open LLM Leaderboard snapshots.

**Output:** By default, `model-checksums/` is created under the given output root (default `/mnt/models/d1`), so full path is `/mnt/models/d1/model-checksums/`. Contains `index.jsonl`, per-repo `fingerprint.json` / `fingerprint.md`, and `commits/<sha>.json`. Leaderboard snapshots go under `model-checksums/leaderboard-snapshots/`.

---

## code-archival/ — Source code archiver

**Purpose:** Snapshots the latest release tarballs and shallow git clones of critical open-source AI projects (inference engines, UIs, training tools, agents, quantization, evaluation) so they survive regulatory or maintainer takedowns.

**Entry points:**

- `bash archive.sh` — archive all projects in registry.
- `bash archive.sh --category inference` — one category.
- `bash archive.sh --risk high` — high-risk projects only.

**Key files:**

- `code-archival/registry.yaml` — ~150 projects across categories (inference, training, agents, quantization, etc.) with risk levels (critical, high, medium, low).
- `code-archival/.secrets` — `GITHUB_TOKEN` (git-ignored).

**Output:** `/mnt/models/d1/code-archival/` (or as configured).

---

## gdrive-archival/ — Cloud backup

**Purpose:** Backs up essential configs, metadata, and a chosen subset of model identifiers to Google Drive via rclone. Complements local and fingerprints by providing an off-site copy of configuration and pointers, not full weights.

**Key files:**

- `gdrive-archival/config.yaml` — `archiver_root`, rclone remote, `extra_paths` (registry, drives, D5 archive/logs/run_state, fingerprints path, code-archives), and optional `model_ids_gguf` / `model_ids_full` for selective backup.
- `gdrive-archival/backup.py` — backup logic.

**Output:** Writes to the configured rclone remote (e.g. `gdrive:llm-survivor`) under the given base path.

---

## Tooling mirror (from local registry)

Tooling projects listed under `tooling:` in `local/config/registry.yaml` (Continue, Aider, Tabby, OpenHands, vLLM, llama.cpp, Ollama, etc.) are mirrored as **bare git repos** on D5 by a separate script:

- **Script:** `local/scripts/archive-tooling.sh`
- **Output:** `/mnt/models/d5/tooling-archive/<id>.git`

This keeps a copy of the code for IDE assistants, agent platforms, and serving backends on the metadata drive without duplicating weight data.
