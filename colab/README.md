# colab — Google Drive Archiver

Downloads LLM/LRM weights from HuggingFace directly into Google Drive using Google Colab.  
Same model list and SHA-256 integrity as the `local/` archiver — manifests are compatible.

---

## Credentials you need

| Credential | What it's for | Where to get it |
|-----------|---------------|----------------|
| **Google account** | Mounting Drive (OAuth popup in Colab) | Your existing account |
| **HuggingFace token** | Gated models (Llama, Gemma, Mistral Large, Phi) | https://huggingface.co/settings/tokens |

Token-free models (DeepSeek, Qwen, Phi-4, all Tier C GGUF, all Tier D) work without a token.  
See `local/docs/HF-TOKEN-GUIDE.md` for per-model licence acceptance instructions.

---

## Quickstart

### 1. Open setup notebook (once per account)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mishra8038/model-archival/blob/master/colab/setup.ipynb)

Or open manually: **File → Open notebook → GitHub → `mishra8038/model-archival` → `colab/setup.ipynb`**

This notebook:
- Checks your Drive quota
- Validates your HF token
- Copies `colab/lib/` and `local/config/registry.yaml` to Drive so they persist across sessions
- Checks which gated models your token can access

### 2. Open the main archiver notebook

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mishra8038/model-archival/blob/master/colab/archiver.ipynb)

Edit **Cell 1** (Configuration):

```python
DRIVE_ROOT = "/content/drive/MyDrive/model-archive"  # where to store on your Drive
TIERS      = ['C', 'D']   # start small; change to ['A','B','C','D'] for everything
MAX_PRIORITY = 1          # 1 = token-free only; 2 = include gated models
DRY_RUN    = False
```

Then: **Runtime → Run all**

### 3. Enable background execution (Pro+ only)

In the Runtime menu: **"Enable background execution"**  
Then close the browser tab — the session continues for up to 24 hours.

---

## Resume behaviour

Each session saves progress to `run_state.json` on your Drive.  
On the next session:
- Already-complete models → skipped (no re-download, no API call)
- Partially downloaded models → resume from last complete file
- Failed models → retried

---

## Recommended download order

| Session | Tiers | Why |
|---------|-------|-----|
| 1 | `['C', 'D']` | Quantized + uncensored — small models, finishes in one session |
| 2 | `['B']` | Code models — moderate size |
| 3+ | `['A']`, priority 1 | Large raw BF16, one or two models per session |
| Last | `['A']`, priority 2 | Gated models (Llama, Gemma, Mistral Large) |

Tier C + D total ≈ 900 GB. Tier A + B total ≈ 5.2 TB.  
At Colab's ~20–30 MB/s to Drive, expect ~10–15 hours per TB.

---

## File layout on Google Drive

```
MyDrive/model-archive/
  run_state.json                    persistent download state
  global_index.jsonl                append-only checksum ledger
  logs/
    verify-report-<ts>.md
  deepseek-ai/
    DeepSeek-R1/
      abc123def456/                 commit SHA subdirectory
        config.json
        config.json.sha256
        model-00001.safetensors
        model-00001.safetensors.sha256
        ...
        manifest.json               compatible with local/ archiver
        DESCRIPTOR.json
        DESCRIPTOR.md
```

The `manifest.json` format is identical to the `local/` archiver — files can be cross-verified between the two archives.

---

## Colab tier comparison

| | Free | Pro | Pro+ |
|--|------|-----|------|
| Max session | 12 h | 24 h | 24 h |
| Background (browser closed) | No | No | **Yes** |
| Suitable for | Testing only | Tier C/D | All tiers |

**Pro+ is strongly recommended** for Tier A (700 GB+ models).

---

## Local runtime on your MX Linux machine (recommended)

Instead of using Colab's hosted servers (with session time limits), you can run an **official Google Colab runtime Docker container** on your local machine. Colab's browser UI connects to it — your machine does all the compute with no time limit.

```bash
# One command — installs Docker, pulls the image, starts the runtime
bash colab/local-tools/setup-docker-runtime.sh

# With your HF token (for gated models):
bash colab/local-tools/setup-docker-runtime.sh --hf-token hf_your_token
# or set it in env:
HF_TOKEN=$(cat ~/.hf_token) bash colab/local-tools/setup-docker-runtime.sh
```

The script:
1. Installs Docker via apt (if not already installed)
2. Adds your user to the docker group
3. Pulls `us-docker.pkg.dev/colab-images/public/runtime` (~5–10 GB, cached after first pull)
4. Starts the container bound to `127.0.0.1:9000` only (localhost, not exposed externally)
5. Mounts the project directory into the container at `/content/model-archival`
6. Prints the connection URL to paste into Colab

Then in Colab: **Connect ▾ → "Connect to a local runtime" → paste URL → Connect**

**Benefits over hosted Colab:**
- No 12/24 hour session limit — runs until you stop it
- Run inside `screen -S colab-runtime` to survive SSH disconnects
- Direct access to your local filesystem from the notebook
- HF token injected securely via environment, not hardcoded

Container management:
```bash
docker stop colab-runtime    # stop
docker logs -f colab-runtime # watch logs
```

## Local keep-alive (fallback)

Only needed if you're using hosted Colab (not the local runtime above) and background execution is unavailable:

```bash
# Install on your local machine:
pip install selenium webdriver-manager

# Run (replace URL with your actual notebook URL):
python colab/local-tools/keep-alive.py \
  --url "https://colab.research.google.com/drive/YOUR_NOTEBOOK_ID" \
  --interval 10
```

---

## Files in this folder

```
colab/
  archiver.ipynb          Main notebook — runs downloads
  setup.ipynb             One-time setup, token check, access audit
  lib/
    downloader.py         Download engine (huggingface_hub + SHA-256)
  local-tools/
    setup-docker-runtime.sh   Install Docker + start Colab local runtime
    keep-alive.py             Selenium keep-alive (fallback, hosted Colab only)
    requirements.txt          pip deps for keep-alive
  config/                 (empty — uses local/config/registry.yaml)
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `FileNotFoundError: Cannot find downloader.py` | Run `setup.ipynb` first — it copies lib/ to Drive |
| `FileNotFoundError: Cannot find registry.yaml` | Run `setup.ipynb` — it copies `local/config/` to Drive |
| HF 401 on a gated model | Accept the model licence at huggingface.co, re-check token |
| Drive quota exceeded | Free up space or upgrade Google One storage |
| Session disconnected mid-download | Re-run `archiver.ipynb` — it resumes automatically |
| Background execution not available | Use `local-tools/keep-alive.py` on your local machine |
| Drive writes very slow (< 5 MB/s) | Normal during first mount; speeds up after a few minutes |
