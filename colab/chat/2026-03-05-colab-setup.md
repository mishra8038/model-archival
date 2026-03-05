# Colab Project Build — 2026-03-05

## Summary

Built the Google Colab / Google Drive archival system as a second strategy alongside the local HDD archiver in `local/`.

---

## Decisions made

### Architecture
- **Hosted Colab (not local Docker) is the fastest download path** — Google's servers download HuggingFace → Drive directly, bypassing the user's home internet connection
- Local Docker runtime useful for no-session-limit operation but bottlenecked by home ISP uplink
- GCP VM option considered and rejected (adds cost); settled on free hosted Colab with full resume support
- Alpine VM with XFCE considered for persistent headless Docker host; deferred — MX Linux machine used instead

### Download strategy
- Fire-and-forget: start session once per day, resume is automatic via `run_state.json` on Drive
- Per-file checkpointing (`.file_state.json`) so a crash wastes at most one file
- `SessionGuard` class stops queuing new models with 1.5h remaining in 24h session limit
- Drive auto-reconnect if mount drops mid-session

### Colab notebook structure (`archiver.ipynb`)
- 9 cells: config → deps → mount → load lib → registry → **run downloads** → quick resume → verify → status
- Cell 7 (Quick Resume) allows restarting just downloads after kernel restart without re-running setup
- `ipywidgets.IntProgress` progress bar per model
- Session log written to Drive after each session (`logs/session-<ts>.md`)

### Credentials
- HF token stored as Colab Secret (`HF_TOKEN`) — never in notebook output
- Google Drive mounted via standard OAuth popup — no service account needed
- Token auto-loaded from `os.environ` fallback for local Docker runtime

### File layout on Drive
```
MyDrive/model-archive/
  run_state.json          model-level state (pending/in_progress/complete/failed)
  global_index.jsonl      append-only checksum ledger
  logs/
    session-<ts>.md
    verify-report-<ts>.md
  <org>/<model>/<commit>/
    manifest.json         compatible with local/ archiver format
    DESCRIPTOR.json / .md
    <files> + .sha256 sidecars
    .file_state.json      per-file checkpoint
```

### Local Docker runtime
- Official image: `us-docker.pkg.dev/colab-images/public/runtime` (~8–10 GB)
- Connect via: Colab → Connect ▾ → Connect to a local runtime → paste URL
- URL changes on container restart — use `~/colab-url.sh` to retrieve it
- `--restart=unless-stopped` for persistence

---

## Files created

| File | Purpose |
|------|---------|
| `colab/archiver.ipynb` | Main download notebook (9 cells) |
| `colab/setup.ipynb` | One-time setup: token check, copy lib to Drive, access audit |
| `colab/lib/downloader.py` | Download engine: HF → Drive, SHA-256, per-file checkpoint, SessionGuard |
| `colab/local-tools/setup-mxlinux-colab.sh` | Deploy Docker + Colab runtime on MX Linux 23 (SysV init) |
| `colab/local-tools/setup-alpine-colab.sh` | Deploy Docker + Colab runtime on Alpine Linux (OpenRC) |
| `colab/local-tools/setup-docker-runtime.sh` | Generic Docker runtime setup (Debian/Ubuntu, updated for SysV) |
| `colab/local-tools/keep-alive.py` | Selenium keep-alive for hosted Colab (fallback) |
| `colab/local-tools/requirements.txt` | pip deps for keep-alive |
| `colab/docs/` | Project documentation |
| `colab/README.md` | Usage guide, credential requirements, file layout |

---

## MX Linux Docker deployment — in progress

### Problem
`setup-mxlinux-colab.sh` ran successfully through Docker CE installation but failed at service start:
```
ERROR: Docker daemon failed to start
Could not start Docker. Check: sudo /etc/init.d/docker start
```

### Likely causes (to investigate)
1. `containerd` not started before Docker
2. iptables/nftables conflict (MX Linux 23 ships nftables; Docker CE expects iptables-legacy)
3. Kernel overlay module not loaded

### Diagnostic commands to run on the MX machine
```bash
sudo /etc/init.d/containerd start 2>&1
sudo /etc/init.d/docker start 2>&1
sudo dockerd 2>&1 | head -30
```

### Status
**Pending** — user to reconnect from remote host for live troubleshooting.

---

## Pending / next steps

- [ ] Resolve Docker daemon startup failure on MX Linux 23
- [ ] Get Colab connection URL from MX machine
- [ ] Connect `archiver.ipynb` to local runtime
- [ ] Run `setup.ipynb` to copy lib files to Drive
- [ ] Start first download session (recommend starting with Tier C/D)
