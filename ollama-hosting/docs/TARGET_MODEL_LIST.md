# Target model list (Ollama) — history, queue, HF mapping

**vLLM path:** For Hugging Face–native archival of the same *intent* (deduped repos, `d5/vllm`, one repo per pull), see repo **`vllm-hosting/`** and **`vllm-hosting/docs/VLLM-ARCHIVE.md`**.

**Purpose:** Operational notes (sizes, throttle policy, HF mapping). **Single picture for download → archive → offload** is **[OLLAMA-ARCHIVE-WORKFLOW.md](OLLAMA-ARCHIVE-WORKFLOW.md)**. **Machine-readable state** (queue order, pull status, archive disk / `supermicro_cleared` merged from ollama-hosting) lives in **`OLLAMA_MODEL_REGISTRY.json`**, maintained with **`ollama_registry_tool.py`** (`init`, `merge-pull-history`, `merge-manifest`, `status`).

### Acquisition priorities (order of preference when we expand or reorder the queue)

Use this when **adding tags**, **re-prioritizing** `queue` in **`OLLAMA_MODEL_REGISTRY.json`**, or **debating what to pull next**. “Leaderboard” means **any** credible public ranking you actually use (e.g. **Open LLM Leaderboard**, **LMSYS Chatbot Arena** (open weights), **MTEB** for embeddings, coding/math suites) — pick the board that matches the task (chat vs code vs retrieval).

| Priority | What to favor | Notes |
|----------|----------------|--------|
| **1 — Self-hostable (under ~200B parameters)** | Models you can run or archive on your hardware with a **sane Ollama quant** (artifact size within disk/VRAM policy). | **Total parameter count under 200B** (dense or MoE **total** count). Skip or defer tags whose **Q4-class** artifact is still impractical on your box. **Top ~10** on a relevant leaderboard in this bucket are **especially valuable** — add and move them **up** the queue when a stable **`model:tag`** exists. |
| **2 — Uncensored / abliterated** | Tags with **`group: uncensored`** (Dolphin, abliterated, community uncensored). | Legal/policy constraints still apply; keep in queue for **registry backup** and controlled use. |
| **3 — Specialized** | Code, math, vision, embedding, “tool” models that win on **task-specific** boards or benchmarks. | Often smaller; pair with general chat models. |
| **4 — Dense leaderboard chat** | Strong **dense** instruct models that rank **high** on **general** chat / reasoning leaderboards. | After the above gaps are filled; prefer **official or well-maintained** Ollama tags. |

**Operational rule:** The **pull order** is whatever appears first in **`TARGET_QUEUE_ORDERED.txt`** / **`registry.queue`**. When priorities shift, **edit the queue** (then `python3 ollama_registry_tool.py init` or hand-edit JSON + `export-queue`) so **`ollama-pull-queue`** matches intent — the file is allowed to **reorder**; history CSV does not define future order.

### Review cadence (keep downloading the right things)

- **Revisit this target list regularly** (e.g. **monthly**, or when a major leaderboard refresh / new open release drops): what’s new in the **under-200B self-hostable** band, what fell out of the top tier, what got a **better quant** on [ollama.com/library](https://ollama.com/library).
- **Explicitly check** for open-weight models in the **top ~10** of at least one leaderboard you care about; if missing from **`registry.queue`**, add the tag and bump priority.
- After changes: update **`TARGET_QUEUE_ORDERED.txt`**, run **`apply-default-groups`** if needed, then **`ollama-pull-queue`** / **`OLLAMA_PULL_GROUP=…`** as appropriate.

### Classification (`group` on every queued tag)

Each model in **`OLLAMA_MODEL_REGISTRY.json`** has a **`group`** field (classification). **Quantization** (e.g. `q4_K_M`, `q8_0`, `:latest`) stays in the **Ollama tag**; the group is the same for all variants of that line in the queue.

| `group` | Meaning |
|---------|---------|
| **`uncensored`** | Dolphin, abliterated, and other uncensored community tags (every variant we queue — Q4, Q8, 8B–70B, Mixtral-class dolphins, etc.). |
| **`coding`** | DeepSeek Coder, Qwen2.5-Coder, StarCoder2. |
| **`reasoning`** | DeepSeek-R1 family, QwQ. |
| **`general`** | Gemma 3/4 instruct, small Llama instruct. |
| **`moe_instruct`** | Censored MoE instruct (e.g. Mixtral 8×7B instruct). |
| **`instruct_70b`** | Dense ~70B instruct class (Llama 3.x 70B, Qwen2.5 72B, Nemotron 70B). |
| **`qwen3`** | Qwen3 library line (`qwen3:…`, not `qwen3.5:`). |
| **`embedding`** | `bge-m3`, `granite-embedding`, `nomic-embed-text`, `embeddinggemma`, `snowflake-arctic-embed`, `mxbai-embed-large`, `bge-large`, `qwen3-embedding`. |
| **`vlm`** | Qwen2.5-VL. |
| **`specialist`** | Qwen3.5 (Q4 and dense **BF16** variants), Mathstral, Phi-4, Mistral Small 3.2, and other frontier picks in the queue tail. |

**Commands**

```bash
python3 ollama_registry_tool.py apply-default-groups --force   # recompute all groups from tag rules
python3 ollama_registry_tool.py list-group uncensored
python3 ollama_registry_tool.py status   # table includes Group column
```

**Pull only uncensored pending models:** `OLLAMA_PULL_GROUP=uncensored ./scripts/ollama-pull-queue` (from **`ollama-hosting/`**; registry mode; one model per run by default; see script header).

The narrative sections below (sizes, HF IDs) remain useful; **which tags are “uncensored”** is defined by **`group: uncensored`** in the registry, not by a separate markdown-only list.

**Bandwidth / concurrency policy**

| Rule | Value |
|------|--------|
| Max simultaneous `ollama pull` jobs | **1** (do not exceed **2** on the whole host) |
| Download cap | **≤ 4 MiB/s** (~4096 KiB/s) — use `pull-queue-throttled.sh` + `trickle` |
| Upload cap (trickle) | **512 KiB/s** default (metadata only; adjust if needed) |

Install throttle helper: `sudo apt install trickle`

**Operational commands**

```bash
# Canonical pull driver (registry + CSV); cwd = ollama-hosting/ on the Ollama host
export OLLAMA_HOST=127.0.0.1:11434
./scripts/ollama-pull-queue                # default: **one** next pending model (~4 MiB/s via trickle)

./scripts/ollama-pull-queue --one          # same as no args

IGNORE_PULL_HISTORY=1 ./scripts/ollama-pull-queue   # re-pull after ~/.ollama wipe (still one model unless --all)

./scripts/ollama-pull-queue --all            # drain all pending models (sequential; one ollama pull at a time)
```

`registry/pull-queue-throttled.sh` is a **thin wrapper** that calls **`../scripts/ollama-pull-queue`**.

**Source files**

| File | Role |
|------|------|
| `registry/OLLAMA_MODEL_REGISTRY.json` | **Canonical** queue + per-tag pull/archive fields |
| `registry/ollama_registry_tool.py` | Init / merge CSV & manifest / `status` |
| `registry/TARGET_QUEUE_ORDERED.txt` | Pull script input; run `init` after you edit |
| `registry/TARGET_PULL_HISTORY.csv` | Append-only pull audit |
| `registry/pull-queue-throttled.sh` | Wrapper → `../scripts/ollama-pull-queue` |

---

## 1. Download history (high level — not cache state)

Rows are **“successfully pulled at least once”** in our sessions (timestamps approximate). After a cache clear, blobs are gone but this table stays true for **inventory / licensing / planning**. Update the CSV when you add new completions.

| Ollama tag | ~Size | When (UTC) | Notes |
|------------|-------|------------|--------|
| `deepseek-coder:6.7b` | 3.8 GB | 2026-04-03 | Base stack |
| `qwen2.5-coder:7b` | 4.7 GB | 2026-04-03 | |
| `llama3.1:8b-instruct-q4_K_M` | 4.9 GB | 2026-04-03 | |
| `deepseek-r1:8b-0528-qwen3-q4_K_M` | 5.2 GB | 2026-04-03 | |
| `gemma4:e2b-it-q4_K_M` | 7.2 GB | 2026-04-03 | |
| `deepseek-coder-v2:16b` | 8.9 GB | 2026-04-03 | |
| `deepseek-r1:14b-qwen-distill-q4_K_M` | 9.0 GB | 2026-04-03 | |
| `qwen2.5-coder:14b-instruct-q4_K_M` | 9.0 GB | 2026-04-03 | |
| `gemma4:e2b-it-q8_0` | 8.1 GB | 2026-04-03 | |
| `gemma4:e4b-it-q4_K_M` | 9.6 GB | 2026-04-03 | |
| `gemma4:e4b-it-q8_0` | 11 GB | 2026-04-03 | |
| `gemma4:26b-a4b-it-q4_K_M` | 17 GB | 2026-04-03 | |
| `dolphin-mistral:latest` | 4.1 GB | 2026-04-03 | Uncensored-style |
| `dolphin-llama3:8b` | 4.7 GB | 2026-04-03 | Uncensored-style |

*Machine-readable copy:* `TARGET_PULL_HISTORY.csv` (add new lines as you finish pulls).

**Not recorded here as finished** (were queued / partial / failed / disk): remainder of `pull-ollama-stack.sh`, `pull-ollama-70b-stack.sh`, full uncensored batch (`huihui_ai/dolphin3-abliterated`, Mixtral, 70B class, `rolandroland/…`), and most `TARGET_QUEUE_ORDERED.txt` tail — treat as **pending** until a row exists in history.

---

## 2. Pending queue (canonical order + sizes)

Same order as `TARGET_QUEUE_ORDERED.txt`. Sizes are **approximate** from Ollama registry / prior pulls — confirm at [ollama.com/library](https://ollama.com/library).

### Base + coding + Gemma + MoE (`pull-ollama-stack.sh`)

| # | Ollama tag | ~Size |
|---|------------|-------|
| 1 | `deepseek-coder:6.7b` | 3.8 GB |
| 2 | `qwen2.5-coder:7b` | 4.7 GB |
| 3 | `llama3.1:8b-instruct-q4_K_M` | 4.9 GB |
| 4 | `deepseek-r1:8b-0528-qwen3-q4_K_M` | 5.2 GB |
| 5 | `gemma4:e2b-it-q4_K_M` | 7.2 GB |
| 6 | `deepseek-coder-v2:16b` | 8.9 GB |
| 7 | `deepseek-r1:14b-qwen-distill-q4_K_M` | 9.0 GB |
| 8 | `qwen2.5-coder:14b-instruct-q4_K_M` | 9.0 GB |
| 9 | `starcoder2:15b` | ~9.1 GB (`starcoder2:15b-instruct-q4_K_M` — **not** on Ollama registry; HF `bartowski/starcoder2-15b-instruct-GGUF`) |
| 10 | `gemma4:e2b-it-q8_0` | 8.1 GB |
| 11 | `gemma4:e4b-it-q4_K_M` | 9.6 GB |
| 12 | `gemma4:e4b-it-q8_0` | 11 GB |
| 13 | `gemma4:26b-a4b-it-q4_K_M` | ~17 GB |
| 14 | `gemma4:31b-it-q4_K_M` | ~20 GB |
| 15 | `qwen2.5-coder:32b-instruct-q4_K_M` | ~18 GB |
| 16 | `deepseek-coder:33b-instruct-q4_K_M` | ~19 GB |
| 17 | `gemma4:26b-a4b-it-q8_0` | larger than Q4 |
| 18 | `gemma4:31b-it-q8_0` | larger than Q4 |
| 19 | `mixtral:8x7b-instruct-v0.1-q4_K_M` | ~26 GB |

### Uncensored / abliterated (registry: `group: uncensored`)

All targets use **`OLLAMA_MODEL_REGISTRY.json`** + **`TARGET_QUEUE_ORDERED.txt`**. Tags in this class include Dolphin lines, `huihui_ai/…abliterated`, `rolandroland/…uncensored`, `closex/neuraldaredevil-…abliterated`, and **`huihui_ai/llama3.3-abliterated:70b`** (70B abliterated is still **`uncensored`**, not `instruct_70b`). **List:** `python3 ollama_registry_tool.py list-group uncensored`. Approximate sizes and quant notes for the dolphin block were previously tabulated here — confirm on [ollama.com/library](https://ollama.com/library).

### 70B dense instruct (registry: mostly `instruct_70b`)

Censored dense ~70B instruct pulls (for stack scripts): `llama3.3:70b-instruct-q4_K_M`, `llama3.1:70b-instruct-q4_K_M`, `qwen2.5:72b-instruct-q4_K_M`. **`huihui_ai/llama3.3-abliterated:70b`** is under **`uncensored`**, not this group.

### Extra “leaderboard / hostable” picks (see [`OLLAMA_HOSTABLE_LEADER_PICKS.md`](OLLAMA_HOSTABLE_LEADER_PICKS.md))

| Ollama tag | ~Size |
|------------|-------|
| `qwen3:8b-q4_K_M` | ~5.2 GB |
| `qwen3:14b-q4_K_M` | ~9.3 GB |
| `qwen3:30b-a3b-instruct-2507-q4_K_M` | ~19 GB |
| `qwen3:32b-q4_K_M` | ~20 GB |
| `llama3.2:3b` | ~2 GB |

### From `SPECIALIST-HF-PENDING-OLLAMA.md` (cross-merge, ≤128 GiB)

Source: `/home/x/z/dev/model-archival/model-archival/model-archival/docs/SPECIALIST-HF-PENDING-OLLAMA.md`. Included only when there is a **first-class or well-used Ollama tag**, **artifact ≤ 128 GB**, and a **current leaderboard / frontier** story (excludes MPT/Falcon-180B/DBRX stragglers, gated-only rows, and HF-only encoders without a library pull). Order matches `TARGET_QUEUE_ORDERED.txt` tail: **small hostable → uncensored → specialist / larger**.

| Priority | Ollama tag | ~Size | Representative HF `id` (pending doc) | Notes |
|----------|------------|-------|----------------------------------------|--------|
| small | `bge-m3` | ~1.2 GB | `BAAI/bge-m3` | Embedding / RAG; MTEB-useful multilingual dense retrieval. |
| `embedding` | `granite-embedding` | ~0.06 GB | *(IBM Granite embed)* | Tiny baseline embedder. |
| `embedding` | `nomic-embed-text` | ~0.27 GB | *(Nomic)* | Widely used Ollama default; fast / CPU-friendly. |
| `embedding` | `embeddinggemma` | ~0.62 GB | *(Google Gemma embed)* | Pairs with Gemma chat/VLM lines. |
| `embedding` | `snowflake-arctic-embed` | ~0.67 GB | *(Snowflake)* | Strong MTEB-class dense retrieval. |
| `embedding` | `mxbai-embed-large` | ~0.67 GB | *(MixedBread)* | See also `OLLAMA_HOSTABLE_LEADER_PICKS.md`. |
| `embedding` | `bge-large` | ~0.67 GB | `BAAI/bge-large-en-v1.5` (family) | English dense; complements multilingual `bge-m3`. |
| `embedding` | `qwen3-embedding` | ~4.7 GB | `Qwen/Qwen3-Embedding-…` (family) | Larger Qwen3 embedding checkpoint. |
| small | `qwen3.5:4b-q4_K_M` | ~3.4 GB | `Qwen/Qwen3.5-4B`, `Qwen/Qwen3.5-4B-Base` | Qwen 3.5 multimodal line; compact frontier workhorse. |
| small | `qwen3.5:4b-bf16` | ~9.3 GB | `Qwen/Qwen3.5-4B` | Same dense checkpoint, **BF16** on Ollama (not GGUF Q4); pulls after `…-q4_K_M`. |
| small | `gemma3:4b-it-q4_K_M` | ~3.3 GB | `google/gemma-3-4b-it` | Gemma 3 small VLM/text-image; HF BF16 failed — Ollama path. |
| small | `alibayram/medgemma:4b` | ~2.5 GB (manifest ~2.49 GB) | `google/medgemma-4b-it` | Community Ollama port; **not** first-party Google — verify licence/size before pull. |
| small | `mathstral:7b` | ~4.1 GB | `mistralai/Mathstral-7B-v0.1` | Mistral math / science specialist. |
| small | `deepseek-r1:8b-llama-distill-q4_K_M` | ~4.9 GB | `deepseek-ai/DeepSeek-R1-Distill-Llama-8B` | R1 distill on Llama 8B (distinct from queued `…-0528-qwen3-…`). |
| small | `deepseek-r1:7b-qwen-distill-q4_K_M` | ~4.7 GB | `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` | Smallest official R1 Qwen distill. |
| small | `qwen2.5vl:7b` | ~6.0 GB | `Qwen/Qwen2.5-VL-7B-Instruct` | Flagship-tier open VLM (7B). |
| small | `qwen3.5:9b-q4_K_M` | ~6.6 GB | `Qwen/Qwen3.5-9B`, `Qwen/Qwen3.5-9B-Base` | Mid Qwen 3.5 multimodal. |
| small | `qwen3.5:9b-bf16` | ~19 GB | `Qwen/Qwen3.5-9B` | Dense **BF16**; verify VRAM/disk before pull. |
| small | `phi4:14b-q4_K_M` | ~9.1 GB | `unsloth/Phi-4-mini-instruct-GGUF`, `unsloth/phi-4-unsloth-bnb-4bit` | Microsoft Phi-4 14B instruct (library). |
| `uncensored` (group) | `closex/neuraldaredevil-8b-abliterated:latest` | ~5.6 GB | `mlabonne/NeuralDaredevil-8B-GGUF` | Same **`group`** as Dolphin / other abliterated queue tags. |
| specialist | `mistral-small3.2:24b-instruct-2506-q4_K_M` | ~15 GB | `mistralai/Mistral-Small-24B-Instruct-2501`, `tensorblock/Mistral-Small-24B-Instruct-2501-abliterated-GGUF` | Mistral Small 3.2 instruct + vision; official quant. |
| specialist | `gemma3:27b-it-q4_K_M` | ~17 GB | `bartowski/google_gemma-3-27b-it-GGUF` | Gemma 3 27B instruct VLM; complements Gemma 4 queue. |
| specialist | `qwen3.5:27b-q4_K_M` | ~17 GB | `Qwen/Qwen3.5-27B` | Dense Qwen 3.5; HF BF16 failed on archive host. |
| specialist | `qwen3.5:27b-bf16` | ~56 GB | `Qwen/Qwen3.5-27B` | Largest **dense** Qwen3.5 on Ollama in BF16; MoE lines use separate tags (`35b-a3b`, `122b-a10b`). |
| specialist | `deepseek-r1:32b-qwen-distill-q4_K_M` | ~20 GB | `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B`, `tensorblock/DeepSeek-R1-Distill-Qwen-32B-abliterated-GGUF` | Large R1 Qwen distill. |
| specialist | `qwq:32b-q4_K_M` | ~20 GB | `Qwen/QwQ-32B` | Qwen “think” / reasoning line. |
| specialist | `qwen2.5vl:32b-q4_K_M` | ~21 GB | *(VL flagship; pairs with failed `Qwen2.5-VL-72B`)* | Hostable VLM step below 72B Q4. |
| specialist | `qwen3.5:35b-a3b-q4_K_M` | ~24 GB | `Qwen/Qwen3.5-35B-A3B`, `Qwen/Qwen3.5-35B-A3B-Base` | Qwen 3.5 MoE instruct (~3B active). |
| specialist | `nemotron:70b-instruct-q4_K_M` | ~43 GB | `nvidia/NVIDIA-Nemotron-3-*` (Nano/Super are separate HF IDs) | Ollama **`nemotron`** is **Llama-3.1-Nemotron-70B-Instruct** (NVIDIA “helpfulness” line), not the 30B Nano checkpoint. |
| specialist | `deepseek-r1:70b-llama-distill-q4_K_M` | ~43 GB | `tensorblock/DeepSeek-R1-Distill-Llama-70B-abliterated-GGUF` | Official R1 Llama-70B distill Q4; abliterated GGUF remains HF-only. |
| specialist | `qwen2.5vl:72b-q4_K_M` | ~49 GB | `Qwen/Qwen2.5-VL-72B-Instruct` | Largest Qwen2.5-VL under 128 GB at Q4 (**skip `…-fp16` ~147 GB**). |
| specialist | `qwen3.5:122b-a10b-q4_K_M` | ~81 GB | `Qwen/Qwen3.5-122B-A10B` | MoE frontier; still under 128 GB at Q4. |

**Explicitly out of scope here (from the same HF table):** artifacts **> 128 GB** (e.g. `qwen2.5vl:72b-fp16`), **no Ollama library mapping** (most BERT/encoder-only biomedical rows, ChemLLM, llemma, RomboUltima without a verified tag), **gated / skipped** (DBRX, Gemini previews), **historical or delisted** (MPT, Falcon-180B), and **671B / 397B** class weights.

---

## 3. Hugging Face → Ollama (residual / not queued)

Rows below are **not** appended to `TARGET_QUEUE_ORDERED.txt` until there is a **stable Ollama tag** or you add a **Modelfile** import.

| HF repo / file | Suggested Ollama tag (or N/A) | ~Size | Status |
|----------------|------------------------------|-------|--------|
| `google/medgemma-4b-it` | **`alibayram/medgemma:4b`** (queued) | ~2.5 GB | Community port — confirm on [ollama.com](https://ollama.com) before production |
| `google/medgemma-27b-it`, `google/medgemma-27b-text-it` | HF archival (no Ollama queue) | — | Prefer Hugging Face for 27B MedGemma; **`alibayram/medgemma:27b`** not targeted |
| `OpenDFM/*`, other discipline LMs | N/A (check library periodically) | — | Import or new library tags |
| `Alibaba-NLP/gte-Qwen2-7B-instruct`, `intfloat/e5-mistral-7b-instruct` | Search [ollama.com/library](https://ollama.com/library) for `gte`, `e5` | — | Not queued; queue already has **`bge-m3`**, **`bge-large`**, **`qwen3-embedding`**, etc. |

When a row is resolved, add the Ollama tag to `TARGET_QUEUE_ORDERED.txt` and move the row out of this table.

---

## 4. Throttle tuning

| Variable | Meaning |
|----------|---------|
| `THROTTLE_KBPS` | `trickle -d` download KiB/s (default **4096** ≈ 4 MiB/s) |
| `THROTTLE_UPLOAD_KBPS` | `trickle -u` (default **512**) |

`trickle` does not apply to all binaries on all kernels; if pulls ignore the cap, use host-level QoS or run during off-peak.

---

## 5. Maintenance

1. After each successful pull, the script appends to `TARGET_PULL_HISTORY.csv`; mirror important rows in **§1** if you want the markdown table to stay in sync.
2. When you **clear `~/.ollama`**, run with `IGNORE_PULL_HISTORY=1` and `--one` in a loop until the cache matches your goals.
3. Edit **`TARGET_QUEUE_ORDERED.txt`** as the single ordered queue; keep sizes in this file updated when Ollama changes blobs.
