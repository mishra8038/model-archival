# GDrive registry upload status

_Generated: 2026-03-25T20:02:32Z (UTC) — discovery under `models_mount` + [`logs/uploaded.log`](uploaded.log) (`registry-model` / `registry-d5`)._

## Summary

| Item | Value |
|------|-------|
| `models_mount` | `/mnt/models` |
| Model revision dirs discovered | 0 |
| Uploaded at least once (in log ∩ on disk) | 0 |
| Pending (on disk, not in log) | 0 |
| In log but path missing locally | 0 |
| Newest `registry-model` log timestamp | — |
| Last `registry-d5` (full `d5/` tree) log timestamp | — (not logged yet) |
| **Tracker** (`registry-upload-state.json`): models marked uploaded (skip rclone) | 0 |
| **Tracker**: `d5/` full tree marked complete | no |
| Pre-upload verify failure lines (`gdrive-preupload-verify-failures.jsonl`) | 0 |

**Regenerate:** `python3 backup.py upload-registry-status` — also refreshed automatically at the end of each `backup-registry` run.

## Pending

*No revision dirs discovered — check `models_mount` and `gdrive-registry.yaml` roots.*

## Uploaded model dirs (present on disk + in log)

*None.*

## Related logs

- Pre-upload checksum skips: [`gdrive-preupload-verify-report.md`](gdrive-preupload-verify-report.md)
