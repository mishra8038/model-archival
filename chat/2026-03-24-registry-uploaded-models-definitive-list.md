# Definitive uploaded models list

- Added `backup.py uploaded-registry-list` and auto-writer in `upload_registry.py` to produce:
  - `gdrive-archival/logs/registry-uploaded-models.json`
  - `gdrive-archival/logs/registry-uploaded-models.md`
- Source of truth: `logs/registry-upload-state.json` (`completed_models`), enriched with latest timestamp from `logs/uploaded.log` and estimated size from manifest/stat.
- VM snapshot at generation: 9 uploaded model dirs, ~17.577 GiB total estimated.
