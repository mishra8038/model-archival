# model-archival / colab — Regeneration Prompt

**Version:** 1.0 — 2026-03-05  
**Purpose:** Feed this file to a Cursor AI agent to fully restore project context for the `colab/` subproject. The agent should be able to troubleshoot, extend, or resume work without any prior transcript.

---

## 1. What this project is

`model-archival` is a system to systematically download, verify, and archive the weights of major open-source LLMs/LRMs from HuggingFace for permanent offline storage.

The repo has **two independent archival strategies**:

| Folder | Strategy |
|--------|----------|
| `local/` | Python archiver (`uv` project) — downloads to physical HDDs on a Linux VM via `aria2c` |
| `colab/` | **THIS PROJECT** — Google Colab notebooks stream weights directly to Google Drive (10 TB quota) |

Both strategies share the same model registry (`local/config/registry.yaml`) and produce identical `manifest.json` / `.sha256` sidecar formats, so archives from either source are cross-verifiable.

---

## 2. Why Colab

The Colab strategy downloads **cloud-to-cloud**: HuggingFace → Google's datacenter network → Google Drive. The user's home internet connection carries only the browser UI — not the model weights. This is significantly faster than downloading to a local machine.

The tradeoff is Colab's 24-hour session limit. The notebook is fully resumable — each new session picks up exactly where the last stopped.

---

## 3. Environment

### Google account
- `mishra8038@gmail.com`
- Google Drive quota: 10 TB available

### HuggingFace token
- Stored as a Colab Secret named `HF_TOKEN`
- Required for gated models: Llama (Meta), Gemma (Google), Mistral Large, Phi-4 (Microsoft)
- Token-free models (DeepSeek, Qwen, all Tier C GGUF, all Tier D uncensored) work without it
- Token also stored at `~/.hf_token` on local machines; auto-loaded by deployment scripts

### Development machine
- `/home/x/dev/model-archival/` on a Debian trixie workstation (SysV init)
- GitHub: `github.com/mishra8038/model-archival`

### Colab local runtime target machine
- MX Linux 23.6 (Debian bookworm-based, SysV init — **not systemd**)
- Remote access via SSH
- Docker CE installed (v26), daemon start currently failing — see Section 9

---

## 4. Repository layout

```
model-archival/
  colab/
    archiver.ipynb              main download notebook (9 cells)
    setup.ipynb                 one-time setup: token check, copy lib to Drive
    lib/
      downloader.py             download engine
    local-tools/
      setup-mxlinux-colab.sh   deploy Docker + Colab runtime on MX Linux 23
      setup-alpine-colab.sh    deploy Docker + Colab runtime on Alpine/OpenRC
      setup-docker-runtime.sh  generic Debian/Ubuntu script (updated for SysV)
      keep-alive.py            Selenium keep-alive for hosted Colab (fallback)
      requirements.txt         pip deps for keep-alive
    docs/
      PROJECT_PROMPT.md        full architecture doc
      REGENERATION_PROMPT.md   THIS FILE
      TROUBLESHOOTING.md       fixes for known issues
    chat/
      2026-03-05-colab-setup.md  session notes
    config/                    (empty — uses local/config/registry.yaml)
    README.md
  local/                       separate HDD-based archiver (see local/docs/)
```

---

## 5. Notebook structure (`archiver.ipynb`)

| Cell | ID | Purpose |
|------|-----|---------|
| 1 | `config` | User-editable: `DRIVE_ROOT`, `TIERS`, `MAX_PRIORITY`, `DRY_RUN`, session limits |
| 2 | `setup` | pip upgrade `huggingface_hub`, load `HF_TOKEN` from Colab Secrets or env |
| 3 | `mount_drive` | `drive.mount()` with retry + Drive free-space check; sets `DRIVE_PATH`, `STATE_FILE`, `INDEX_FILE`, `LOG_DIR` |
| 4 | `load_lib` | Imports `downloader.py` from Drive/repo, loads/inits `run_state.json`, creates `SessionGuard` |
| 5 | `load_registry` | Loads `local/config/registry.yaml`, builds ordered download queue |
| 6 | `run_downloads` | **Main cell** — per-model loop with progress bar, Drive health check, session guard, state save |
| 7 | `quick_resume` | Restart downloads after kernel reset without re-running cells 2–5 |
| 8 | `verify` | Cross-check `.sha256` sidecars vs `manifest.json`; optional full re-hash |
| 9 | `status` | Per-model status table, Drive free space, recent session log list |

### Key configuration variables (Cell 1)
```python
DRIVE_ROOT         = "/content/drive/MyDrive/model-archive"
TIERS              = ['C', 'D']   # start small; change to ['A','B','C','D'] for all
MAX_PRIORITY       = 2            # 1=token-free only, 2=include gated
SPECIFIC_MODELS    = []           # override to target specific model IDs
SESSION_WARN_HOURS = 1.5          # stop queuing this many hours before session limit
DRY_RUN            = False
SESSION_LIMIT_HOURS= 24
```

---

## 6. Downloader design (`lib/downloader.py`)

### Dependencies
- `huggingface_hub` — all downloads (no `aria2c`; not available in Colab)
- `hashlib`, `json`, `pathlib`, `shutil` — stdlib only beyond HF hub

### Resume layers (checked in order)
1. **Model-level state**: `run_state.json` — if `state[model_id] == "complete"`, skip entirely
2. **Manifest complete check**: if `manifest.json` exists and all `.sha256` sidecars present → skip
3. **File-level sidecar**: if `<file>.sha256` exists → skip that file
4. **Per-file checkpoint**: `.file_state.json` inside model dir — written atomically after every file; crash-safe

### `SessionGuard` class
Tracks elapsed wall-clock time since kernel start. Passed into `download_model()`.
When `remaining_hours() <= warn_hours`: stops queuing new models, logs warning.
Current model completes cleanly; no file is abandoned mid-transfer.

### Key function signature
```python
download_model(
    model_id: str,
    dest_root: Path,
    hf_token: Optional[str] = None,
    tier: str = "A",
    quant_levels: Optional[list[str]] = None,
    global_index_path: Optional[Path] = None,
    state: Optional[dict] = None,
    save_state_fn: Optional[Callable] = None,
    session_guard: Optional[SessionGuard] = None,
    on_file_progress: Optional[Callable] = None,
) -> ModelResult
```

### File layout on Drive
```
DRIVE_ROOT/
  run_state.json              model-level status dict (persists across sessions)
  global_index.jsonl          append-only per-file checksum ledger
  logs/
    session-<ts>.md           written after each session
    verify-report-<ts>.md     written by Cell 8
  <org>/<model>/<commit[:12]>/
    <filename>
    <filename>.sha256         one hex digest per file
    manifest.json             compatible with local/ archiver format
    DESCRIPTOR.json           machine-readable provenance
    DESCRIPTOR.md             human-readable provenance
    .file_state.json          internal checkpoint (not part of archive)
```

---

## 7. Model registry

Shared YAML at `local/config/registry.yaml`. `setup.ipynb` copies it to Drive.

| Tier | Description | Format | ~Total size |
|------|-------------|--------|------------|
| A | Raw BF16 general/reasoning (DeepSeek, Qwen, Llama, Gemma, Mistral, Phi) | safetensors | ~4.3 TB |
| B | Raw BF16 code models (DeepSeek-Coder, Qwen-Coder, Codestral) | safetensors | ~0.9 TB |
| C | Quantized GGUF (Q4_K_M or Q8_0, bartowski/unsloth) | .gguf | ~0.4 TB |
| D | Uncensored/abliterated variants (huihui-ai, mlabonne, Dolphin) | safetensors + GGUF | ~0.5 TB |

Priority 1 = token-free. Priority 2 = gated (requires accepted HF licence per model).

**Recommended download order:** C → D → B → A(P1) → A(P2)

---

## 8. Docker local runtime

For no-session-limit operation: run the official Colab Docker image on a local machine. Colab's browser UI connects to it. Downloads: HuggingFace → local machine → Drive.

**Image:** `us-docker.pkg.dev/colab-images/public/runtime` (~8–10 GB, cached after first pull)

**Container run command:**
```bash
docker run -d \
  --name colab-runtime \
  --restart=unless-stopped \
  -p 127.0.0.1:9000:8080 \
  --memory=4g --cpus=2 \
  -e HF_TOKEN="hf_..." \
  us-docker.pkg.dev/colab-images/public/runtime
```

**Get connection URL:**
```bash
bash ~/colab-url.sh
# or manually:
docker logs colab-runtime 2>&1 | grep -oP 'http://127\.0\.0\.1:\d+/\?token=\S+' | tail -1 | sed 's/8080/9000/'
```

**SSH tunnel (required when container is on a remote machine):**
```bash
ssh -L 9000:127.0.0.1:9000 user@<remote-ip> -N
# Then paste http://127.0.0.1:9000/?token=... into Colab
```

**In Colab:** Connect ▾ → Connect to a local runtime → paste URL

---

## 9. Current issue — Docker daemon on MX Linux 23

### Status: UNRESOLVED — under active investigation

### What was done
`setup-mxlinux-colab.sh` ran on the MX Linux 23 target machine and:
- ✅ Installed Docker CE v26 from Docker's official bookworm apt repo
- ✅ Added user to docker group
- ❌ Failed to start Docker daemon via `/etc/init.d/docker start`

### Error
```
ERROR: Docker daemon failed to start
Could not start Docker. Check: sudo /etc/init.d/docker start
```

### MX Linux 23 specifics
- Based on Debian bookworm
- Uses **SysV init** (not systemd — `systemctl` commands do not work)
- Ships **nftables** by default — this conflicts with Docker CE which expects iptables-legacy
- Init PID 1: `/sbin/init → ../lib/sysvinit/init`

### Diagnostic commands to run
```bash
# 1. Get the actual daemon error
sudo dockerd 2>&1 | head -40

# 2. Try starting containerd first (Docker depends on it)
sudo /etc/init.d/containerd start
sudo /etc/init.d/docker start

# 3. Check kernel modules
lsmod | grep -E "overlay|br_netfilter"

# 4. Check syslog
sudo tail -30 /var/log/syslog | grep -i docker
```

### Most likely fix — iptables-legacy
```bash
sudo apt-get install -y iptables
sudo update-alternatives --set iptables /usr/sbin/iptables-legacy
sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy
sudo /etc/init.d/docker start
```

### Second likely fix — load kernel modules
```bash
sudo modprobe overlay
sudo modprobe br_netfilter
echo -e "overlay\nbr_netfilter" | sudo tee -a /etc/modules
sudo /etc/init.d/docker start
```

### If dockerd output shows "permission denied" on cgroup
```bash
sudo mkdir -p /sys/fs/cgroup/docker
sudo /etc/init.d/docker start
```

---

## 10. How to connect Colab once Docker is working

1. Run `bash ~/colab-url.sh` on the MX machine → copy the URL
2. On your local machine: `ssh -L 9000:127.0.0.1:9000 user@<mx-ip> -N &`
3. Open `https://colab.research.google.com`
4. Open `archiver.ipynb` (File → Open → GitHub → mishra8038/model-archival)
5. Click **Connect ▾** → **Connect to a local runtime**
6. Paste the URL → Connect
7. Run `setup.ipynb` once to copy library files to Drive
8. Run `archiver.ipynb` → Runtime → Run all

---

## 11. Deployment scripts

| Script | Target | What it does |
|--------|--------|-------------|
| `colab/local-tools/setup-mxlinux-colab.sh` | MX Linux 23 (SysV) | Docker CE + Colab runtime, helper scripts |
| `colab/local-tools/setup-alpine-colab.sh` | Alpine (OpenRC) | Docker + Colab runtime, helper scripts |
| `colab/local-tools/setup-docker-runtime.sh` | Generic Debian/Ubuntu | Original script, updated for SysV detection |

All scripts:
- Accept `--hf-token hf_xxx` and `--port 9000` arguments
- Load token from `~/.hf_token` if not passed as argument
- Write a timestamped Markdown report to `~/`
- Create `~/colab-url.sh` and `~/colab-status.sh` helper scripts

**SCP and run pattern:**
```bash
scp colab/local-tools/setup-mxlinux-colab.sh user@<ip>:~/
ssh user@<ip> "bash ~/setup-mxlinux-colab.sh --hf-token hf_TOKEN"
```

---

## 12. First-time Colab workflow (once Docker is running)

```
1. setup.ipynb         — run once to copy lib/ and registry.yaml to Drive
2. archiver.ipynb      — run each session
   Cell 1: set TIERS = ['C', 'D'] for first session
   Cell 6: downloads run, state saved after every file
   Close browser (Pro+: enable background execution first)
3. Next session:
   Re-open archiver.ipynb → Runtime → Run all
   Picks up automatically from run_state.json on Drive
```

---

## 13. Key file paths (runtime)

| File | Location | Purpose |
|------|----------|---------|
| `run_state.json` | `DRIVE_ROOT/` | Model-level download state |
| `global_index.jsonl` | `DRIVE_ROOT/` | Append-only checksum ledger |
| `registry.yaml` | `DRIVE_ROOT/model-archival/local/config/` | Copied here by setup.ipynb |
| `downloader.py` | `DRIVE_ROOT/model-archival/colab/lib/` | Copied here by setup.ipynb |
| `~/colab-url.sh` | MX machine home | Retrieve Docker runtime URL |
| `~/colab-status.sh` | MX machine home | Container health check |
