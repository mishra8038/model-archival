# Remote Activity Log

Log of actions performed by Cursor agent(s) on this remote machine.

## 2026-03-25

- Verified active archiver/download processes (`aria2c`, `screen`, `scripts/run.sh`, `uv run archiver ...`).
- Read `/mnt/models/d5/STATUS.md` and sampled `/mnt/models/d5/run_state.json` for progress reporting.
- Confirmed running specialist queue and reported speed/ETA/completed/failed snapshot.

## 2026-03-25 (windowed caps)

- Restarted specialist archiver with 3h timeout at 4 MB/s:
  - `screen -dmS archiver timeout --signal=TERM --kill-after=10m 3h bash scripts/run.sh --all --registry config/registry-specialists.yaml --queue-mode serial --max-parallel 1 --bandwidth-cap 4 --skip-drive-space-check`
- Fixed `gdrive-archival/config.yaml` `archiver_root` to `/home/x/dev/model-archival/model-archiver` (was stale `/home/x/dev/model-archival/local`).
- Set `gdrive.bwlimit: 2M` and started 3h upload window:
  - `screen -dmS gdrive-update timeout --signal=TERM --kill-after=5m 3h bash run.sh`
- Verified detached screens: `archiver`, `gdrive-update`.


## 2026-03-25 verification — gdrive token
- Checked `screen -S gdrive-update` output.
- Observed rclone auth failure: `couldn\x27t fetch token: invalid_grant: maybe token expired? - try refreshing with "rclone config reconnect gdrive:"`.
- `logs/uploaded.log` unchanged since 2026-03-24 00:56Z (no new successful uploads).

## 2026-03-25 — post-reconnect upload status
- rclone auth verified:  lists .
- gdrive-update started, but staging roots  and  do not exist; explicit model list has only 2 paths present on disk.
- Action: create staging dirs or adjust / to match downloaded models.

## 2026-03-25 — post-reconnect upload status
- rclone auth verified (using project config): `RCLONE_CONFIG=/home/x/dev/model-archival/gdrive-archival/rclone.conf rclone lsf gdrive:` returned `models/`.
- gdrive-update started, but staging roots `/mnt/models/d3/gdrive-upload` and `/mnt/models/d5/gdrive-upload` do not exist.
- gdrive-archival is currently configured with explicit `model_ids_full` list; only 2 of those paths exist on disk, so the run has little/no work.
- Action: create staging dirs or adjust gdrive selection (explicit IDs or upload_selection) to match downloaded models.

## 2026-03-25 — gdrive registry uploader (upload-only)
- Safety: do NOT delete from Drive. Uploader uses `rclone copy` and optional `rclone check` only (no sync/delete/purge).
- Removed staging roots `d3/gdrive-upload` and `d5/gdrive-upload` from `gdrive-registry.yaml`.
- Patched `upload_registry.py` so all rclone subprocesses include `--config $RCLONE_CONFIG` (prevents falling back to ~/.config/rclone).
- Started gdrive-update with registry uploader + 3h timeout + bwlimit=2M:
  - `screen -dmS gdrive-update env RCLONE_CONFIG=$PWD/rclone.conf timeout --signal=TERM --kill-after=5m 3h bash run-registry-upload.sh --limit 50 --resync-all`
