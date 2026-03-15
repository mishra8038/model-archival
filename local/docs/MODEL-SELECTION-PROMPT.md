# Prompt: Generate model selection list for archival

Use this prompt with **any LLM** (local or API) to produce a candidate model list for the archival registry. Paste the prompt below and, if needed, append your constraints (e.g. “only models under 50B”, “add this month’s Hugging Face trending open LLMs”).

---

## Prompt (copy from here)

You are helping maintain a **Hugging Face model archival registry** for offline, resumable, verified storage of open-source LLM/LRM weights. The registry is YAML: each entry has `id`, `hf_repo`, `tier`, `drive`, `priority`, `licence`, `requires_auth`, and optional `notes`, `quant_levels` (for GGUF), `parent_model`, `method`.

**Model preference criteria (what to include in the MAIN list):**

1. **Frontier / leaderboard** — Current top open models: DeepSeek (V3, R1, R1-Distill-*), Qwen (2.5, 3, base + instruct), Meta Llama (3.1, 3.2, 3.3), Google Gemma 3, Mistral (Large, Small, Mixtral), Microsoft Phi-4, Cohere Command R+, NVIDIA Nemotron, AllenAI Tulu, NovaSky, xAI Grok, etc. Include both **instruct** and **base** (pre-trained) versions where relevant for reproducibility and fine-tuning.

2. **Code-specialist (Tier B)** — DeepSeek-Coder-V2, Qwen2.5-Coder, Qwen3-Coder, Codestral, Devstral, OlympicCoder, and similar top code models.

3. **Abliterated / uncensored (Tier D)** — Variants that fulfill a clear use: huihui-ai abliterated, tensorblock abliterated GGUF, mlabonne, failspy, cognitivecomputations Dolphin, CombinHorizon, rombodawg, FINGU-AI merges, etc.

4. **Niche / SME** — Models that fulfill a function: **embeddings** (e.g. BAAI/bge-*, Alibaba-NLP/gte-Qwen2-*, intfloat/e5-mistral-*) for RAG; **reward models** (e.g. Skywork) for RLHF; **reasoning** (QwQ, OlympicCoder, NovaSky); **vision** (Qwen VL, DeepSeek-VL, Llama Vision, Gemma 4B); **math** (Qwen2.5-Math, DeepSeek-R1-Distill-Qwen-7B); **research** (e.g. small reference models with a clear baseline role).

**Exclude from the main list (put in LEGACY instead):**

- Older or superseded models (e.g. Qwen1.5, Phi-3-mini, TinyLlama, Yi-34B, GLM-4 9B, older InternLM chat).
- Models that are only of historical significance and can be recreated or are no longer on the frontier (e.g. starcoder2, zephyr-7b-beta, Intel neural-chat-7b).
- Duplicates or strictly worse variants of a model already in the list.

**Tiers:** A = general/reasoning raw; B = code raw; C = GGUF quantized; D = uncensored/abliterated; E = reasoning; F = vision; G = math/research. **Drive:** d1 = large raw; d2 = mid-size raw + Tier D raw; d3 = GGUF + research. **Priority:** 1 = token-free; 2 = gated (HF token required).

**Output format:** For each model, output one line or a YAML block with: `id` (Hugging Face repo id, e.g. `org/model-name`), `tier`, `drive`, `priority`, `licence` (if known), `requires_auth` (true if gated on HF), and a short `notes` if useful. If the model is GGUF or has specific quant levels, add `quant_levels` (e.g. `["Q8_0"]` or `["Q3_K_M"]`). Prefer official HF repo IDs and current canonical names.

**Task:** [INSERT HERE: e.g. “List the top 20 open LLMs on the Hugging Face Open LLM Leaderboard as of 2025 that are not yet in our registry.” / “Add any new Qwen or DeepSeek models released in the last 30 days.” / “Suggest embedding models for RAG that we don’t already have.”]

---

## Example follow-ups

- “Output the list as YAML list items under `models:` so I can paste into `config/registry.yaml`.”
- “For each model, also suggest `parent_model` and `method` if it’s a fine-tune or abliterated variant.”
- “Mark which of these should go in the legacy registry instead of the main one.”

---

## Reference: existing registry layout

- Main registry: `config/registry.yaml` — frontier, base, abliterated, niche only; default download uses this.
- Legacy registry: `config/registry-legacy.yaml` — older/superseded; only used with `--registry config/registry-legacy.yaml --include-legacy`.
- Drives: d1 (large raw), d2 (mid-size raw + Tier D), d3 (GGUF + research), d5 (metadata only, no model data).
