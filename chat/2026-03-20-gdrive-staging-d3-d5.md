# GDrive staging workflow (D3/D5 → 1JFis3GX…)

- **`upload_staging`** in `config.yaml`: `/mnt/models/d3/gdrive-upload` → remote `d3/`, `/mnt/models/d5/gdrive-upload` → remote `d5/`. Each **immediate subdirectory** = one `rclone copy` job (resumable).
- **`gdrive.remote`:** `gdrive:1JFis3GXDbVxvRO_m4pJnBuO5LpYCf4sJ` (user’s target folder). `base_path: ""`.
- **Commands:** `backup-staging`, `list-staging`; **`run-staging.sh`**, **`start-staging-screen.sh`**; **`deploy/gdrive-staging.service`** for dinit.
- **Legacy** `extra_paths` / `upload_selection` commented out in `config.yaml`; **`run.sh`** unchanged for optional re-enable.
