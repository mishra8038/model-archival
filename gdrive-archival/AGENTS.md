---
description: Agent bootstrap for gdrive-archival (upload-only Google Drive sync via rclone).
alwaysApply: true
---

# gdrive-archival — agents

## Start here

- **Runbook:** `docs/GDRIVE-UPLOAD-RUNBOOK.md`
- **Primary plan:** `gdrive-archival/gdrive-registry.yaml` + `gdrive-archival/upload_registry.py`
- **Local audit:** `gdrive-archival/logs/` (tracker + status)

## Safety invariant (must)

- **Upload-only:** use `rclone copy` + optional `rclone check` only.
- **Never delete from Drive:** do not use `rclone sync`, `delete`, `purge`, or any `--delete*` flags.

## Common failure mode

- If rclone says “didn’t find section (gdrive)”, ensure the process is using the intended config file:
  - export `RCLONE_CONFIG=/path/to/gdrive-archival/rclone.conf`
  - registry uploader must pass `rclone --config "$RCLONE_CONFIG" ...` to avoid falling back to `~/.config/rclone/rclone.conf`.

## Entry points

```bash
cd gdrive-archival

# Registry-driven upload (preferred)
bash run-registry-upload.sh [--dry-run] [--limit N] [--resync-all]

# Human-friendly wrapper (screen lifecycle)
bash start.sh
bash stop.sh
```

