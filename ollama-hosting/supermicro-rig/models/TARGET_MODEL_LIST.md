# Target model list (Ollama) — history, queue, HF mapping

**Purpose:** Canonical list of models we want in **Ollama tag** form, with **approximate sizes**, **download history** (not tied to current `~/.ollama` — you may clear the cache anytime), and **pending queue** order.

**Bandwidth / concurrency policy**

| Rule | Value |
|------|--------|
| Max simultaneous `ollama pull` jobs | **1** (do not exceed **2** on the whole host) |
| Download cap | **≤ 4 MiB/s** (~4096 KiB/s) — use `pull-queue-throttled.sh` + `trickle` |
| Upload cap (trickle) | **512 KiB/s** default (metadata only; adjust if needed) |

Install throttle helper: `sudo apt install trickle`

**Operational commands**

```bash
# One model per invocation (safest after cache clear)
export OLLAMA_HOST=127.0.0.1:11434
./pull-queue-throttled.sh --one

# Re-download everything after you wiped ~/.ollama (ignores completed history)
IGNORE_PULL_HISTORY=1 ./pull-queue-throttled.sh --one

# Full queue pass (still one pull at a time inside the script)
./pull-queue-throttled.sh
```

**Source files**

| File | Role |
|------|------|
| `TARGET_QUEUE_ORDERED.txt` | Ordered pull queue (one tag per line) |
| `TARGET_PULL_HISTORY.csv` | Append-only audit of completed / failed pulls |
| `pull-queue-throttled.sh` | Sequential, throttled pulls + history append |

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
| 9 | `starcoder2:15b-instruct-q4_K_M` | ~9 GB |
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

### Uncensored / abliterated batch

| Ollama tag | ~Size | Notes |
|------------|-------|--------|
| `dolphin-mistral:latest` | 4.1 GB | |
| `dolphin-llama3:8b` | 4.7 GB | |
| `huihui_ai/dolphin3-abliterated:latest` | ~5 GB | verify tag page |
| `dolphin-mixtral:8x7b` | ~26 GB | |
| `dolphin-mixtral:8x7b-v2.7` | TBD | **may 404** — drop from queue if pull fails |
| `dolphin-llama3:70b-v2.9-q4_K_M` | ~43 GB | explicit Q4 Dolphin 70B |
| `rolandroland/llama3.1-uncensored:latest` | TBD | community |

### 70B dense + abliterated (`pull-ollama-70b-stack.sh`)

| Ollama tag | ~Size |
|------------|-------|
| `llama3.3:70b-instruct-q4_K_M` | ~43 GB |
| `llama3.1:70b-instruct-q4_K_M` | ~43 GB |
| `qwen2.5:72b-instruct-q4_K_M` | ~40+ GB |
| `huihui_ai/llama3.3-abliterated:70b` | ~43 GB |

### Extra “leaderboard / hostable” picks (see `../OLLAMA_HOSTABLE_LEADER_PICKS.md`)

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
| small | `qwen3.5:4b-q4_K_M` | ~3.4 GB | `Qwen/Qwen3.5-4B`, `Qwen/Qwen3.5-4B-Base` | Qwen 3.5 multimodal line; compact frontier workhorse. |
| small | `gemma3:4b-it-q4_K_M` | ~3.3 GB | `google/gemma-3-4b-it` | Gemma 3 small VLM/text-image; HF BF16 failed — Ollama path. |
| small | `mathstral:7b` | ~4.1 GB | `mistralai/Mathstral-7B-v0.1` | Mistral math / science specialist. |
| small | `deepseek-r1:8b-llama-distill-q4_K_M` | ~4.9 GB | `deepseek-ai/DeepSeek-R1-Distill-Llama-8B` | R1 distill on Llama 8B (distinct from queued `…-0528-qwen3-…`). |
| small | `deepseek-r1:7b-qwen-distill-q4_K_M` | ~4.7 GB | `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` | Smallest official R1 Qwen distill. |
| small | `qwen2.5vl:7b` | ~6.0 GB | `Qwen/Qwen2.5-VL-7B-Instruct` | Flagship-tier open VLM (7B). |
| small | `qwen3.5:9b-q4_K_M` | ~6.6 GB | `Qwen/Qwen3.5-9B`, `Qwen/Qwen3.5-9B-Base` | Mid Qwen 3.5 multimodal. |
| small | `phi4:14b-q4_K_M` | ~9.1 GB | `unsloth/Phi-4-mini-instruct-GGUF`, `unsloth/phi-4-unsloth-bnb-4bit` | Microsoft Phi-4 14B instruct (library). |
| uncensored | `closex/neuraldaredevil-8b-abliterated:latest` | ~5.6 GB | `mlabonne/NeuralDaredevil-8B-GGUF` | Strong uncensored 8B; community namespace on Ollama. |
| specialist | `mistral-small3.2:24b-instruct-2506-q4_K_M` | ~15 GB | `mistralai/Mistral-Small-24B-Instruct-2501`, `tensorblock/Mistral-Small-24B-Instruct-2501-abliterated-GGUF` | Mistral Small 3.2 instruct + vision; official quant. |
| specialist | `gemma3:27b-it-q4_K_M` | ~17 GB | `bartowski/google_gemma-3-27b-it-GGUF` | Gemma 3 27B instruct VLM; complements Gemma 4 queue. |
| specialist | `qwen3.5:27b-q4_K_M` | ~17 GB | `Qwen/Qwen3.5-27B` | Dense Qwen 3.5; HF BF16 failed on archive host. |
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
| `google/medgemma-*`, `OpenDFM/*`, discipline LMs | N/A (check library periodically) | — | Import or new library tags |
| `Alibaba-NLP/gte-Qwen2-7B-instruct`, `intfloat/e5-mistral-7b-instruct` | Search [ollama.com/library](https://ollama.com/library) for `gte`, `e5` | — | Embedding alternates to `bge-m3` |

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
