# GDrive archival

Backs up extra paths (registry, drives, D5 archive/logs/run_state, fingerprints, code-archives) and a curated subset of model dirs to Google Drive via rclone.

## rclone config

- **Config in repo:** `gdrive-archival/rclone.conf` is in the codebase with the target folder set (`root_folder_id = 1JFis3GXDbVxvRO_m4pJnBuO5LpYCf4sJ`). Replace the `token` line with your OAuth token (from `rclone config` or your existing config). The file is in `.gitignore` so your token is not committed.
- **Remote name:** Must be `[gdrive]`. Backup uses this remote; uploads go to the folder above.
- **Config location:** `run.sh` uses `./rclone.conf` in this directory first, then `~/Downloads/rclone.conf`, or set `RCLONE_CONFIG` to point at your config.

## Run once

```bash
cd /home/x/dev/model-archival/gdrive-archival
# Optional: export RCLONE_CONFIG=/home/x/Downloads/rclone.conf
bash run.sh
```

Or run subcommands:

```bash
python3 backup.py backup-extra   # only extra_paths
python3 backup.py backup-gguf   # only GGUF models
python3 backup.py backup-full   # only full-weight models
python3 backup.py backup-all    # extra + gguf + full
```

## Autostart (dinit)

To run backup once at boot (after network is up):

```bash
# Ensure logs dir exists and rclone config is findable (run.sh checks ~/Downloads/rclone.conf when run as your user)
mkdir -p /home/x/dev/model-archival/gdrive-archival/logs
sudo ln -sf /home/x/dev/model-archival/gdrive-archival/deploy/gdrive-backup.service /etc/dinit.d/boot.d/
```

For a **daily** (or other schedule) run, trigger manually or use cron:

```bash
# Example: run daily at 03:00
# 0 3 * * * RCLONE_CONFIG=/home/x/Downloads/rclone.conf bash /home/x/dev/model-archival/gdrive-archival/run.sh >> /home/x/dev/model-archival/gdrive-archival/logs/cron.log 2>&1
```

Alternatively trigger manually when you want:

```bash
bash /home/x/dev/model-archival/gdrive-archival/run.sh
```

## What gets uploaded

- **extra_paths:** registry.yaml, drives.yaml, D5 archive/, logs/, run_state.json, fingerprints dir, code-archives (see `config.yaml`).
- **Models:** Either a fixed list (`model_ids_gguf` / `model_ids_full`) or **budget-based selection** when `upload_selection` is set (see below). Run `python3 backup.py list-candidates` to see what would be uploaded without running rclone.

State is stored in `gdrive-archival/state.json` so already-backed-up models and paths are skipped on later runs.

### 3 TB budget selection

With ~3 TB free on GDrive, set `upload_selection` in `config.yaml` (already set by default): the script picks completed D2/D3 models from the archiver’s `run_state.json`, caps each at `max_per_model_gb` (200), and fills up to `max_total_gb` (3000), ordered by tier and priority. See `UPLOAD-SELECTION.md` for details.
