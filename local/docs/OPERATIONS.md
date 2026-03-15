# Operations Guide

Day-to-day usage, monitoring, troubleshooting, and maintenance for the model-archival system.

---

## Starting a download run

Always run inside `screen` — downloads take hours to days and SSH sessions drop.

```bash
# Start archiver inside a named screen session
screen -S archiver bash run.sh --all

# Detach from screen (leave running):  Ctrl+A  D
# Reattach later:
screen -r archiver
```

### Common run.sh options

```bash
bash run.sh --all                   # download everything (P1 + P2, all tiers) — default
bash run.sh --dry-run               # simulate, no downloads
bash run.sh --priority-only 1       # token-free models only (no HF token needed)
bash run.sh --tier A                # Tier A only
bash run.sh --tier B                # Tier B (code models) only
bash run.sh --bandwidth-cap 200     # cap at 200 MB/s
bash run.sh --rehash                # full SHA-256 re-hash of all files after download
bash run.sh --skip-env-check        # skip environment verification (faster restart)
```

The script is fully idempotent — re-running it skips already-verified models.

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

The archiver replicates `archive/` (manifests, global index) to all non-D5 drives automatically after each model completes. To trigger manually — re-run any model with `uv run archiver download <model-id>` or wait for the next full run.

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
