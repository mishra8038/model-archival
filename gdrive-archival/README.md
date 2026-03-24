# GDrive archival

Upload to Google Drive via rclone. **Primary workflow:** `gdrive-registry.yaml` → `models/…` on Drive (`backup-registry`). Optional **staging** dirs on D3/D5 (`backup-staging`). Legacy **`run.sh`** if you re-enable `extra_paths` / `upload_selection` in `config.yaml`.

## Start / stop (screen + process cleanup)

```bash
cd /home/x/dev/model-archival/gdrive-archival
bash start.sh              # runs stop.sh first, then registry upload in screen 'gdrive-upload' → logs/registry-upload.log
bash start.sh staging      # runs stop.sh first, then staging in screen 'gdrive-staging' → logs/staging-upload.log
bash stop.sh               # quit gdrive-* screens; upload Python; rclone copy /mnt/models
```

**`start.sh`** always invokes **`stop.sh`** first (unless `START_SKIP_STOP=1`) so duplicate screen sessions and stray `rclone`/`python` jobs are cleared before attaching a new upload.

**`stop.sh`** tears down: `gdrive-upload`, `gdrive-registry`, `gdrive-staging`, `gdrive-backup` screen sessions, then `python3 … backup-registry|backup-staging`, `upload_registry.py`, `run-staging.sh` / `run-registry-upload.sh`, and **`rclone copy /mnt/models`** (registry layout only).

**Tracker:** `logs/registry-upload-state.json` — after each successful model dir upload, that relpath is recorded; future runs **skip rclone** for it (use `backup-registry --resync-all` to ignore). Seeded from `uploaded.log` on first create.

**Remote verify (idempotent):** default `gdrive.registry_verify_remote: true` — for tracker-skipped dirs, `rclone check --checksum --one-way` vs Drive before skipping; mismatch → re-upload. Override: `--no-verify-remote` or set config to `false`.

**Pre-upload verify failures** (`backup-registry` / `upload_registry.py`): model dirs that fail local SHA-256 vs manifest are **skipped** and appended to `logs/gdrive-preupload-verify-report.md` and `logs/gdrive-preupload-verify-failures.jsonl`. See `docs/GDRIVE-UPLOAD-RUNBOOK.md`.

**Upload status:** `logs/GDRIVE-REGISTRY-UPLOAD-STATUS.md` is refreshed at the end of every `backup-registry` run and when you run `python3 backup.py upload-registry-status` (pending vs logged uploads, last `registry-d5` sync time).

## Staging workflow (optional)

1. **Create staging dirs** on the archive host (once):

   ```bash
   mkdir -p /mnt/models/d3/gdrive-upload /mnt/models/d5/gdrive-upload
   ```

2. **Place each model** you intend to upload as **its own subdirectory** under `d3` or `d5` staging (symlinks or moves from your real `quantized/` or `raw/` trees are fine).

3. **Dry-run** (lists subdirs + verification):

   ```bash
   cd /home/x/dev/model-archival/gdrive-archival
   python3 backup.py list-staging
   ```

4. **Upload / resume** (idempotent `rclone copy --checksum` per model subdir):

   ```bash
   bash run-staging.sh
   # or: python3 backup.py backup-staging
   ```

5. **Screen:** `bash start.sh staging` (or `bash start-staging-screen.sh`) then `screen -r gdrive-staging`

**Remote layout:** `gdrive:<folder_id>/d3/<model_dir>/…` and `…/d5/<model_dir>/…` (see `upload_staging` → `dest` in `config.yaml`). Loose files sitting directly in the staging root are warned and **not** uploaded—only **immediate subdirectories** are synced.

**Config keys:** `upload_staging` (list of `{ path, dest, exclude? }`), `upload_staging_verify` (default `true`: manifest / `.sha256` check per subdir).

## rclone config

- **Remote name:** Must be `[gdrive]`. **Folder ID** in `config.yaml` → `gdrive.remote` must match `root_folder_id` in `rclone.conf` if you set it—**do not** point those at two different folders or uploads will land in the wrong tree.
- **Token:** Copy `rclone.conf.sample` → `rclone.conf`, add OAuth token. `rclone.conf` is gitignored.
- **Config discovery:** `run-staging.sh` / `run.sh` use `./rclone.conf`, then `~/Downloads/rclone.conf`, or `RCLONE_CONFIG`.

## Legacy: `run.sh` (extra_paths + registry models)

If you uncomment **`extra_paths`**, **`upload_selection`**, etc. in `config.yaml`:

```bash
bash run.sh   # backup-extra-refresh, backup-gguf, backup-full
```

Subcommands:

```bash
python3 backup.py backup-staging          # staging folders only
python3 backup.py list-staging
python3 backup.py backup-extra            # extra_paths only
python3 backup.py backup-extra-refresh
python3 backup.py backup-extra-if-pending
python3 backup.py backup-gguf
python3 backup.py backup-full
python3 backup.py backup-all
python3 backup.py list-candidates
python3 backup.py compare-with-archiver
python3 backup.py backup-dirs /path/to/model/dir ...
```

### Metadata sentinel (`run.sh` workflow)

When the archiver updates metadata it can touch `metadata_pending_path` on D5. Use `backup-extra-if-pending` or `backup-extra-refresh` as before.

**Idempotent and resumable:** Each sync uses `rclone copy --checksum`; rclone only transfers missing or changed files. Re-run after interruption to resume. `state.json` is audit-only and does not block rclone.

## Autostart (dinit)

```bash
mkdir -p /home/x/dev/model-archival/gdrive-archival/logs
# For staging-only uploads, point the service at run-staging.sh instead of run.sh if desired.
sudo ln -sf /home/x/dev/model-archival/gdrive-archival/deploy/gdrive-backup.service /etc/dinit.d/boot.d/
```

Cron example: run `run-staging.sh` on a schedule when you use the staging workflow.

## Reference

- **3 TB budget / registry ordering:** `UPLOAD-SELECTION.md` (legacy when `upload_selection` is enabled).
- **Upload log:** `logs/uploaded.log` (audit; not used to skip work).
