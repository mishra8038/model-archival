# Architecture

Design decisions, module breakdown, and data flows for the model-archival system.

---

## Goals and constraints

- **Fidelity** — raw BF16/FP16 weights only for Tier A/B; no server-side conversion
- **Integrity** — every byte verifiable after download, independently and without this software
- **Resilience** — crash/restart at any point must not require re-downloading intact files
- **Unattended** — zero interactive input once started; all failures logged, retried, or reported
- **Portability** — metadata, manifests, and `.sha256` sidecars survive if this codebase is lost
- **Storage isolation** — no model data on root SSD; all writes to known mount points

---

## Python package layout

```
src/archiver/
  __init__.py          version string
  cli.py               click entry points — all user-facing commands
  models.py            ModelEntry / DriveConfig dataclasses + registry I/O
  downloader.py        per-model download orchestration
  scheduler.py         per-drive worker threads + signal handling
  aria2_manager.py     aria2c daemon lifecycle + aria2p RPC wrapper
  verifier.py          SHA-256, manifest.json, global_index.jsonl, DESCRIPTOR files
  state.py             run_state.json persistence + archive replication
  preflight.py         pre-flight checks (tools, drives, HF token, network)
  status.py            rich console display + STATUS.md + RunReport
```

---

## Download pipeline (per model)

```
cli.download()
  └── scheduler.run()
        └── [drive worker thread]
              └── downloader.download_model(model, run_report)
                    ├── _check_manifest_complete()    ← fast path: skip HF API if already done
                    ├── hf_api.repo_info(files_metadata=True)  ← file list + storage backend
                    ├── pin commit SHA from API response
                    │
                    ├── [for each LFS file]
                    │     ├── hf_hub_url()             ← fresh CDN URL (re-fetched per attempt,
                    │     │                               HF pre-signed tokens expire ~1 hour)
                    │     └── aria2c.add_download()    ← resumable, 8 connections, 32 MB pieces
                    │           └── on complete: sha256 verify → mv to final path → write sidecar
                    │
                    ├── [for each XET/direct file]
                    │     └── hf_hub_download()        ← native HF lib handles XET protocol
                    │           └── on complete: sha256 verify → mv to final path → write sidecar
                    │
                    ├── verifier.write_manifest()      ← manifest.json
                    ├── verifier.append_global_index() ← global_index.jsonl (append-only)
                    ├── verifier.write_descriptor()    ← DESCRIPTOR.json + DESCRIPTOR.md
                    └── _post_verify()                 ← full SHA-256 re-hash of all files
```

### Storage backend detection

HuggingFace uses two storage backends:

| Backend | Detection | Download method | Resumable |
|---------|-----------|-----------------|-----------|
| LFS | `lfs` field present in file metadata from `repo_info()` | `aria2c` via fresh CDN URL | Yes (`.aria2` control file) |
| XET | No `lfs` field + file > 10 MB | `huggingface_hub.hf_hub_download()` | Partial (HF lib manages `.incomplete/` cache) |
| Direct | No `lfs` field + file ≤ 10 MB | `huggingface_hub.hf_hub_download()` | No (re-downloads on restart) |

`aria2c` is used exclusively for LFS because:
- LFS CDN URLs are plain HTTPS, compatible with aria2's multi-connection engine
- `.aria2` control files allow byte-accurate resume across crashes
- Authorization headers must NOT be forwarded to CDN (aria2's default cross-origin behaviour is correct)

XET uses a custom binary protocol that `aria2c` cannot speak. The HF Python library handles it natively.

### Temporary directory

All in-progress LFS downloads land in `D1/.tmp/<model_id_slug>/`. On completion the file is `shutil.move()`-renamed to its final path on the correct drive. This means:
- Partial files never appear in the model directory
- A crash leaves a `.tmp` entry that aria2 can resume on the next run
- The root SSD is never written to
- D1 is used (not D5) because it has the largest free headroom (~2.3 TB post-downloads vs 1 TB on D5)

### Orphaned partial file detection

When aria2c restarts after a crash, it requires both the partial file AND its `.aria2` control file to resume. If the control file is missing (e.g. the process was killed mid-handshake before aria2 could write it), aria2 would silently truncate the partial file to 0 bytes and restart from scratch — wasting all prior progress.

`Aria2Manager.add_download()` detects this case: if the partial file exists but its `.aria2` control file does not, the partial is removed before submission. aria2 then starts a clean download, which is safer than a silent truncation.

---

## Idempotency and resume logic

Three layers, checked in order:

1. **Manifest complete check** (`_check_manifest_complete`):  
   If `manifest.json` exists, lists the expected files, and every corresponding `.sha256` sidecar exists on disk → skip the entire HF API call and return immediately. This is the fast path for already-archived models.

2. **File-level skip** (inside the download loop):  
   For each file, if `<final_path>.sha256` sidecar exists → skip aria2/hf_hub call entirely.

3. **aria2c resume** (for LFS files in flight):  
   If `D1/.tmp/<model>/<file>.aria2` exists alongside the partial file, aria2c continues from the last byte rather than restarting.

---

## Concurrency model

```
main thread  (signal handler: SIGTERM/SIGINT → set _stop_event)
  └── DriveScheduler.run()
        ├── D1 worker thread  → download_model() calls, serialized within D1
        ├── D2 worker thread  → download_model() calls, serialized within D2
        ├── D3 worker thread  → ...
        ├── D5 worker thread  → ...
        └── bandwidth sampler thread  → EWMA speed + ETA every 10s
```

- Models assigned to different drives download in parallel (up to `--max-parallel 4`)
- Models assigned to the same drive download sequentially (avoids seek thrashing on HDD)
- Workers check `_stop_event` before starting each new model — a shutdown signal completes the current shard cleanly then exits without starting the next model
- `run_state.json` is protected by a `threading.Lock`; all writes go through an atomic `.json.tmp` → rename pattern

### Scheduler queue

The scheduler uses **one `deque` per drive** (not a heap). Models are sorted by `(priority, drive, model_id)` before being enqueued in `cli.py`, so P1 (token-free) models are always processed before P2 (gated) models within each drive.

### Signal handling and graceful shutdown

`DriveScheduler.run()` installs `SIGTERM` and `SIGINT` handlers on the main thread. On signal:
1. `_stop_event` is set
2. Each worker thread checks the event before dequeuing its next model
3. In-flight shard downloads complete normally (partial files stay intact for aria2 resume)
4. `run_state.json` is flushed with current statuses
5. The process exits cleanly

`run.sh` additionally traps SIGTERM/SIGINT at the bash level, forwards SIGTERM to the Python child process, and waits up to 5 minutes for a clean exit before force-killing. The `.archiver.pid` file in the repo root allows `stop.sh` to find the process from any terminal.

---

## Integrity system

### Per-file

Each downloaded file gets a `.sha256` sidecar:

```
model_dir/
  config.json
  config.json.sha256        ← "hex_digest  config.json\n"
  model-00001-of-00003.safetensors
  model-00001-of-00003.safetensors.sha256
  ...
```

For LFS files the SHA-256 is verified against the `lfs_sha256` field from the HF API. On mismatch, both the partial file and its `.aria2` control file are removed (the byte-range map is unreliable for corrupt data), and the download is retried from scratch.

### Per-model

`manifest.json` captures the full state of a downloaded model version:

```json
{
  "model_id": "deepseek-ai/DeepSeek-R1",
  "hf_repo": "deepseek-ai/DeepSeek-R1",
  "commit_sha": "abc123...",
  "downloaded_at": "2026-03-04T17:38:00Z",
  "total_size_bytes": 1234567890,
  "file_count": 163,
  "files": {
    "model-00001.safetensors": {
      "sha256": "abc...",
      "size_bytes": 1234567,
      "storage": "lfs"
    }
  }
}
```

After a model is complete, `_post_verify()` performs a **full SHA-256 re-hash** of every file from disk and cross-checks against the manifest. This is not a sidecar-only check — every byte is re-read.

### Global index

`D5/archive/checksums/global_index.jsonl` is append-only — one JSON line per file, written at download time:

```json
{"ts": "2026-03-04T17:38:00Z", "model_id": "...", "file": "...", "sha256": "...", "size": 1234}
```

This file survives even if `manifest.json` on the model's drive is corrupted or lost. It is replicated to all other drives via `sync_archive()` after each model completes.

### Descriptor files

Each model directory also contains:
- `DESCRIPTOR.json` — machine-readable provenance (id, commit SHA, tier, drive, date, size)
- `DESCRIPTOR.md` — human-readable provenance (readable without any tooling)

These allow identification and verification of an archived model even if the project codebase is unavailable.

---

## State and logging

| File | Location | Purpose |
|------|----------|---------|
| `run_state.json` | `D5/` | Persistent per-model status: `pending`, `in_progress`, `complete`, `failed`, `skipped` |
| `.archiver.pid` | repo root | PID of the running archiver child process (written by `run.sh`, used by `stop.sh`) |
| `STATUS.md` | `D5/` | Human-readable status page, updated every ~60 s atomically |
| `<ts>_download.log` | `D5/logs/` | Structured text log |
| `run-report-<ts>.md` | `D5/logs/` | Incremental Markdown session report (RunReport class) |
| `global_index.jsonl` | `D5/archive/checksums/` | Append-only checksum ledger |

`STATUS.md` is written atomically: write to `.STATUS.md.tmp`, then `os.replace()` — never a partial file visible to readers. Same pattern for `run_state.json` (via `.json.tmp`).

---

## Configuration

### `config/registry.yaml`

Source of truth for all models. Each entry:

```yaml
deepseek-ai/DeepSeek-R1:
  hf_repo: deepseek-ai/DeepSeek-R1
  commit_sha: null          # null = resolve latest HEAD; set to a SHA to pin
  tier: A
  priority: 1               # 1 = no token needed, 2 = gated (requires HF_TOKEN)
  drive: d1
  requires_auth: false
  licence: MIT
  notes: "..."
```

`commit_sha` is resolved from the HF API on the first download and written back to the registry file, pinning the version for all future runs.

### `config/drives.yaml`

```yaml
d1:
  mount_point: /mnt/models/d1
  role: "Raw giants (Tier A/B large models)"
  tmp_dir: /mnt/models/d1/.tmp    # in-progress LFS download scratch space

d2:
  mount_point: /mnt/models/d2
  role: "Raw mid-size (Tier A/B) + Tier D uncensored"

d3:
  mount_point: /mnt/models/d3
  role: "Quantized GGUF (Tier C/D)"

d5:
  mount_point: /mnt/models/d5
  role: "Metadata, logs, state, STATUS.md"
```

D5 hosts only metadata (run_state.json, STATUS.md, logs, global_index.jsonl). The `.tmp/` scratch space is on D1, not D5, because D1 has far more headroom.

---

## Bash script structure

```
deploy/
  _common.sh              shared library: colors, logging, run_cmd, Markdown reporting
  setup-mxlinux.sh        Debian/MX Linux OS dependency installer
  setup-artix.sh          Artix/Arch Linux (dinit) OS dependency installer
  vm-mount-disks.sh       disk identification, partitioning, formatting, fstab
  proxmox-attach-disks.sh Proxmox HDD → VM SCSI passthrough
  verify-environment.sh   pre-run environment and drive audit
  sethfToken.sh           safe HF token storage (~/.hf_token, chmod 600)

scripts/
  archiver-download.sh    thin wrapper → uv run archiver download
  archiver-verify.sh      thin wrapper → uv run archiver verify
  archiver-status.sh      thin wrapper → uv run archiver status
  archiver-drives.sh      thin wrapper → uv run archiver drives status
  archiver-list.sh        thin wrapper → uv run archiver list
  check-environment.sh    thin wrapper → deploy/verify-environment.sh
```

All deploy scripts source `_common.sh` for:
- Colored timestamped console output
- `run_cmd` wrapper (captures exit code, logs pass/fail)
- Incremental Markdown report accumulation (`init_report`, `_rpt`, `flush_report`)

---

## Security considerations

- `~/.hf_token` — chmod 600, never in the project repo, never in shell history when set via `sethfToken.sh`
- `.gitignore` covers `*.token`, `.hf_token`, `.env`, `run-report-*.md`
- HF token is redacted in all Markdown reports
- LFS CDN URLs contain short-lived HMAC signatures; they are never logged
- `aria2c` RPC secret (`archiver-local`) is localhost-only (`--rpc-listen-all=false`)
