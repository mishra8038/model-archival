> **Mirror:** This file is a copy of `~/z/env/dev-environment/supermicro/README.md`. Update the canonical tree there, then refresh this copy under `ollama-hosting/supermicro-rig/`.

## Supermicro 1028GQ-TXR – ML Server Notes

Server profile:

- Model: Supermicro 1028GQ-TXR
- RAM: 256 GB
- OS: Ubuntu 24.04.4 LTS
- GPUs: 4x Tesla P100-SXM2-16GB

### Completed bootstrap (2026-04-03)

Performed on host `x@192.168.8.106`:

- Installed base packages (`build-essential`, `python3-pip`, `python3-venv`, `git`, `tmux`, etc.).
- Installed NVIDIA stack via `ubuntu-drivers autoinstall`:
  - Driver: `535.288.01`
  - Kernel updated to `6.8.0-107-generic`
- Installed Docker and NVIDIA Container Toolkit.
- Validated GPU in container with:
  - `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi`
- Created Python venv at `~/venvs/ml` and installed:
  - `huggingface_hub`, `transformers`, `accelerate`, `sentencepiece`, `bitsandbytes`
- Applied low-power GPU policy (for cooling):
  - Persistence mode enabled
  - Power cap set to `150W` on all GPUs
  - Persisted via systemd unit: `set-gpu-power-limits.service`

### Services configured

- `set-gpu-power-limits.service` (system boot oneshot)
- `ollama.service` (custom unit, listens on `0.0.0.0:11434`)

**Ollama model picks** (leaderboard-style hostable set, Q4–FP16 ladder, uncensored/abliterated, specialties): [OLLAMA_HOSTABLE_LEADER_PICKS.md](OLLAMA_HOSTABLE_LEADER_PICKS.md).

**Target queue + download history** (ordered pulls, sizes, HF mapping table, throttled script): [models/TARGET_MODEL_LIST.md](models/TARGET_MODEL_LIST.md).

**Archival sync** (rsync Supermicro `~/.ollama` → disk VM; **destination rotates** `d5`→`d2`→`d3`→`d1` per run unless `ARCHIVAL_VM_DEST` is set): run **`ollama-hosting/scripts/ollama-sync.sh`** from the **model-archival monorepo** (see `ollama-hosting/README.md`). Sync **excludes** incomplete Ollama `*partial*` blobs by default; after sync it **cleans** stray partials on the VM and checks **manifest↔blob integrity**. After each run, open **`ollama-hosting/docs/OLLAMA-ARCHIVAL-MODEL-MAP.md`** for **which `model:tag` lives on which disk** before pruning the Supermicro cache (keep Gemma 4 + Qwen Coder only). See `ollama-hosting/docs/OLLAMA-CACHE-POLICY.md`. The archival VM often cannot SSH to the Supermicro, so the script may use an **sshfs bridge** from a workstation that can reach both hosts.

### vm_host_gpu tuning (dev-environment)

Inventory profile **`vm_host_gpu`** enables optional **`vm_host_gpu_tuning`** (see `restore/network/topology/workgroup.json`). For this host it applies:

- **`/etc/sysctl.d/99-dev-env-vm-host-gpu.conf`**: `vm.swappiness=10`, `vm.max_map_count=524288` (large mmap for ML stacks).
- **Docker** `/etc/docker/daemon.json`: `json-file` log rotation defaults (`max-size` 50m, `max-file` 3) merged without overwriting stricter existing `log-opts`; Docker restart is offered only when the file changes.
- **`irqbalance`** installed and enabled.
- **`nvidia-persistenced`** enabled when the unit/binary exists (alongside your existing persistence / power-cap units).

Apply from your workstation (streams bootstrap + tuning script over SSH):

```bash
cd ~/z/env/dev-environment   # or your clone path
APPLY_ALL=1 ./restore/network/scripts/run-on-hosts.sh --host supermicro-p100
```

Or on the server after pulling the repo:

```bash
sudo APPLY_ALL=1 bash ~/z/env/dev-environment/restore/network/scripts/apply-vm-host-gpu-tuning.sh
```

### Gemma 4 MoE, 4-bit (recommended tag)

On [Ollama’s Gemma 4 library](https://ollama.com/library/gemma4/tags), the **26B MoE** variant with **4-bit-style quantization** (GGUF `Q4_K_M`) is:

| Goal | Ollama image | Approx size | Notes |
|------|----------------|-------------|--------|
| **Gemma 4 MoE + Q4** | `gemma4:26b-a4b-it-q4_K_M` | ~18 GB | **26B** total params, **A4B** = small active set per token (MoE-style); instruction-tuned (`it`); **Q4_K_M** = 4-bit-ish block quant. |
| Smaller Q4 (not the 26B MoE line) | `gemma4:e4b-it-q4_K_M` | ~9.6 GB | Fits a single 16 GB P100 more easily; different size tier than `26b-a4b`. |
| Larger dense Q4 | `gemma4:31b-it-q4_K_M` | ~20 GB | 31B context/product line; not the same as `26b-a4b`. |

**Your hardware:** four **P100 16 GB** (64 GB VRAM total). The **~18 GB** artifact is the right MoE+Q4 choice; Ollama/llama.cpp can use **multiple GPUs** so you are not limited to one 16 GB card. If a run fails with OOM, try shorter context first or temporarily raise power limits only while benchmarking.

**Hugging Face (if you skip Ollama):**

- Base (BF16): [google/gemma-4-26B-A4B-it](https://huggingface.co/google/gemma-4-26B-A4B-it) (accept license + auth).
- Community **GGUF Q4** builds (for llama.cpp / LM Studio–style workflows): e.g. [bartowski/google_gemma-4-26B-A4B-it-GGUF](https://huggingface.co/bartowski/google_gemma-4-26B-A4B-it-GGUF), [ggml-org/gemma-4-26B-A4B-it-GGUF](https://huggingface.co/ggml-org/gemma-4-26B-A4B-it-GGUF).

### Gemma hosting status

- `ollama` service is configured (`0.0.0.0:11434`).
- **Single bulk pull script:** `supermicro/scripts/pull-ollama-stack.sh` — Gemma 4 (Q4/Q8) **plus** coding + reasoning models; order **smallest first**. Copy to `~/pull-ollama-stack.sh` on the server and run (foreground or `nohup`). Expect on the order of **~250+ GB** total disk once all 19 finish; watch `df -h /` — if you run out of space, `ollama rm <name>` on the largest tags you can live without, then re-run the script (it resumes layers).

**Why no BF16 in the stack:** Tesla **P100** has no native **bfloat16** like Ampere+. The script uses **Q4_K_M / Q8_0** (and default small quant blobs) only.

**Included (19 `ollama pull` lines):**  
`deepseek-coder:6.7b`, `qwen2.5-coder:7b`, `llama3.1:8b-instruct-q4_K_M`, `deepseek-r1:8b-0528-qwen3-q4_K_M`, `gemma4:e2b-it-q4_K_M`, `deepseek-coder-v2:16b`, `deepseek-r1:14b-qwen-distill-q4_K_M`, `qwen2.5-coder:14b-instruct-q4_K_M`, `starcoder2:15b-instruct-q4_K_M`, `gemma4:e2b-it-q8_0`, `gemma4:e4b-it-q4_K_M`, `gemma4:e4b-it-q8_0`, `gemma4:26b-a4b-it-q4_K_M`, `gemma4:31b-it-q4_K_M`, `qwen2.5-coder:32b-instruct-q4_K_M`, `deepseek-coder:33b-instruct-q4_K_M`, `gemma4:26b-a4b-it-q8_0`, `gemma4:31b-it-q8_0`, `mixtral:8x7b-instruct-v0.1-q4_K_M`.

**Optional (newer GPUs only):** Gemma / other **BF16** tags — pull manually on Ampere+.

**Monitor a long pull:**

```bash
tail -f ~/logs/ollama-stack-pull.log
ollama list
```

### Next commands

On the server (`ssh x@192.168.8.106`):

```bash
# verify stack
uname -r
nvidia-smi
systemctl status ollama --no-pager

# one-shot full stack (foreground)
chmod +x ~/pull-ollama-stack.sh
OLLAMA_HOST=127.0.0.1:11434 ~/pull-ollama-stack.sh

# or background + log
mkdir -p ~/logs
nohup env OLLAMA_HOST=127.0.0.1:11434 ~/pull-ollama-stack.sh > ~/logs/ollama-stack-pull.log 2>&1 &

# Gemma 4 MoE Q4 alone (quick test)
ollama pull gemma4:26b-a4b-it-q4_K_M

# smoke test (API)
curl -s http://127.0.0.1:11434/api/generate -d '{
  "model": "gemma4:26b-a4b-it-q4_K_M",
  "prompt": "Explain MoE in one paragraph.",
  "stream": false
}' | head -c 2000; echo

# optional: interactive
ollama run gemma4:26b-a4b-it-q4_K_M
```

**Optional smaller Q4** (single-GPU friendly on 16 GB):

```bash
ollama pull gemma4:e4b-it-q4_K_M
```

### Ollama disk cleanup (partial downloads)

Ollama does not ship `prune`; aborted pulls leave `*-partial-*` files under `~/.ollama/models/blobs/`. Script: **`supermicro/scripts/ollama-cleanup-partials.sh`** (also `~/ollama-cleanup-partials.sh` on the server). It stops **`ollama.service`**, deletes those shards, then starts the service again.

**Do not run it while `pull-ollama-stack.sh` or `ollama pull` is active** — the script exits with an error if it detects a running pull (and stopping Ollama would corrupt in-flight downloads anyway).

```bash
chmod +x ~/ollama-cleanup-partials.sh   # copy from repo if missing
~/ollama-cleanup-partials.sh            # needs sudo for systemctl stop/start
```

Remove a **completed** model: `ollama rm <name>`.

### Other Ollama models worth pulling (4× P100 16 GB, research / coding / RAG)

Prefer **Q4** (or small **Q8**) tags on [ollama.com/library](https://ollama.com/library); avoid huge BF16 blobs on Pascal.

| Model (example tag) | Why |
|---------------------|-----|
| **`qwen2.5-coder:7b`** or **`7b-instruct`** | Strong coding + general instruct; good on 16 GB at Q4. |
| **`llama3.2:3b`** | Fast sanity checks and scripting; tiny footprint. |
| **`mistral:7b-instruct-v0.3-q4_0`** (or latest 7B instruct Q4) | Solid general chat / tools-style use. |
| **`phi3:mini`** or **`phi3:medium`** | Efficient Microsoft small models; good latency on P100. |
| **`deepseek-r1:8b`** (Q4 if offered) | Lightweight “reasoning” style without 70B+ VRAM. |
| **`nomic-embed-text`** | Text **embeddings** for RAG / clustering (CPU or GPU). |
| **`mxbai-embed-large`** | Higher-quality embeddings if you have RAM/VRAM headroom. |
| **`llava:7b` / `llava-phi3`** (Q4 variants) | Optional **vision** experiments; heavier and slower on P100—pull only if you need VLM. |

**Not a priority on P100:** 70B+ dense models, BF16 “full” weights, or the largest multimodal stacks unless you accept very slow inference and tight VRAM.

Pull when ready:

```bash
ollama pull qwen2.5-coder:7b
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

### Ready to “host the model” (checklist)

Ollama is **already serving** once `systemctl status ollama` is healthy and `0.0.0.0:11434` is reachable. “Ready” for agents means the **tags you care about** have finished pulling:

- On the server: `ollama list` shows the model(s); `curl -s http://127.0.0.1:11434/api/tags | head` returns JSON.
- If `pull-ollama-stack.sh` is still running: `tail -f ~/logs/ollama-stack-pull.log` (or your log path).

Ensure the **workstation can reach** `tcp/11434` on the server IP (e.g. `192.168.8.106`) if agents run in Docker on another machine.

### Long-term AI coding stack (install once, loop forever)

**One-shot installer on the Supermicro host** (as the desktop user, repo at `~/z/env/dev-environment`):

```bash
cd ~/z/env/dev-environment
chmod +x supermicro/scripts/install-ai-sandboxes-and-clis.sh
APPLY_ALL=1 ./supermicro/scripts/install-ai-sandboxes-and-clis.sh
```

Re-runs are **idempotent**: restore skips CLIs and packages that are already installed; **`dev-environment-*-sandbox:latest`** images are **not** rebuilt if those tags already exist (set **`AI_SANDBOX_REBUILD_IMAGES=1`** when you change a Dockerfile and need a fresh image). The installer also refuses an empty or broken **`restore.sh`** so partial checkouts fail fast.

This runs restore groups **`python`** (installs **uv**), **`node`**, **`ai_dev_tools`**, AI/Hermes **Docker** images, **Cursor** + AppArmor, and **`editors`** (unless you opt out — see below). You get:

| Layer | Tools | Role |
|--------|--------|------|
| **CLI / tmux / CI** | **Aider** (`uv tool install aider-chat`), **Claude Code**, **Codex CLI**, Repomix, Nemoclaw (when uv works), OpenRouter CLI | Scripted refactors, batch tasks, agent sandboxes |
| **Editor (GUI or Remote SSH)** | **Cursor** + extensions: **Continue**, **Roo Code** (`RooVeterinaryInc.roo-cline`), **Cline** (`saoudrizwan.claude-dev`), Claude + ChatGPT IDE | Human-in-the-loop editing on the box or via Remote SSH |
| **Orchestration** | **OpenClaw** + **n8n** inside `dev-environment-ai-sandbox` | Multi-step workflows, webhooks, scheduled jobs |
| **Local models** | **Ollama** on `:11434` | Zero-cost inference for Aider / OpenClaw / Hermes when pointed at `/v1` |

**Headless server (no Cursor extension pass):** some installs still want a display for `cursor --install-extension`. Skip that step with:

```bash
INSTALL_AI_EDITOR_EXTENSIONS=0 APPLY_ALL=1 ./supermicro/scripts/install-ai-sandboxes-and-clis.sh
```

**Aider + Ollama (continuous refactor harness):**

1. Copy `supermicro/config/aider-ollama.env.example` to `~/z/env/ai/aider/ollama.env` and set `OLLAMA_HOST` if Ollama is not on `127.0.0.1:11434`.
2. From a **git** repo root:

```bash
export AIDER_ENV_FILE=~/z/env/ai/aider/ollama.env
export AIDER_MODEL=ollama/qwen2.5-coder:7b   # or another tag from ollama list
~/z/env/dev-environment/supermicro/scripts/run-dev-loop-aider.sh -- "Your improvement task in natural language"
```

Use **`--`** before the message for **`--yes-always`** (fully non-interactive). The wrapper passes your text with **`aider --message`** (plain arguments would be treated as file paths). Omit `--` for interactive review. For long runs, wrap in **tmux** and tail git commits / `aider` output.

**Example layout:** clone work under **`~/z/dev/<repo>`**; improve-loop manifest lives in **`~/z/env/ai/improve-loop/manifest`**. If **`gh`** is not available from apt, install the official binary to **`~/.local/bin/gh`** and run **`gh auth login --with-token`** once. User timers stop after logout unless **`sudo loginctl enable-linger "$USER"`**.

**AI sandbox image** (`dev-environment-ai-sandbox:latest`) includes **Aider**; pass Ollama from the host, e.g.:

```bash
docker run --rm -it --add-host=host.docker.internal:host-gateway \
  -e OPENAI_API_BASE=http://host.docker.internal:11434/v1 -e OPENAI_API_KEY=ollama \
  -v "$PWD:/work" -w /work dev-environment-ai-sandbox:latest \
  bash -lc 'aider --model ollama/qwen2.5-coder:7b'
```

Rebuild the image after Dockerfile changes: `./restore.sh --group ai_docker_sandbox`.

### Hermes Agent + OpenClaw (workstation → LAN Ollama)

**Install persistent Docker VMs** (build images if needed, create/start **`hermes-agent-vm`** and **`openclaw-ai-vm`**; no tmux): **`restore/scripts/install-agent-docker-vms.sh`**.  
Also runs at the end of **`supermicro/scripts/install-ai-sandboxes-and-clis.sh`** unless **`INSTALL_AGENT_VMS=0`**.

**Hermes** (Docker VM `hermes-agent-vm` via `restore/scripts/launch-hermes-agent-tmux.sh`):

1. Copy `supermicro/config/hermes-ollama-override.env.example` to **`~/z/env/ai/hermes/ollama-override.env`** and set `OPENAI_BASE_URL` to `http://<ollama-host>:11434/v1`, `OPENAI_API_KEY=ollama`.
2. Optionally set `HERMES_MODEL=<ollama-tag>` or run `hermes model` once and choose **Custom endpoint** with the same URL and model name.
3. The launcher sources `ollama-override.env` **after** `api-keys.env` so Ollama wins over cloud keys when both exist.

**OpenClaw** (Docker VM `openclaw-ai-vm` via `restore/scripts/launch-openclaw-ai-sandbox-tmux.sh`):

1. First run seeds **`~/z/env/ai/openclaw/openclaw.json`** from `supermicro/config/openclaw-ollama.json.example` if missing — edit **`baseUrl`** (same `http://<host>:11434/v1`) and **`agents.defaults.model.primary`** / provider model **`id`** to match `ollama list`.
2. OpenClaw uses a **custom provider** with `api: "openai-completions"` (Ollama’s OpenAI-compatible surface), per [OpenClaw custom providers](https://docs.openclaw.ai/gateway/configuration-reference#custom-providers-and-base-urls).

**Same host as Docker, Ollama on the host OS:** set `baseUrl` to `http://host.docker.internal:11434/v1` (the launcher adds `host.docker.internal` via `host-gateway`).

