# GDrive upload runbook

**Shared folder:** [Drive folder `1JFis3GXDbVxvRO_m4pJnBuO5LpYCf4sJ`](https://drive.google.com/drive/folders/1JFis3GXDbVxvRO_m4pJnBuO5LpYCf4sJ)

**Path rule:** local `/mnt/models/<relpath>/` → remote `models/<relpath>/` under that folder.

**Registry:** [`gdrive-archival/gdrive-registry.yaml`](../gdrive-archival/gdrive-registry.yaml)

**Automated uploader (archive host):**

```bash
cd /home/x/dev/model-archival/gdrive-archival
python3 backup.py list-registry              # what will be uploaded (model dirs + d5 tree note)
python3 backup.py backup-registry --dry-run  # rclone dry-run
python3 backup.py backup-registry --limit 1   # first model only (smoke test)
python3 backup.py backup-registry             # full run
python3 backup.py upload-registry-status      # refresh upload dashboard only (no rclone)
# or: bash run-registry-upload.sh [--dry-run] [--limit N]
```

**Upload dashboard:** after each `backup-registry` run (and on demand via `upload-registry-status`), the repo writes [`gdrive-archival/logs/GDRIVE-REGISTRY-UPLOAD-STATUS.md`](../gdrive-archival/logs/GDRIVE-REGISTRY-UPLOAD-STATUS.md) — discovered model dirs vs lines in `logs/uploaded.log` (`registry-model`), optional `registry-d5` timestamp, pending list, and pointer to verify-failure logs.

**Local tracker (no GDrive listing for done dirs):** [`gdrive-archival/logs/registry-upload-state.json`](../gdrive-archival/logs/registry-upload-state.json) records each model relpath after a successful verify + `rclone copy`. Later `backup-registry` runs **skip** those dirs entirely (no rclone). First-time seed: if the JSON file is missing, it is built from existing `registry-model` / `registry-d5` lines in `uploaded.log`. Force a full pass: `backup-registry --resync-all`.

**Remote spot-check (idempotent):** Default on via `gdrive.registry_verify_remote: true` in [`config.yaml`](../gdrive-archival/config.yaml). For tracker-skipped model dirs, runs **`rclone check --checksum --one-way`** (local hash vs Drive-side hash metadata; **does not** bulk-download weights). If the check fails, the uploader re-runs local verify + `rclone copy` for that path. Same for **`d5/`** when `d5_complete`. Turn off for one run: `backup-registry --no-verify-remote`. Force on: `--verify-remote`.

**Screen lifecycle:** [`gdrive-archival/start.sh`](../gdrive-archival/start.sh) runs [`stop.sh`](../gdrive-archival/stop.sh) first (screens, upload Python, `rclone copy /mnt/models`), then starts `screen` **`gdrive-upload`**. Override: `START_SKIP_STOP=1 bash start.sh` (not recommended).

Uses local **manifest/sidecar** verify (unless `--no-verify`), then **`rclone copy --checksum --transfers 1`**. If `d5` is in the registry, ends with a full **`d5/` → `models/d5/`** sync excluding `.tmp/**`.

If local verify fails for a model directory, that directory is **skipped** (not uploaded) and the failure is **appended** to:

- [`gdrive-archival/logs/gdrive-preupload-verify-report.md`](../gdrive-archival/logs/gdrive-preupload-verify-report.md) — short Markdown table per model
- [`gdrive-archival/logs/gdrive-preupload-verify-failures.jsonl`](../gdrive-archival/logs/gdrive-preupload-verify-failures.jsonl) — one JSON line per bad file (full expected/actual SHA-256)

The run still exits **0** when only verify skips occur; **1** only if **rclone** fails.

Run all commands **on the archive host** where `/mnt/models` is mounted. Set:

```bash
export RCLONE_CONFIG=/path/to/rclone.conf   # or use ~/Downloads/rclone.conf
REMOTE='gdrive:1JFis3GXDbVxvRO_m4pJnBuO5LpYCf4sJ'
```

## Pristine check (SHA-256) before upload

The archiver records **`manifest.json`** (paths + expected SHA-256) and/or **`.sha256` sidecars** per weight file. Before any `rclone copy`, verify the local tree so you only upload **bit-identical** content.

**Option A — by directory** (works for any path under `/mnt/models`, from repo `gdrive-archival/`):

```bash
cd /home/x/dev/model-archival/gdrive-archival   # or path to this repo on the VM
python3 verify_local_model_dir.py \
  "/mnt/models/d3/quantized/bartowski/Qwen2.5-7B-Instruct-GGUF/8911e8a47f92bac19d6f5c64a2e2095bd2f7d031"
```

If `model-archival/src` is not next to `gdrive-archival` in the tree, set:

```bash
export ARCHIVER_SRC=/home/x/dev/model-archival/model-archival/src
```

**Option B — by registry model id** (from `model-archival/`, only if the model is present and complete):

```bash
cd /home/x/dev/model-archival/local
uv run archiver verify "bartowski/Qwen2.5-7B-Instruct-GGUF"
```

Exit code must be **0** / all **PASS** before uploading. If verification fails, fix the local files (re-download, fsck, etc.) — **do not** upload.

---

## Network and verification policy

| Step | What happens | Egress / download from GDrive? |
|------|----------------|----------------------------------|
| **Local pristine check** | Read files on disk; SHA-256 vs `manifest.json` / sidecars | **No** GDrive traffic |
| **`rclone copy --checksum`** | Hash locally; compare to **remote file metadata** (e.g. MD5 from Drive API) to **skip** unchanged files | **No** full re-download of stored weights for verification; only **upload** missing/changed bytes |
| **Post-upload “prove it on Drive”** | e.g. `rclone check` downloading every object | **Not used** — would blow bandwidth; **do not** run for full model trees |

So: **trust** = local archiver verify **before** upload + rclone’s checksum-based **skip** on resume. **Do not** verify integrity by pulling models back from Google Drive.

**Cost of `--checksum` on resume:** rclone still **reads each local file** to compute a hash (disk I/O, not GDrive download). That avoids mistaken “already there” skips if sizes match but content differs, and avoids redundant **upload** traffic.

---

## Verify-first: one model (1 transfer, `rclone --checksum`)

**Proposed first upload** (smaller than the Qwen bases): **bartowski Qwen2.5-7B Instruct GGUF**.

| | |
|--|--|
| **Local source** | `/mnt/models/d3/quantized/bartowski/Qwen2.5-7B-Instruct-GGUF/8911e8a47f92bac19d6f5c64a2e2095bd2f7d031` |
| **Remote destination** | `gdrive:1JFis3GXDbVxvRO_m4pJnBuO5LpYCf4sJ/models/d3/quantized/bartowski/Qwen2.5-7B-Instruct-GGUF/8911e8a47f92bac19d6f5c64a2e2095bd2f7d031` |
| **In browser** | Inside the shared folder, open **`models` → `d3` → `quantized` → `bartowski` → `Qwen2.5-7B-Instruct-GGUF` → `8911e8a47f92bac19d6f5c64a2e2095bd2f7d031`** |

Dry-run (no upload):

```bash
rclone copy \
  "/mnt/models/d3/quantized/bartowski/Qwen2.5-7B-Instruct-GGUF/8911e8a47f92bac19d6f5c64a2e2095bd2f7d031" \
  "${REMOTE}/models/d3/quantized/bartowski/Qwen2.5-7B-Instruct-GGUF/8911e8a47f92bac19d6f5c64a2e2095bd2f7d031" \
  --checksum --transfers 1 --checkers 1 --dry-run
```

Real upload:

```bash
rclone copy \
  "/mnt/models/d3/quantized/bartowski/Qwen2.5-7B-Instruct-GGUF/8911e8a47f92bac19d6f5c64a2e2095bd2f7d031" \
  "${REMOTE}/models/d3/quantized/bartowski/Qwen2.5-7B-Instruct-GGUF/8911e8a47f92bac19d6f5c64a2e2095bd2f7d031" \
  --checksum --transfers 1 --checkers 1 --retries 10 --low-level-retries 20
```

If your revision directory is `main` instead of the SHA, replace the last path segment in both local and remote paths.

## After you confirm

A registry-driven uploader should: **(1)** `verify_local_model_dir.py` (or `archiver verify`) on each model subtree, **(2)** `rclone copy` only if step 1 passed, with **`--transfers 1`**, **`--checksum`** (skip re-upload when remote hash matches; **no** post-upload download verification). Do **not** add a third step that downloads from GDrive to re-hash models.

## Script reference

| Script | Role |
|--------|------|
| [`gdrive-archival/verify_local_model_dir.py`](../gdrive-archival/verify_local_model_dir.py) | Full SHA-256 check vs manifest/sidecars before upload |
