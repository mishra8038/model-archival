---
description: Agent bootstrap for fingerprints (checksum / fingerprint crawler; no weights download).
alwaysApply: true
---

# fingerprints — agents

## Purpose

Harvest and store upstream integrity metadata (checksums/fingerprints) for models without downloading full weights.

## Start here

- Repo map: `docs/PROJECTS.md` (root)
- This subproject: `fingerprints/README.md`

## Key paths

- `fingerprints/config/registry.yaml` — models to fingerprint
- `fingerprints/run.sh` — typical entrypoint

## Safety

- This subproject should **not** download full model weights; it collects metadata/pointers/checksums.

