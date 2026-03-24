# 2026-03-24 docs coherence pass

## Scope

- Normalized project-wide docs for consistent subsystem framing and terminology.
- Updated root `README.md` plus `docs/README.md`, `docs/PROJECTS.md`,
  `docs/CONFIGURATION.md`, and `docs/ARTIFACTS.md`.

## Key decisions captured

- Treat repository as a 4-part pipeline: `local`, `fingerprints`,
  `code-archival`, `gdrive-archival`.
- Use `run_state.json` + `STATUS.md` on D5 as canonical runtime control-plane
  references in top-level docs.
- Standardize fingerprints output path as `D1/model-checksums/`.
- Clarify priority policy (1-4) independently from `requires_auth`.
- Keep GDrive docs explicit about registry mode vs staging mode and legacy paths.

## Validation

- Ran markdown lint diagnostics on edited files: no warnings/errors.
