# Colab Archiver — Project Prompt

Portable context document for future AI assistants working on this subproject.

---

## Mission

Archive open-source LLM/LRM weights from HuggingFace to Google Drive (10 TB quota) using Google Colab as the execution environment. Downloads happen cloud-to-cloud (HuggingFace → Google's network → Drive), bypassing the user's home internet connection.

This is the second archival strategy in the `model-archival` repo. The first (`local/`) downloads to physical HDDs on a local VM. Both strategies use the same model registry and produce compatible `manifest.json` / `.sha256` sidecar formats.

---

## Repository layout

```
model-archival/
  local/          Python archiver → physical HDDs via aria2c on VM
  colab/          THIS PROJECT — Colab notebooks → Google Drive
    archiver.ipynb        main download notebook
    setup.ipynb           one-time credential setup
    lib/
      downloader.py       download engine (no aria2c — huggingface_hub only)
    local-tools/
      setup-mxlinux-colab.sh    deploy Docker + runtime on MX Linux 23
      setup-alpine-colab.sh     deploy Docker + runtime on Alpine Linux
      setup-docker-runtime.sh   generic Debian/Ubuntu script (updated for SysV)
      keep-alive.py             Selenium keep-alive for hosted Colab (fallback)
    docs/                 this folder
    chat/                 session notes
    config/               (empty — uses local/config/registry.yaml)
    README.md
```

---

## Credentials

| Credential | Storage | Used for |
|-----------|---------|---------|
| Google account | OAuth popup in browser | Drive mount |
| HuggingFace token | Colab Secret named `HF_TOKEN` | Gated models (Llama, Gemma, Mistral Large, Phi) |

The HF token is loaded in notebook Cell 2 via `google.colab.userdata.get('HF_TOKEN')` with fallback to `os.environ.get('HF_TOKEN')` for local Docker runtime sessions.

Google account: `mishra8038@gmail.com`

---

## Execution modes

### Mode A — Hosted Colab (recommended for speed)
Downloads run on Google's servers. HuggingFace → Google datacenter → Drive.
No home internet involved. Session limit: 24h (Pro+). Fully resumable.

### Mode B — Local Docker runtime (no session limit)
Run the official Colab Docker image on a local machine (MX Linux VM).
Connect Colab's browser UI to it via "Connect to local runtime".
Downloads: HuggingFace → local machine → Drive (via mounted path).
Bottleneck: home ISP uplink. No time limit.

---

## Notebook structure (`archiver.ipynb`)

| Cell | Name | Purpose |
|------|------|---------|
| 1 | Configuration | `DRIVE_ROOT`, `TIERS`, `MAX_PRIORITY`, `DRY_RUN`, session limits |
| 2 | Install deps + token | pip upgrade huggingface_hub, load `HF_TOKEN` |
| 3 | Mount Drive | `google.colab.drive.mount()` with retry + free space check |
| 4 | Load lib + state | Import `downloader.py`, load/init `run_state.json`, create `SessionGuard` |
| 5 | Registry + queue | Load `registry.yaml`, build ordered download queue |
| 6 | **Run downloads** | Main loop — resumable, per-file checkpoint, session guard, progress bar |
| 7 | Quick resume | Restart downloads after kernel restart without re-running setup |
| 8 | Verify integrity | Cross-check `.sha256` sidecars vs `manifest.json` |
| 9 | Status summary | Per-model status table, Drive free space, recent session logs |

---

## Downloader design (`lib/downloader.py`)

### Resume layers

1. **Model-level**: `run_state.json` on Drive — if `state[model_id] == "complete"`, skip HF API entirely
2. **Manifest-level**: if `manifest.json` exists and all `.sha256` sidecars present → skip
3. **File-level**: if `.sha256` sidecar exists for a file → skip that file
4. **Per-file checkpoint**: `.file_state.json` inside each model dir — written after every file atomically; survives kernel crash

### Session guard
`SessionGuard` class tracks elapsed time since kernel start. Configured via `SESSION_LIMIT_HOURS` (default 24) and `SESSION_WARN_HOURS` (default 1.5). When time remaining ≤ warn threshold:
- Stops queuing new models
- Logs warning with exact time remaining
- Current in-progress model completes cleanly

### Key functions
```python
download_model(model_id, dest_root, hf_token, tier, quant_levels,
               global_index_path, state, save_state_fn,
               session_guard, on_file_progress) -> ModelResult
```

### File layout on Drive
```
DRIVE_ROOT/
  run_state.json
  global_index.jsonl
  logs/
    session-<ts>.md
    verify-report-<ts>.md
  <org>/<model>/<commit_sha[:12]>/
    <files>
    <files>.sha256
    manifest.json
    DESCRIPTOR.json
    DESCRIPTOR.md
    .file_state.json       internal checkpoint — not part of archive
```

---

## Model registry

Shared with `local/` archiver. Located at `local/config/registry.yaml`.
`setup.ipynb` copies it to Drive so it persists across sessions.

Structure per entry:
```yaml
- id: deepseek-ai/DeepSeek-R1
  hf_repo: deepseek-ai/DeepSeek-R1
  tier: A          # A=raw BF16 general, B=raw BF16 code, C=GGUF, D=uncensored
  priority: 1      # 1=token-free, 2=gated (needs HF_TOKEN)
  requires_auth: false
  quant_levels: null   # for Tier C: e.g. [Q4_K_M] or [Q8_0]
```

---

## Docker local runtime setup

### MX Linux 23 (Debian bookworm, SysV init)
```bash
scp colab/local-tools/setup-mxlinux-colab.sh user@<ip>:~/
ssh user@<ip> "bash ~/setup-mxlinux-colab.sh --hf-token hf_TOKEN"
```

Script handles: Docker CE install (bookworm repo), SysV service start,
`update-rc.d` boot enable, docker group, image pull, container start,
helper scripts `~/colab-url.sh` and `~/colab-status.sh`.

### Alpine Linux (OpenRC)
```bash
scp colab/local-tools/setup-alpine-colab.sh root@<ip>:~/
ssh root@<ip> "sh ~/setup-alpine-colab.sh --hf-token hf_TOKEN"
```

### Container spec
```
Image:   us-docker.pkg.dev/colab-images/public/runtime  (~8-10 GB)
Port:    127.0.0.1:9000:8080  (localhost only — use SSH tunnel for remote)
Memory:  4 GB
CPUs:    2
Restart: unless-stopped
```

### SSH tunnel (required for remote machine)
```bash
ssh -L 9000:127.0.0.1:9000 user@<mx-ip> -N
```
Then paste `http://127.0.0.1:9000/?token=...` into Colab.

### Get URL after restart
```bash
ssh user@<mx-ip> "bash ~/colab-url.sh"
```

---

## Known issues

### Docker daemon fails to start on MX Linux 23
**Symptom**: `sudo /etc/init.d/docker start` fails silently.
**Likely causes**:
1. `containerd` not started first — try `sudo /etc/init.d/containerd start` then retry Docker
2. iptables/nftables conflict — MX Linux 23 uses nftables; Docker CE needs iptables-legacy
3. Kernel overlay module not loaded — check `lsmod | grep overlay`

**Diagnostic**:
```bash
sudo /etc/init.d/containerd start
sudo /etc/init.d/docker start
sudo dockerd 2>&1 | head -30   # reveals actual startup error
```

**Fix for nftables conflict** (most common on MX Linux 23):
```bash
sudo apt-get install -y iptables
sudo update-alternatives --set iptables /usr/sbin/iptables-legacy
sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy
sudo /etc/init.d/docker start
```

**Status**: Under active investigation.

---

## Recommended download order

| Session | Tiers | Approx size | Notes |
|---------|-------|------------|-------|
| 1 | C, D | ~900 GB | Quantized + uncensored — completes in 1-2 sessions |
| 2 | B | ~400 GB | Code models |
| 3+ | A priority 1 | ~2.5 TB | Large raw BF16, token-free |
| Last | A priority 2 | ~2.7 TB | Gated models (Llama, Gemma, Mistral Large) |
