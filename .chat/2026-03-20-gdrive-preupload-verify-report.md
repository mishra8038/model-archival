# GDrive pre-upload verify failure report

- **`upload_registry.py`**: On local manifest/sidecar checksum failure, skip `rclone copy` for that model dir; append rows to `logs/gdrive-preupload-verify-report.md` (Markdown) and `logs/gdrive-preupload-verify-failures.jsonl` (one JSON object per bad file with full expected/actual SHA-256).
- **Exit code**: `1` only for rclone failures; verify-only skips still exit `0` (stderr summary points at the log files).
- **Docs**: `docs/GDRIVE-UPLOAD-RUNBOOK.md`, `gdrive-archival/README.md`.
