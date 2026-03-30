# Archive inventory (GitHub-facing lists)

Machine-readable snapshots of **where models are assigned**, **optional on-disk manifest metadata and checksums**, **every `manifest.json` tree found under the models mount**, and **code-archival / gdrive registry lists**. Regenerate before pushing when registries or the archive host change.

## Regenerate

From the **repository root**:

```bash
uv run --directory model-archival python3 ../scripts/generate-archive-inventory.py
```

On the **archive host** (so paths, `run_state.json`, manifests, and `global_index.jsonl` resolve):

```bash
ARCHIVER_MODELS_MOUNT=/mnt/models \
ARCHIVER_RUN_STATE=/mnt/models/d3/run_state.json \
uv run --directory model-archival python3 ../scripts/generate-archive-inventory.py
```

**Full per-file SHA-256** (large JSON — use when you need a portable checksum manifest in git):

```bash
ARCHIVER_MODELS_MOUNT=/mnt/models \
uv run --directory model-archival python3 ../scripts/generate-archive-inventory.py --include-file-checksums
```

Optional: `ARCHIVER_GLOBAL_INDEX=/path/to/global_index.jsonl` if the index is not under `d3/archive/checksums/`. Use `--global-index-max-lines 0` to omit tail records.

## Files

| File | Contents |
|------|----------|
| `inventory-header.json` | UTC timestamp, models mount, run-state path, global index tail summary |
| `models-merged.json` | All unique model IDs from master + legacy + specialist registries, paths, download status, manifest summary + `manifest_sha256` when `manifest.json` is readable |
| `models-by-drive.json` | Same models grouped by `drive` (`d1` … `d5`) |
| `models-by-drive.md` | Human table per drive |
| `disk-manifest-hits.json` | Every revision directory under `raw/` / `quantized/` / `uncensored/` that contains `manifest.json` (includes paths not in YAML) |
| `archived-code-projects.json` | `code-archival/registry.yaml` as JSON |
| `archived-code-projects.md` | Short table of code projects |
| `gdrive-roots.json` | Upload roots + `d5_exclude` from `gdrive-archival/gdrive-registry.yaml` |
| `monorepo-scope.json` | Counts and pointers to authoritative registries |

**Authoritative sources** remain the YAML registries and live archive files; this folder is a **published index** for navigation and GitHub archival.
