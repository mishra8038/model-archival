# Archived models documentation

- Added `docs/ARCHIVED-MODELS.md`: full master registry list (unique ids), legacy + specialist registries, tier table, **uncensored/abliterated** vs **tier-D Nemotron** split, **specialty** breakdown (E/F/G + `registry-specialists.yaml`).
- Added `scripts/generate-archived-models-doc.py` to regenerate from YAML; linked from `docs/README.md`, `docs/ARTIFACTS.md`, `docs/PROJECTS.md`, root `README.md`.
- Removed duplicate `open-r1/OlympicCoder-32B` from `registry.yaml` (kept tier B / d2 / pinned `commit_sha`, merged notes).
- Status table: **path on disk** (`models_mount` + archiver layout), optional **Download** (`run_state.json`) and **GDrive** (`registry-upload-state.json`) columns when those files exist; **Dir** + **manifest.json** probed on the host running the generator. Env: `ARCHIVER_RUN_STATE`, `ARCHIVER_MODELS_MOUNT`.
