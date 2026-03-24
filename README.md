# model-archival

Insurance-first archival of open-source AI artifacts so model weights, checksums,
and critical tooling code survive deletion, restriction, or takedown.

## Repository layout

| Folder | Purpose | Status |
| ------ | ------- | ------ |
| [`model-archival/`](model-archival/) | **Weight archiver** — resumable Hugging Face downloader with SHA-256 verification and live status/reporting | Active |
| [`fingerprints/`](fingerprints/) | **Checksum crawler** — records authoritative LFS SHA-256 fingerprints without downloading model weights | Active |
| [`code-archival/`](code-archival/) | **Source archiver** — snapshots important AI tooling repos/releases from GitHub | Active |
| [`gdrive-archival/`](gdrive-archival/) | **Cloud backup** — uploads selected archived trees to Google Drive via rclone | Active |

---

## model-archival/ — Model weight archiver

Self-contained Python package (`uv`). All code, config, docs, scripts, and
deployment tools live under `model-archival/`.

```bash
cd local
uv sync
bash run.sh --dry-run       # preview what will be downloaded
bash run.sh --all           # full run (requires HF_TOKEN for gated models)
```

Authoritative files:

- `model-archival/config/registry.yaml` — master model list (tier, drive, priority)
- `model-archival/config/drives.yaml` — drive mount points and capacity
- `/mnt/models/d5/run_state.json` — per-model download state
- `/mnt/models/d5/STATUS.md` — live run dashboard

See [`model-archival/README.md`](model-archival/README.md) for full documentation.

---

## fingerprints/ — Checksum crawler

Records SHA-256 LFS fingerprints of every important model release on
HuggingFace — without downloading the weights. Provides a lightweight
audit trail and integrity reference.

```bash
cd fingerprints
uv sync
bash run.sh                 # crawl all models in config/registry.yaml
```

Key files:

- `fingerprints/config/registry.yaml` — models to fingerprint
- `fingerprints/scripts/build_registry.py` — regenerates registry from leaderboard data
- `fingerprints/scripts/snapshot_leaderboard.py` — archives Open LLM Leaderboard snapshot

Output lands on `/mnt/models/d1/model-checksums/`.

See [`fingerprints/README.md`](fingerprints/README.md) for full documentation.

---

## code-archival/ — Source code archiver

Archives the latest release tarballs + shallow git clones of critical
open-source AI projects (inference engines, UIs, training tools, agents,
quantization tools, etc.) so they survive potential regulatory takedowns.

```bash
cd code-archival
bash archive.sh             # archive all projects in registry.yaml
bash archive.sh --category inference   # archive one category only
bash archive.sh --risk high            # archive high-risk projects only
```

Key files:

- `code-archival/registry.yaml` — ~150 projects across 25 categories
- `code-archival/.secrets` — `GITHUB_TOKEN` (git-ignored)

Output lands on `/mnt/models/d1/code-archival/`.

---

## gdrive-archival/ — Cloud backup

Uploads curated local archive trees to Google Drive with resumable,
checksum-based rclone sync.

Primary modes:

- **Registry mode** (`backup-registry`) — uses `gdrive-archival/gdrive-registry.yaml`.
- **Staging mode** (`backup-staging`) — uploads immediate subdirectories from
  configured staging roots (default D3/D5 staging dirs).

```bash
cd gdrive-archival
python3 backup.py list-registry
python3 backup.py backup-registry --dry-run
python3 backup.py backup-registry
```

See [`gdrive-archival/README.md`](gdrive-archival/README.md) for operations and
service/screen workflow.

---

## Documentation

The central `docs/` folder is the repository-level source of truth for mission,
architecture by subsystem, configuration policy, and storage layout:

- [docs/README.md](docs/README.md) — Overview, mission, objectives, doc index
- [docs/ARCHIVED-MODELS.md](docs/ARCHIVED-MODELS.md) — Complete model inventory (master + legacy + specialists; uncensored and specialty sections)
- [docs/PROJECTS.md](docs/PROJECTS.md) — Summary of each project (local, fingerprints, code-archival, gdrive-archival)
- [docs/CONFIGURATION.md](docs/CONFIGURATION.md) — Registry, drives, tiers, priorities
- [docs/ARTIFACTS.md](docs/ARTIFACTS.md) — What we archive (weights, checksums, code, tooling)
- [docs/DISKS-AND-DISTRIBUTION.md](docs/DISKS-AND-DISTRIBUTION.md) — Disk layout and artifact distribution per drive

---

## Quick status

```bash
# Model weights
cd local && uv run archiver status

# Fingerprint crawl
cd fingerprints && uv run fingerprints status

# Code archival
ls /mnt/models/d1/code-archival/

# GDrive upload status (if configured)
cd gdrive-archival && python3 backup.py upload-registry-status
```
