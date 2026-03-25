# GDrive registry upload tracker + start/stop

- **`logs/registry-upload-state.json`**: After each successful `registry-model` upload, append relpath to `completed_models` (atomic write). Later `backup-registry` runs skip verify+rclone for those paths unless `--resync-all`. `d5_complete` skips the full `d5/` rclone when set. New file seeds from `uploaded.log` (`registry-model` / `registry-d5`).
- **`start.sh`**: Runs `stop.sh` then `screen -S gdrive-upload` → `python3 -u backup.py backup-registry`. `START_SKIP_STOP=1` bypasses stop.
- **`stop.sh`**: Kills `rclone copy /mnt/models` (narrow) plus upload Python helpers and gdrive-* screens.
