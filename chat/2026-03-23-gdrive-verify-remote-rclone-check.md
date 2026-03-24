# GDrive — remote verify for tracker skips

- Default **`gdrive.registry_verify_remote: true`** in `config.yaml`: for dirs the tracker would skip, run **`rclone check --checksum --one-way`** (local hash vs Drive metadata; no full download). Failure → local verify + `rclone copy` again. Same for **`d5/`** when `d5_complete`.
- **`backup-registry --no-verify-remote`** disables for one run; **`--verify-remote`** forces on even if config false.
