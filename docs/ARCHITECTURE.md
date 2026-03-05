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
  scheduler.py         priority queue + per-drive worker threads
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
  └── scheduler.submit(model)
        └── [drive worker thread]
              └── downloader.download_model(model, run_report)
                    ├── _check_manifest_complete()    ← fast path: skip HF API if already done
                    ├── hf_api.list_repo_tree()        ← resolve file list + storage backends
                    ├── hf_api.get_commit()            ← pin commit SHA
                    │
                    ├── [for each LFS file]
                    │     ├── hf_api.get_paths_info()  ← get fresh CDN URL (expires ~8 hours)
                    │     └── aria2c.download(url, dest=d1/.tmp/<hash>)
                    │           └── on complete: mv to final path
                    │
                    ├── [for each XET/direct file]
                    │     └── hf_hub_download()        ← native HF lib handles XET protocol
                    │
                    ├── verifier.compute_sha256()      ← hash each file
                    ├── verifier.write_manifest()      ← manifest.json
                    ├── verifier.append_global_index() ← global_index.jsonl (append-only)
                    ├── verifier.write_descriptor()    ← DESCRIPTOR.json + DESCRIPTOR.md
                    └── _post_verify()                 ← cross-check sidecar vs manifest
```

### Storage backend detection

HuggingFace uses two storage backends:

| Backend | Detection | Download method | Resumable |
|---------|-----------|-----------------|-----------|
| LFS | `lfs_sha256` field present in file metadata | `aria2c` via fresh CDN URL | Yes (`.aria2` control file) |
| XET | `xet_hash` field present | `huggingface_hub.hf_hub_download()` | Partial (HF lib handles) |
| Direct | Neither field | `huggingface_hub.hf_hub_download()` | No (re-downloads) |

`aria2c` is used exclusively for LFS because:
- LFS CDN URLs are plain HTTPS, compatible with aria2's multi-connection engine
- `.aria2` control files allow byte-accurate resume across crashes
- Authorization headers must NOT be forwarded to CDN (aria2's default cross-origin behaviour is correct)

XET uses a custom binary protocol that `aria2c` cannot speak. The HF Python library handles it natively.

### Temporary directory

All in-progress downloads land in `D1/.tmp/<sha256-partial>`. On completion, the file is `mv`-renamed to its final path on the correct drive. This means:
- Partial files never appear in the model directory
- A crash leaves a `.tmp` entry that aria2 can resume
- The root SSD is never written to

---

## Idempotency and resume logic

Three layers, checked in order:

1. **Manifest complete check** (`_check_manifest_complete`):  
   If `manifest.json` exists, lists the expected files, and every corresponding `.sha256` sidecar exists on disk → skip the entire HF API call and return immediately. This is the fast path for already-archived models.

2. **File-level skip** (inside the download loop):  
   For each file, if `<final_path>.sha256` exists → skip aria2/hf_hub call entirely.

3. **aria2c resume** (for LFS files in flight):  
   If `d1/.tmp/<file>.aria2` exists, aria2c continues from the last byte rather than restarting.

---

## Concurrency model

```
main thread
  └── scheduler
        ├── D1 worker thread  → download_model() calls, serialized within D1
        ├── D2 worker thread  → download_model() calls, serialized within D2
        ├── D3 worker thread  → ...
        └── D5 worker thread  → ...
```

- Models assigned to different drives download in parallel
- Models assigned to the same drive download sequentially (avoids seek thrashing)
- Bandwidth is sampled via `psutil.net_io_counters()` every 5 s; if total throughput < threshold, additional downloads may be scheduled

The scheduler uses a priority queue (`heapq`): P1 (token-free) models are dequeued before P2 (gated) models.

---

## Integrity system

### Per-file

Each downloaded file gets a `.sha256` sidecar:

```
model_dir/
  config.json
  config.json.sha256        ← hex digest only, one line
  model-00001-of-00003.safetensors
  model-00001-of-00003.safetensors.sha256
  ...
```

### Per-model

`manifest.json` captures the full state of a downloaded model version:

```json
{
  "model_id": "deepseek-ai/DeepSeek-R1",
  "commit_sha": "abc123...",
  "downloaded_at": "2026-03-04T17:38:00Z",
  "total_size_bytes": 1234567890,
  "files": {
    "model-00001.safetensors": {
      "sha256": "abc...",
      "size_bytes": 1234567,
      "lfs_oid": "sha256:...",
      "storage": "lfs"
    }
  }
}
```

### Global index

`D5/global_index.jsonl` is append-only — one JSON line per file, written at download time:

```json
{"ts": "2026-03-04T17:38:00Z", "model_id": "...", "file": "...", "sha256": "...", "size": 1234}
```

This file survives even if `manifest.json` on the model's drive is corrupted or lost.

### Descriptor files

Each model directory also contains:
- `DESCRIPTOR.json` — machine-readable provenance (id, commit SHA, tier, drive, date, size)
- `DESCRIPTOR.md` — human-readable provenance (readable without any tooling)

These allow identification and verification of an archived model even if the project codebase is unavailable.

---

## State and logging

| File | Location | Purpose |
|------|----------|---------|
| `run_state.json` | `D5/` | Persistent per-model status: `pending`, `in_progress`, `complete`, `failed` |
| `STATUS.md` | `D5/` | Human-readable status page, updated every ~60 s atomically |
| `archiver-<ts>.log` | `D5/logs/` | Structured text log with box-drawing style messages |
| `archiver-<ts>.jsonl` | `D5/logs/` | Machine-readable structured log (one JSON per event) |
| `run-report-<ts>.md` | `D5/logs/` | Incremental Markdown session report (RunReport class) |
| `global_index.jsonl` | `D5/` | Append-only checksum ledger |

`STATUS.md` is written atomically: write to `.STATUS.md.tmp`, then `os.replace()` — never a partial file visible to readers.

---

## Configuration

### `config/registry.yaml`

Source of truth for all models. Each entry:

```yaml
deepseek-ai/DeepSeek-R1:
  hf_repo: deepseek-ai/DeepSeek-R1
  commit_sha: null          # null = always resolve latest; set to pin
  tier: A
  priority: 1
  drive: d1
  auth_required: false
  license: MIT
  description: "..."
  tags: [reasoning, open-weights]
```

`commit_sha: null` resolves to the current HEAD on first download, then gets pinned in `run_state.json`.

### `config/drives.yaml`

```yaml
d1:
  mount_point: /mnt/models/d1
  label: "6TB WD Red"
  tmp_dir: /mnt/models/d1/.tmp

d5:
  mount_point: /mnt/models/d5
  label: "1TB SSD"
  roles: [metadata, logs, state]
```

---

## Bash script structure

```
deploy/
  _common.sh              shared library: colors, logging, run_cmd, Markdown reporting
  setup-mxlinux.sh        Debian/MX Linux OS dependency installer
  setup-artix.sh          Artix/Arch Linux OS dependency installer
  vm-mount-disks.sh       disk identification, partitioning, formatting, fstab
  proxmox-attach-disks.sh Proxmox HDD → VM SCSI passthrough
  verify-environment.sh   pre-run environment and drive audit
  fix-apparmor-cursor.sh  Cursor Remote SSH AppArmor fix
  sethfToken.sh           safe HF token storage

scripts/
  archiver-download.sh    thin wrapper → uv run archiver download
  archiver-verify.sh      thin wrapper → uv run archiver verify
  archiver-status.sh      thin wrapper → uv run archiver status
  archiver-drives.sh      thin wrapper → uv run archiver drives status
  archiver-list.sh        thin wrapper → uv run archiver list
  check-environment.sh    thin wrapper → deploy/verify-environment.sh
  verify-archive.sh       thin wrapper → verification/verify-archive.py

verification/
  verify-archive.py       standalone integrity verifier (stdlib only)
  verification-reports/   verify-report-<ts>.md files
```

All deploy scripts source `_common.sh` for:
- Colored timestamped console output
- `run_cmd` wrapper (captures exit code, logs pass/fail)
- Incremental Markdown report accumulation (`init_report`, `_rpt`, `flush_report`)

---

## Security considerations

- `~/.hf_token` — chmod 600, never in the project repo, never in shell history when set via `sethfToken.sh`
- `.gitignore` covers `*.token`, `.hf_token`, `.env`, `run-report-*.md`, `verification-reports/`
- HF token is redacted in all Markdown reports (`<redacted>` substitution in RunReport)
- `aria2c` is called with `--no-conf` to prevent user config interference
- LFS CDN URLs contain short-lived HMAC signatures; they are never logged
