# Operations Guide

Day-to-day usage, monitoring, troubleshooting, and maintenance for the model-archival system.

---

## Starting a download run

Always run inside `screen` — downloads take hours to days and SSH sessions drop.

```bash
# Start a new screen session
screen -S archiver

# Full run (all tiers, all priorities)
cd /opt/model-archival
bash run.sh

# Detach from screen (leave running):  Ctrl+A  D
# Reattach later:
screen -r archiver
```

### Common run.sh options

```bash
bash run.sh --dry-run               # simulate, no downloads
bash run.sh --priority-only 1       # token-free models only (no HF token needed)
bash run.sh --tier A                # Tier A only
bash run.sh --tier B                # Tier B (code models) only
bash run.sh --bandwidth-cap 200     # cap at 200 MB/s
bash run.sh --rehash                # full SHA-256 re-hash of all files after download
bash run.sh --skip-env-check        # skip environment verification (faster restart)
bash run.sh --failures-only         # only retry previously failed models
```

The script is fully idempotent — re-running it skips already-verified models.

---

## Monitoring a running download

### Live status file

```bash
watch -n 30 cat /mnt/models/d5/STATUS.md
```

Updated atomically every ~60 seconds. Shows per-model progress, drive usage, and totals.

### Reattach to session

```bash
screen -r archiver
screen -ls                  # list all sessions
```

### Per-model status table

```bash
bash scripts/archiver-status.sh
# or:
uv run archiver status
```

### Drive usage

```bash
bash scripts/archiver-drives.sh
# or:
uv run archiver drives status
```

Shows used/free space per drive and which models are assigned there.

### Log tail

```bash
# Text log (human-readable, box-drawing style):
tail -f /mnt/models/d5/logs/archiver-*.log | tail -100

# Structured JSON log (for grepping):
tail -f /mnt/models/d5/logs/archiver-*.jsonl
```

---

## After downloads complete

### Check the session report

The run generates a timestamped report:

```bash
ls -lt /mnt/models/d5/logs/run-report-*.md | head -5
cat /mnt/models/d5/logs/run-report-<timestamp>.md
```

Also, `run.sh` writes a `run-report-<ts>.md` to the project root after completing all steps.

### Run a standalone integrity verification

Fast sidecar cross-check (compares `.sha256` files against `manifest.json`, no re-hashing):

```bash
bash scripts/verify-archive.sh
# or directly:
python3 verification/verify-archive.py \
  --drives /mnt/models/d1 /mnt/models/d2 /mnt/models/d3 /mnt/models/d5
```

Full SHA-256 re-hash from disk (very slow — only needed after hardware events):

```bash
python3 verification/verify-archive.py \
  --drives /mnt/models/d1 /mnt/models/d2 /mnt/models/d3 /mnt/models/d5 \
  --rehash
```

### Verify a single model

```bash
uv run archiver verify deepseek-ai/DeepSeek-R1
# or standalone:
python3 verification/verify-archive.py \
  --model-dir /mnt/models/d1/deepseek-ai/DeepSeek-R1/<commit-sha>
```

---

## Adding a new model

1. Open `config/registry.yaml`
2. Add an entry:

```yaml
org/ModelName:
  hf_repo: org/ModelName
  commit_sha: null          # resolves latest on first download
  tier: A                   # A / B / C / D
  priority: 1               # 1 = no token needed, 2 = gated
  drive: d1                 # which drive to store on
  auth_required: false
  license: Apache-2.0
  description: "One-line description"
  tags: [llm, reasoning]
```

3. Run `bash run.sh --dry-run` to preview
4. Run `bash run.sh` to download

---

## Pinning a model to a specific commit

```bash
uv run archiver pin deepseek-ai/DeepSeek-R1 <commit-sha>
```

This writes the commit SHA into `run_state.json`. Future runs will use this exact commit and skip the HF API resolution.

To see the current commit for a model:

```bash
uv run archiver status | grep DeepSeek-R1
```

---

## Checking HuggingFace token access

```bash
uv run archiver tokens check
```

Shows which gated models are accessible with the current `HF_TOKEN`.

To update the token:

```bash
bash deploy/sethfToken.sh hf_NEWTOKEN
source ~/.bashrc
```

---

## Disk maintenance

### Check drive health

```bash
sudo smartctl -a /dev/sdX
```

### Check free space

```bash
df -h /mnt/models/d1 /mnt/models/d2 /mnt/models/d3 /mnt/models/d5
```

### Re-mount after reboot

```bash
sudo mount -a
# verify:
mount | grep /mnt/models
```

### If a drive was replaced

1. Run `deploy/vm-mount-disks.sh --wipe` to format and mount the new drive
2. Run `uv run archiver download --drive dN` to re-download models assigned to that drive
3. The existing `manifest.json` files on other drives are unaffected

---

## Troubleshooting

### Downloads not starting

```bash
# Check pre-flight:
bash deploy/verify-environment.sh

# Check aria2c is installed:
which aria2c

# Check drives are mounted:
mount | grep /mnt/models

# Check run_state.json for stuck "in_progress" entries:
cat /mnt/models/d5/run_state.json | python3 -m json.tool | grep -A2 in_progress
```

### A model stays "in_progress" after crash

```bash
# Reset a single model's state:
uv run archiver status            # find the model id
# Edit run_state.json manually and set status back to "pending"
nano /mnt/models/d5/run_state.json
```

Or just re-run `bash run.sh` — the downloader will pick up from the last complete file thanks to `.sha256` sidecar checks.

### Checksum failure after download

The downloader automatically removes the corrupt file and marks the model for retry. On next run it re-downloads only the failed files.

To manually inspect failures:

```bash
python3 verification/verify-archive.py \
  --drives /mnt/models/d1 /mnt/models/d2 \
  --failures-only
```

### STATUS.md not updating

```bash
ls -la /mnt/models/d5/STATUS.md
# Should be writable:
touch /mnt/models/d5/STATUS.md
```

If D5 is full:

```bash
df -h /mnt/models/d5
# Logs accumulate in /mnt/models/d5/logs/ — remove old ones if needed
ls -lh /mnt/models/d5/logs/
```

### HF 401 / 403 on a gated model

1. Check the token is set: `echo $HF_TOKEN`
2. Verify access on huggingface.co for the specific model (must accept terms per-model)
3. Re-run `bash deploy/sethfToken.sh hf_NEWTOKEN` if the token changed

### LFS URL expired (0-byte file or connection reset)

This is handled automatically — the downloader calls `hf_api.get_paths_info()` to get a fresh CDN URL on each run. Simply re-run `bash run.sh`.

### Network timeout / rate limiting (HTTP 429)

The downloader has exponential backoff with jitter, up to 5 retries. If HuggingFace is rate-limiting:

```bash
# Cap bandwidth to reduce request rate:
bash run.sh --bandwidth-cap 100
```

### Disk full mid-download

The downloader detects `ENOSPC` and raises `DiskFullError`, which triggers a graceful shutdown. The partial `.tmp` file is left in place (aria2c can resume it). After freeing space or adding a drive, re-run `bash run.sh`.

### aria2c daemon not responding

```bash
# Kill and restart:
pkill aria2c
bash run.sh
```

### Cursor Remote SSH "Terminal sandbox could not start"

```bash
bash deploy/fix-apparmor-cursor.sh
```

---

## Maintenance tasks

### Rotate old logs

```bash
find /mnt/models/d5/logs/ -name "archiver-*.log" -mtime +30 -delete
find /mnt/models/d5/logs/ -name "run-report-*.md" -mtime +60 -delete
```

### Replicate metadata to all drives

The archiver replicates `manifest.json`, `global_index.jsonl`, and state files to all drives automatically. To trigger a manual replication:

```bash
uv run archiver verify --all --replicate-only
```

### Upgrade a model to a newer version

1. Update `commit_sha` in `config/registry.yaml` (or set to `null` for latest)
2. The new version downloads to a new subdirectory: `<drive>/<org>/<model>/<new-commit-sha>/`
3. Old version is preserved — delete manually if space is needed

```bash
# Download only the upgraded model:
uv run archiver download <model-id>
```

---

## File layout reference

```
/mnt/models/
  d1/
    .tmp/                             in-progress downloads (aria2 resume files here)
    deepseek-ai/
      DeepSeek-R1/
        abc123def456.../              commit SHA subdirectory
          config.json
          config.json.sha256
          model-00001.safetensors
          model-00001.safetensors.sha256
          ...
          manifest.json               per-model checksum manifest
          DESCRIPTOR.json             machine-readable provenance
          DESCRIPTOR.md               human-readable provenance

  d5/
    STATUS.md                         live status page
    run_state.json                    persistent per-model download state
    global_index.jsonl                append-only checksum ledger (all models)
    logs/
      archiver-<ts>.log               structured text log
      archiver-<ts>.jsonl             structured JSON log
      run-report-<ts>.md              session Markdown report

verification/
  verify-archive.py                   standalone verifier (no archiver import)
  verification-reports/
    verify-report-<ts>.md             verification Markdown reports
```
