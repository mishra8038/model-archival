# GDrive specialist priority + strict verify + smallest-first

- Added `d3/specialist` and `d5/specialist` as top roots in `gdrive-archival/gdrive-registry.yaml` (ahead of broad roots).
- `upload_registry.py`: strict pre-upload integrity policy — if verifier path/import unavailable, model is skipped (no upload) unless `--no-verify`.
- `upload_registry.py`: model dirs sorted by estimated size ascending before upload; estimate uses manifest `size_bytes` sum first, fallback recursive stat.
- Synced updated `upload_registry.py` and `gdrive-registry.yaml` to VM.
