# Ollama picks: leaderboard-tier, hostable on Supermicro-class GPUs

**Machine profile (this repo):** Supermicro 1028GQ-TXR, **4× Tesla P100 16GB** (~64 GB VRAM total), **no native bfloat16**. **Disk** on the current host is often **~200 GB** class — plan pulls against `df -h` and `du -sh ~/.ollama/models`.

**What “leaderboard” means here:** Public benchmarks (e.g. Chatbot Arena, Open LLM Leaderboard, coding/math suites, MTEB for embeddings) mix **closed** and **open** models. The list below is a **practical self-host subset**: strong **open-weight** lines that have **first-class Ollama tags**, with quant options from **Q2–FP16** where published.

**Safety / uncensored:** “Uncensored” or “abliterated” models **remove or weaken refusals**. Use only where **law and policy** allow, in **controlled** environments.

---

## Top ~10 “compact hostable” cores (open-weight, Ollama)

Roughly ordered by **usefulness on 4×16 GB** at **Q4**; validate each tag on [ollama.com/library](https://ollama.com/library) before pulling.

| # | Focus | Example `ollama pull` | ~Artifact (Q4 ballpark) | Notes |
|---|--------|------------------------|-------------------------|--------|
| 1 | **General SOTA (70B-class)** | `llama3.3:70b-instruct-q4_K_M` | ~43 GB | Strong open instruct; **>4-bit:** same family has `…-q5_K_M` ~50 GB, `…-q6_K` ~58 GB, `…-q8_0` ~75 GB, `…-fp16` ~141 GB (FP16 not realistic on P100+this disk). |
| 2 | **General SOTA (72B-class)** | `qwen2.5:72b-instruct-q4_K_M` | ~40+ GB | Dense flagship tier; complements Llama. |
| 3 | **New-gen Qwen (MoE, hostable)** | `qwen3:30b-a3b-instruct-2507-q4_K_M` | ~19 GB | MoE stack; **Q8** ~32 GB, **FP16** ~61 GB on Ollama tag page — skip FP16 on P100. |
| 4 | **New-gen Qwen (dense 32B)** | `qwen3:32b-q4_K_M` | ~20 GB | **Q8** ~35 GB; **FP16** ~66 GB — too heavy for full-speed FP16 on this box. |
| 5 | **Gemma 4 MoE (Google open line)** | `gemma4:26b-a4b-it-q4_K_M` | ~17–18 GB | Good MoE/Q4 fit; **Q8** variants exist (`…-q8_0`). |
| 6 | **Coding (large Q4)** | `qwen2.5-coder:32b-instruct-q4_K_M` | ~18 GB | Strong code instruct; pair with smaller `qwen2.5-coder:7b` / `14b`. |
| 7 | **Coding (15B StarCoder family)** | `starcoder2:15b-instruct-q4_K_M` | ~9 GB | Code-specialized; smaller footprint. |
| 8 | **Reasoning (distill)** | `deepseek-r1:14b-qwen-distill-q4_K_M` | ~9 GB | “Thinking” style without huge MoE; 8B distill also useful. |
| 9 | **MoE general (wider experts)** | `mixtral:8x7b-instruct-v0.1-q4_K_M` | ~26 GB | Classic MoE; needs **multi-GPU** + disk headroom. |
|10 | **Fast / router / tool smoke** | `llama3.2:3b` or `qwen3:8b-q4_K_M` | ~2–5 GB | Cheap latency for tests and orchestration. |

**Not “compact” on a 200 GB disk / 4×P100:** `deepseek-v3` (hundreds of GB Q4), `qwen3:235b-*` (142 GB+ Q4), **FP16/BF16** blobs for 30B+ — listed on Ollama for completeness but **not** this machine’s sweet spot.

---

## Quantization > 4-bit (same model family, higher quality)

Example **Llama 3.3 70B Instruct** — all official tags exist on [llama3.3 tags](https://ollama.com/library/llama3.3/tags):

| Quant | Tag suffix | ~Size |
|-------|------------|-------|
| Q2 | `llama3.3:70b-instruct-q2_K` | ~26 GB |
| Q3 | `…-q3_K_M` | ~34 GB |
| Q4 | `…-q4_K_M` | ~43 GB |
| Q5 | `…-q5_K_M` | ~50 GB |
| Q6 | `…-q6_K` | ~58 GB |
| Q8 | `…-q8_0` | ~75 GB |
| FP16 | `…-fp16` | ~141 GB |

**P100 guidance:** Prefer **Q4–Q6** for 70B-class; **Q8** only if VRAM and cooling allow; **FP16 70B** is for **smaller** models (e.g. `qwen3:8b-fp16` ~16 GB) or non-Pascal hardware.

**Qwen3** exposes **`-q4_K_M` / `-q8_0` / `-fp16`** per size on [qwen3 tags](https://ollama.com/library/qwen3/tags) — use the tag page to pick “>4-bit” for the size you can fit.

---

## Uncensored / abliterated (70B-class and smaller)

| Style | Example pulls | Notes |
|--------|----------------|--------|
| Dolphin (Llama 3, uncensored-style) | `dolphin-llama3:8b`, `dolphin-llama3:70b-v2.9-q4_K_M` | Strong coding/chat; explicit **Q4** 70B tag. |
| Dolphin + Mistral | `dolphin-mistral`, `dolphin-mixtral:8x7b` | Mixtral is **large** (~26 GB Q4). |
| Abliterated Llama 3.3 | `huihui_ai/llama3.3-abliterated:70b` | Community abliteration; **research / controlled** use. |
| Other community | `huihui_ai/dolphin3-abliterated:latest`, `rolandroland/llama3.1-uncensored` | Verify license + size on Ollama before pull. |

---

## Specialty stacks (top practical picks)

| Specialty | Pull ideas | Quant notes |
|-----------|------------|-------------|
| **Code** | `qwen2.5-coder:*`, `starcoder2:15b-instruct-q4_K_M`, `deepseek-coder-v2:16b`, `codellama:13b-instruct-q4_K_M` | Prefer **Q4_K_M** on P100; **Q8** on smaller coders if you want quality. |
| **Reasoning / “think”** | `deepseek-r1:*-distill-*`, `qwen3:*-thinking*` (see qwen3 tags) | Distills fit VRAM; full R1-class huge models are separate. |
| **Embeddings (MTEB-useful)** | `nomic-embed-text`, `mxbai-embed-large` | Often CPU-OK; GPU speeds batching. |
| **Vision (optional)** | e.g. LLaVA-style tags on Ollama | **Heavy** on P100; treat as experimental. |

---

## Suggested pull batches (scripts in this repo)

- Broad coding + Gemma + MoE (quantized): `supermicro/scripts/pull-ollama-stack.sh`
- 70B dense + abliterated 70B: `supermicro/scripts/pull-ollama-70b-stack.sh`
- Ad-hoc uncensored Dolphin line: `~/pull-uncensored-ollama.sh` on host (if deployed)

Always run `ollama list` and watch **free disk**; **dedupe** is partial — multiple quants of the same base still cost a lot of space.

---

## Revision

When Ollama adds new **library** entries (new Qwen/Llama/Gemma minors), refresh this file and the pull scripts — tag names are the source of truth on **ollama.com/library**.
