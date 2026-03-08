# model-archival

Insurance-first archival of open-source AI artifacts — weights, checksums, and
source code — in case models or projects disappear from the internet.

## Repository layout

| Folder | Purpose | Status |
|--------|---------|--------|
| [`local/`](local/) | **Weight downloader** — Python archiver that pulls full model weights from HuggingFace to local HDDs via `aria2c` | Active |
| [`fingerprints/`](fingerprints/) | **Checksum crawler** — lightweight tool that records SHA-256 LFS fingerprints + metadata for every major model release without downloading weights | Active |
| [`code-archival/`](code-archival/) | **Source archiver** — snapshots critical open-source AI project releases (inference engines, training tools, UIs, agents, etc.) from GitHub | Active |

---

## local/ — Model weight downloader

Self-contained Python package (`uv`). All code, config, docs, scripts, and
deployment tools live under `local/`.

```bash
cd local
uv sync
bash run.sh --dry-run       # preview what will be downloaded
bash run.sh --all           # full run (requires HF_TOKEN for gated models)
```

Key files:
- `local/config/registry.yaml` — master model list (tier, drive, priority)
- `local/config/drives.yaml` — drive mount points and capacity
- `/mnt/models/d5/run_state.json` — per-model download state
- `/mnt/models/d5/MANIFEST.md` — human-readable status table

See [`local/README.md`](local/README.md) for full documentation.

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

Output lands on `/mnt/models/d1/model-fingerprints-data/`.

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

## Quick status

```bash
# Model weights
cd local && uv run archiver status

# Fingerprint crawl
cd fingerprints && uv run fingerprints status

# Code archival
ls /mnt/models/d1/code-archival/
```
