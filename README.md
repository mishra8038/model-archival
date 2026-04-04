# model-archival — monorepo

This Git repository is a **monorepo**: one version-controlled tree that contains **several related projects**, each in its own top-level directory. They share a common mission—**preserving open AI artifacts**—but have separate codebases, dependencies, and entry points. You work inside **one subproject folder at a time** (for example `cd model-archival` or `cd fingerprints`), unless a task spans multiple areas.

## Intent

**Insurance-first archival:** keep model weights, integrity metadata, source/tooling snapshots, and selected cloud mirrors so they survive deletion, licensing changes, or takedowns. The monorepo groups everything an operator needs: download and verify HF weights, fingerprint without pulling tensors, snapshot GitHub projects, push to Drive, archive owned GitHub repos as tarballs, and operate **Ollama** on a local GPU host with an **additive** sync to the archival disk server.

## Objectives

- **Coverage:** Frontier and specialist models (registry-driven), plus uncensored and quantized lines where policy allows.
- **Integrity:** SHA-256 verification and manifests for weights; LFS fingerprints where full downloads are optional.
- **Resumability:** Long-running jobs are safe to stop and resume (archiver, crawls, uploads).
- **Clarity:** Repository-level docs under [`docs/`](docs/) describe drives, configuration, and how subprojects fit together; each subproject has its own `README.md` and often `AGENTS.md` for automation-friendly context.
- **Safe storage:** Model payloads live on the HDD pool, not the root SSD; control-plane state uses atomic writes where applicable (see [`docs/DISKS-AND-DISTRIBUTION.md`](docs/DISKS-AND-DISTRIBUTION.md)).

**Single-page orientation:** [`docs/PROJECT-PROMPT-AND-REQUIREMENTS.md`](docs/PROJECT-PROMPT-AND-REQUIREMENTS.md) · **Per-folder map:** [`docs/PROJECTS.md`](docs/PROJECTS.md) · **Agents:** [`docs/AGENTS.md`](docs/AGENTS.md)

## Repository layout (subprojects)

| Folder | Purpose | Status |
| ------ | ------- | ------ |
| [`model-archival/`](model-archival/) | **Weight archiver** — resumable Hugging Face downloader with SHA-256 verification and live status/reporting | Active |
| [`fingerprints/`](fingerprints/) | **Checksum crawler** — records authoritative LFS SHA-256 fingerprints without downloading model weights | Active |
| [`code-archival/`](code-archival/) | **Source archiver** — snapshots important AI tooling repos/releases from GitHub | Active |
| [`gdrive-archival/`](gdrive-archival/) | **Cloud backup** — uploads selected archived trees to Google Drive via rclone | Active |
| [`gh-archival/`](gh-archival/) | **GitHub tarball archiver** — owned repos → `git archive` + manifest + optional rclone | Active |
| [`ollama-hosting/`](ollama-hosting/) | **Supermicro Ollama + VM sync** — rig scripts, `ollama-sync.sh`, rotation/inventory docs | Active |
| [`full-stack/`](full-stack/) | **Full-stack archive utilities** — helpers and tooling (see `full-stack/README.md`) | Active |
| [`integrity_tools/`](integrity_tools/) | **Integrity helpers** — miscellaneous verification utilities | Active |
| [`multidisk-downloader/`](multidisk-downloader/) | **Design docs** — selector / downloader / uploader boundaries (documentation-first) | Docs |
| [`docs/`](docs/) | **Cross-project documentation** — mission, configuration, inventories, runbooks (not a Python package) | Active |

Top-level [`scripts/`](scripts/) holds **cross-cutting generators** (e.g. archived-models and archive-inventory docs) used by more than one subproject.

---

## model-archival/ — Model weight archiver

Self-contained Python package (`uv`). All code, config, docs, scripts, and
deployment tools live under `model-archival/`.

```bash
cd model-archival
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

## gh-archival/ — Owned GitHub repos → tarballs

```bash
cd gh-archival
uv sync
uv run gh-archival check
uv run gh-archival run    # optional: set GH_ARCHIVAL_RCLONE_REMOTE for upload
```

See [`gh-archival/README.md`](gh-archival/README.md).

---

## ollama-hosting/ — Supermicro Ollama + archival sync

```bash
cd ollama-hosting
uv sync
./scripts/ollama-sync.sh   # Supermicro ~/.ollama → archival VM (see docs/SYNC-JOB.md)
```

Rig mirror and pull scripts: `ollama-hosting/supermicro-rig/`. **Repo overview:** [docs/SUPERMICRO.md](docs/SUPERMICRO.md).

---

## Documentation

The central `docs/` folder is the repository-level source of truth for mission,
architecture by subsystem, configuration policy, and storage layout:

- [docs/README.md](docs/README.md) — Overview, mission, objectives, doc index
- [docs/PROJECT-PROMPT-AND-REQUIREMENTS.md](docs/PROJECT-PROMPT-AND-REQUIREMENTS.md) — **Consolidated** prompt, subprojects, cross-cutting requirements
- [docs/SUPERMICRO.md](docs/SUPERMICRO.md) — Supermicro GPU host role and pointers
- [docs/ARCHIVED-MODELS.md](docs/ARCHIVED-MODELS.md) — Complete model inventory (master + legacy + specialists; uncensored and specialty sections)
- [docs/PROJECTS.md](docs/PROJECTS.md) — Summary of each project directory
- [docs/CONFIGURATION.md](docs/CONFIGURATION.md) — Registry, drives, tiers, priorities
- [docs/ARTIFACTS.md](docs/ARTIFACTS.md) — What we archive (weights, checksums, code, tooling)
- [docs/DISKS-AND-DISTRIBUTION.md](docs/DISKS-AND-DISTRIBUTION.md) — Disk layout and artifact distribution per drive

---

## Quick status

```bash
# Model weights
cd model-archival && uv run archiver status

# Fingerprint crawl
cd fingerprints && uv run fingerprints status

# Code archival
ls /mnt/models/d1/code-archival/

# GDrive upload status (if configured)
cd gdrive-archival && python3 backup.py upload-registry-status
```
