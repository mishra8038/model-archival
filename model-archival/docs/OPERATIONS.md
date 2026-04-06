# Operations Guide

Day-to-day usage, monitoring, troubleshooting, and maintenance for the model-archival system.

---

## Starting a download run

### Forward policy: max checkpoint size (80 GiB)

**Default (`run.sh`):** new downloads are **skipped** when the summed Hugging Face LFS+XET file sizes for a checkpoint exceed **80 binary GiB** (`1024³` bytes per file, then summed). Those models are recorded in `run_state.json` as **`deferred_large`** (not `failed`). They are **not** retried automatically until you clear or edit that state, raise the cap, or run without a cap.

- **CLI:** `uv run archiver download --max-model-download-gib 80 …` (omit the flag for no cap).
- **`run.sh`:** default `MAX_MODEL_DOWNLOAD_GIB=80`; use **`--no-max-model-download`** for full registry sizes (e.g. 70B+ BF16 giants), or **`--max-model-download-gib N`** to change the threshold.

When adding models to the registry, prefer checkpoints that fit under this cap unless you plan a dedicated uncapped run.

---

Always run inside `screen` — downloads take hours to days and SSH sessions drop.

```bash
# Start archiver inside a named screen session
screen -S archiver bash run.sh --all

# Detach from screen (leave running):  Ctrl+A  D
# Reattach later:
screen -r archiver
```

The default `run.sh` profile is intentionally neighbor-friendly: it caps aggregate download traffic at `6 Mbps` (`0.75 MB/s`) and processes the queue serially.

### Common run.sh options

```bash
bash run.sh --all                   # download everything (P1 + P2, all tiers) — default
bash run.sh --dry-run               # simulate, no downloads
bash run.sh --priority-only 1       # token-free models only (no HF token needed)
bash run.sh --tier A                # Tier A only
bash run.sh --tier B                # Tier B (code models) only
bash run.sh --bandwidth-cap 0.75    # cap at 0.75 MB/s = 6 Mbps
bash run.sh --queue-mode adaptive   # opt back into adaptive parallel downloads
bash run.sh --registry config/registry-specialists.yaml --drive d3   # only models with drive: d3
bash run.sh --rehash                # full SHA-256 re-hash of all files after download
bash run.sh --skip-env-check        # skip environment verification (faster restart)
```

The script is fully idempotent — re-running it skips already-verified models.

### Specialist registry — one model, flat cap (restart friendly)

Checkpoints whose Hugging Face LFS+XET total is **above ~140 GB** are **not** listed in `registry-specialists.yaml`; they live in **`config/registry.yaml`** only (pull them with the default registry / `--all`, often with `--no-max-model-download` when above the 80 GiB default cap). The specialist file keeps smaller discipline + GGUF + tag-map entries; BF16 parents for Ollama-class maps remain in the main registry.

To **resume or start exactly one** model from `config/registry-specialists.yaml` with a **single global cap** (serial queue = one model at a time):

```bash
# 1 MB/s total (tool uses mebibytes/s; not megabits/s)
screen -S specialist bash scripts/download-specialist-one.sh 'org/model-id'

# ~1 megabit/s line rate instead → 0.125 MB/s
BANDWIDTH_CAP_MBPS=0.125 screen -S specialist bash scripts/download-specialist-one.sh 'org/model-id'
```

`archiver download` matches the positional argument to the registry **`id`** field (same string as on Hugging Face, e.g. `seyonec/ChemBERTa-zinc-base-v1`). Re-run the same command to **continue** a partial download.

### Specialist registry + GDrive upload (phased drives)

**Goal:** Pull specialist weights to **D3** while `rclone` upload runs against **D5** (separate `screen` sessions). Later you can **copy raw trees from D1/D2 → D5** for consolidation (those paths are **not** in the default GDrive “pending” set until you choose to sync them). After D5 work, run the same specialist registry limited to **D1/D2** (and **d5** rows) so large BF16 lands on the right spindles.

1. **Uploader (existing):** e.g. `screen -S gdrive-upload bash run-registry-upload.sh` from `gdrive-archival/` (see `gdrive-archival/docs/GDRIVE-UPLOAD-RUNBOOK.md`).
2. **Archiver — D3-only slice** (does not touch registry `drive: d5` rows):

```bash
screen -S archiver-specialists-d3 bash run.sh --all \
  --registry config/registry-specialists.yaml \
  --drive d3 \
  --bandwidth-cap 2 \
  --queue-mode serial
```

Use `--skip-drive-space-check` if preflight aborts on a full drive you are not writing to this run.

3. **After moving raw D1/D2 → D5:** run the remaining specialist entries on their assigned drives, e.g.:

```bash
screen -S archiver-specialists-rest bash run.sh --all \
  --registry config/registry-specialists.yaml \
  --drive d1 --drive d2 --drive d5 \
  --bandwidth-cap 2
```

(`--drive` may be passed multiple times in `run.sh`.)

**Do not** use `--storage-drive d3` for the whole specialist list unless you intentionally want every model file on D3 — large `drive: d5` rows belong on D5 when you are ready.

### One active download per disk (`.tmp` / incomplete models)

LFS scratch lives under **`<destination_mount>/.tmp/<model_slug>/`**. To avoid several large partials on the same spindle and to concentrate free space for the **largest single shard** being written, cap **one concurrent model per drive** and allow multiple drives in parallel:

```bash
# Example: adaptive pool, at most one partial per d1/d2/d3/d5 at a time
uv run archiver --registry config/registry-specialists.yaml download --all \
  --queue-mode adaptive \
  --max-parallel-drives 5 \
  --max-per-drive 1 \
  --min-speed-mbps 3 \
  --bandwidth-cap 2
```

Or via `run.sh`:

```bash
bash run.sh --all --registry config/registry-specialists.yaml \
  --queue-mode adaptive --max-parallel 5 --max-per-drive 1 --bandwidth-cap 2
```

`--queue-mode serial` (default in `run.sh`) already implies a **single** active model globally — use the pattern above when you want **parallelism across disks** but not **within** a disk.

### Queue plan (order + sizes + free space — e.g. after ENOSPC)

When preflight fails on low space or you want a printable plan:

```bash
uv run archiver --registry config/registry-specialists.yaml queue-plan \
  --out-md /mnt/models/d3/logs/QUEUE-PLAN.md
```

- **By drive (default):** each disk shows **free/total/used** once, then models targeting that `drive:` in order `(effective priority, id)`. **Est. size** = `run_state` `total_bytes` when known.
- **Merged list:** add `--flat` for a single table sorted `eff. priority → drive → id`.
- **Order:** same sort keys as the scheduler. With several workers, bandwidth gating can interleave jobs — treat as approximate.
- **Est. size:** `total_bytes` from `run_state.json` when the downloader has planned the manifest (otherwise `—`).
- **Free on dest:** live `df` via `psutil` for each registry drive mount. Rows with **&lt; 50 GiB** free match the default preflight abort threshold (unless you use `--skip-drive-space-check` on `download`).

JSON for tooling: `queue-plan --json`. No Hugging Face downloads; optional `--skip-token-check` to skip gated API probes.

### Specialist queue: finish near-complete models first (priority overrides)

`DriveScheduler` reads **`priority_overrides.json`** on the infra drive (D3). Lower numbers run sooner. To **boost models that are already half-done on disk** and **defer large trees that are only ~20–40% complete** (until later in the queue), regenerate overrides from `run_state.json` + a multi-drive scan:

```bash
# From the archiver repo root on the VM (paths may be model-archiver/ on disk)
uv run python scripts/compute-priority-overrides.py \
  --registry config/registry-specialists.yaml \
  --run-state /mnt/models/d3/run_state.json \
  --mount /mnt/models \
  --merge /mnt/models/d3/priority_overrides.json \
  --output /mnt/models/d3/priority_overrides.json \
  --defer-id 'MiniMaxAI/MiniMax-M2.5'
```

Repeat `--defer-id` for any huge partial where `run_state` has `total_bytes: 0`. Tune thresholds with `--finish-ratio`, `--large-bytes`, `--defer-below-ratio`. Overrides are re-read on each scheduler pick — no archiver restart required unless you change the running process.

**Older VM `run.sh` without `--drive`:** start the specialist queue with the archiver CLI (global `--registry`):

```bash
screen -S archiver-specialists bash -lc \
  'cd /path/to/archiver && uv run archiver --registry config/registry-specialists.yaml download --all \
    --queue-mode adaptive --max-parallel-drives 4 --max-per-drive 2 \
    --bandwidth-cap 4 --min-speed-mbps 3 --skip-drive-space-check \
    2>&1 | tee -a /mnt/models/d3/logs/archiver-specialists.log'
```

---

## Stopping downloads gracefully

**Always stop the archiver before rebooting.** An unclean kill mid-write can corrupt the filesystem on the target drive (requires `fsck` to recover).

```bash
# From any terminal — graceful stop (finishes current shard, then exits cleanly)
bash stop.sh

# Force-kill immediately (aria2 .aria2 control files are preserved, downloads resume)
bash stop.sh --force

# Check if archiver is running and its PID
bash stop.sh --status
```

`stop.sh` reads `.archiver.pid` from the repo root (written by `run.sh` at startup). Downloads are fully resumable after a graceful stop — re-run `bash run.sh --all` to continue from exactly where it left off.

You can also send the signal directly to the screen session:
```bash
# Send Ctrl+C to the archiver's screen session
screen -S archiver -X stuff $'\003'
```

---

## Monitoring a running download

### Live screen GUI

The archiver displays a rich live UI inside the screen session showing:
- **Progress bar** — overall % + bytes downloaded / total + **speed in MB/s** + ETA + elapsed time
- **Active Downloads** — per-drive table with speed column; panel title shows aggregate throughput and Mbps
- **Drive Usage** — bar charts per drive
- **Queue** — pending models
- **Completed** — verified models with sizes

Speed colour coding: green ≥ 20 MB/s, yellow ≥ 5 MB/s, red < 5 MB/s.

```bash
# Snapshot current screen output without attaching:
screen -S archiver -X hardcopy /tmp/status.txt && cat /tmp/status.txt
```

### Live status file

```bash
watch -n 30 cat /mnt/models/d5/STATUS.md
```

Updated atomically every ~60 seconds. Shows per-model progress, drive usage, speed, and ETA.

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

### Log tail

```bash
# Text log (human-readable):
tail -f /mnt/models/d5/logs/*_download.log
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

```bash
uv run archiver verify --all
# or per-tier:
uv run archiver verify --tier A
# or single model:
uv run archiver verify deepseek-ai/DeepSeek-R1
```

This performs a full SHA-256 re-hash of every file from disk and compares against the manifest.

---

## Adding a new model

1. Open `config/registry.yaml`
2. Add an entry:

```yaml
org/ModelName:
  hf_repo: org/ModelName
  commit_sha: null          # resolves latest on first download; gets pinned automatically
  tier: A                   # A / B / C / D
  priority: 1               # 1 = no token needed, 2 = gated (requires HF_TOKEN + licence acceptance)
  drive: d1                 # which drive to store on
  requires_auth: false
  licence: Apache-2.0
  notes: "One-line description"
```

3. Run `bash run.sh --dry-run` to preview
4. Run `bash run.sh --all` to download

---

## Pinning a model to a specific commit

```bash
uv run archiver pin deepseek-ai/DeepSeek-R1 <commit-sha>
```

This writes the commit SHA into `config/registry.yaml`. Future runs will download this exact commit and skip the HF API resolution step.

The commit SHA is also resolved and pinned automatically on first download — subsequent dry-runs will show the resolved SHA.

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

## VPN for ISP throttling

If your ISP throttles HuggingFace downloads, use OpenVPN with Surfshark (or any provider that supplies `.ovpn` configs). Use a server near you (e.g. **us-nyc** for NYC/US East, **nl-ams** for EU).

```bash
# Connect — use us-nyc for NYC/US East; nl-ams for EU (configs in /etc/openvpn/client/surfshark/)
sudo openvpn --config /etc/openvpn/client/surfshark/us-nyc.prod.surfshark.com_udp.ovpn \
             --auth-user-pass /etc/openvpn/client/surfshark.auth \
             --daemon --log /var/log/surfshark-openvpn.log

# Verify tunnel is active:
curl -s https://ipinfo.io | grep -E '"ip"|"org"'
# Should show VPN provider (e.g. "AS9009 M247 Europe SRL"), not your ISP

# Stop VPN:
sudo pkill openvpn
```

Auto-start: **MX Linux (sysvinit)** — `sudo service openvpn-surfshark start|stop|status` or `sudo /etc/init.d/openvpn-surfshark start` (see [DEPLOYMENT.md](DEPLOYMENT.md)). **Artix/dinit** — `sudo dinitctl start openvpn-surfshark`.

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

### Scratch audit (`.tmp` trees vs `run_state` + verified installs)

Large partial downloads live under ``<drive>/.tmp/<org_ModelName>/`` (same path the downloader uses for aria2 resume). To see **what is already verified on disk** (``manifest.json`` + ``.sha256`` sidecars), **``run_state.json`` status**, and whether scratch is **reclaimable** after a complete install:

```bash
cd model-archival
uv run archiver audit-tmp
```

Outputs (on **D3** infra, same tree as ``run_state.json``):

- ``logs/TMP-SCRATCH-AUDIT.json`` — full structured snapshot for scripts
- ``logs/TMP-SCRATCH-AUDIT.md`` — human-readable tables

Optional: remove only rows classified ``reclaimable_tmp`` (after you confirm the listed manifest paths):

```bash
uv run archiver audit-tmp --delete-reclaimable        # dry-run list
uv run archiver audit-tmp --delete-reclaimable --apply
```

The audit merges ``config/registry.yaml``, ``registry-specialists.yaml``, ``registry-legacy.yaml``, and ``registry_high_risk.yaml`` for **id → drive** lookup.

On a machine **without** ``/mnt/models/d3`` mounted, pass a writable output root (JSON/MD still reflect whatever drives exist):

```bash
uv run archiver audit-tmp --infra /tmp/archiver-audit-out
```

### Failed download registry (classify `run_state.json` + historical run reports)

Builds **`config/failed-models-registry.yaml`** and **`docs/FAILED_MODEL_REGISTRY.md`** from:

1. **`run_state.json`** — models with `status: failed` (and optional `skipped`).
2. **`run-report-*.md`** under **`<run_state_dir>/logs/`** (and any **`--reports-dir`**) — same format as `RunReport` (`record_model_fail`, verification ✗ blocks, optional skips).

Merges **`registry*.yaml`** for tier / `hf_repo` / `requires_auth`. Each row has **`primary_source`**: `run_state` vs `run_report`, plus **`historical_incidents`** (deduped events from reports, newest first by filename timestamp). Models that **no longer** have `failed` in `run_state` but appear in old reports are included as **`historical_only: true`** (e.g. later completed or pending).

| Category | Meaning |
|----------|---------|
| `disk_space` | ENOSPC / no space left on device |
| `unavailable` | Repo or asset not found (404, resolve errors) |
| `auth` | 401/403, gated repo, access denied |
| `failed_shards` | aria2 / hub retries exhausted (shards, transport) |
| `verify` | Checksum / verification section marked failed in a run report |
| `other` | Does not match the above |
| `skipped_gated` | `status=skipped` in run_state and/or skip lines in run reports (with `--include-skipped`) |

```bash
cd model-archival
uv run archiver failed-registry
uv run archiver failed-registry --include-skipped
uv run archiver failed-registry --no-historical   # run_state only
uv run archiver failed-registry --reports-dir /path/to/extra/logs  # plus default <state>/logs
# custom paths:
uv run archiver failed-registry --state /mnt/models/d3/run_state.json --out-yaml /tmp/failed.yaml --no-md
```

### Re-mount after reboot

Drives are in `/etc/fstab` (UUID-based, `nofail`) and mount automatically. If they don't:

```bash
sudo bash /home/x/dev/model-archival/deploy/vm-mount-disks.sh
# verify:
mount | grep /mnt/models
```

### If a drive needs fsck (filesystem corruption after unclean shutdown)

```bash
# Drive must be unmounted first
sudo fsck.ext4 -y /dev/sdXN
# Then remount:
sudo mount /mnt/models/dN
```

### If a drive was replaced

1. Run `sudo bash deploy/vm-mount-disks.sh --wipe` to format and mount the new drive
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

Re-run `bash run.sh --all` — the downloader picks up from the last complete file thanks to `.sha256` sidecar checks and aria2 resume. No manual state editing required in most cases.

To manually reset a single model:
```bash
# Edit run_state.json and set status back to "pending":
nano /mnt/models/d5/run_state.json
```

### Checksum failure after download

The downloader automatically removes the corrupt file (and its `.aria2` control file) and marks the model for retry. On next run it re-downloads only the failed files from scratch.

### STATUS.md not updating

```bash
ls -la /mnt/models/d5/STATUS.md
# Should be writable:
touch /mnt/models/d5/STATUS.md
```

If D5 is full:

```bash
df -h /mnt/models/d5
ls -lh /mnt/models/d5/logs/
# Remove old logs if needed:
find /mnt/models/d5/logs/ -name "run-report-*.md" -mtime +30 -delete
```

### HF 401 / 403 on a gated model

1. Check the token is set: `echo $HF_TOKEN`
2. Verify access on huggingface.co for the specific model (must accept terms per-model)
3. Re-run `bash deploy/sethfToken.sh hf_NEWTOKEN` if the token changed
4. The downloader will not retry 401/403 — it immediately marks the model `skipped` and moves on

### LFS URL expired (0-byte file or connection reset)

This is handled automatically — the downloader calls `hf_hub_url()` to get a fresh CDN URL before each download attempt. Simply re-run `bash run.sh --all`.

### ISP throttling / low bandwidth

Use a VPN — see the VPN section above. Confirmed to improve throughput by ~50% on throttled connections.

### Network timeout / rate limiting (HTTP 429)

The downloader has exponential backoff with jitter, up to 5 retries (delays: 30s, 60s, 120s, 300s, 600s). If HuggingFace is rate-limiting:

```bash
# Cap bandwidth to reduce request rate:
bash run.sh --all --bandwidth-cap 100
```

### Disk full mid-download

The downloader detects `ENOSPC` and the model is marked `failed`. The partial `.tmp` file is left in place (aria2 can resume it if space is freed). After freeing space or adding a drive:

```bash
bash run.sh --all
```

### aria2c daemon not responding

```bash
pkill aria2c
bash run.sh --all
```

---

## Maintenance tasks

### Rotate old logs

```bash
find /mnt/models/d5/logs/ -name "*_download.log" -mtime +30 -delete
find /mnt/models/d5/logs/ -name "run-report-*.md" -mtime +60 -delete
```

### Replicate metadata to all drives

The archiver replicates **`d3/archive/`** (manifests, global index, metadata snapshots) to **`d1/archive/`**, **`d2/archive/`**, and **`d5/archive/`** automatically after each model completes. To trigger the same sync without a download, call `archiver.state.sync_archive` from a short `uv run python` snippet (primary = `<d3>/archive`, replicas = d1/d2/d5 mount points from `drives.yaml`).

### Upgrade a model to a newer version

1. Set `commit_sha: null` in `config/registry.yaml` to unpin (or set a new SHA)
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
    .tmp/                             in-progress LFS downloads (aria2 resume files here)
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
          latest -> abc123def456.../  symlink to most recent commit

  d5/
    STATUS.md                         live status page (updated every ~60s)
    run_state.json                    persistent per-model download state
    archive/
      checksums/
        global_index.jsonl            append-only checksum ledger (all models, all drives)
    logs/
      <ts>_download.log               structured text log
      run-report-<ts>.md              session Markdown report

/home/x/dev/model-archival/
  .archiver.pid                       PID of running archiver (written by run.sh, used by stop.sh)
  run-report-<ts>.md                  orchestrator-level report (run.sh output)
```
