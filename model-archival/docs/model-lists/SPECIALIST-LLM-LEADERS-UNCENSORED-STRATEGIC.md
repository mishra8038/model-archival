# Specialist LLM leaders, sizes, uncensored equivalents & strategic reasoning

Curated reference (Mar 2026). **Frontier** names change quickly; **open-weight** IDs below are concrete Hugging Face–style references where they exist.  
**“Uncensored”** here means *less alignment refusals* — usually **community abliterated / unfiltered Instruct** builds, not separate base models. Verify licence and safety before production.

---

## 1. Frontier vs open specialist (by domain)

| Category | Typical frontier / API leader | Reported / active size (indicative) | Strong open-weight specialist | Uncensored / low-refusal open options |
|----------|------------------------------|--------------------------------------|-------------------------------|----------------------------------------|
| **Coding** | Gemini / Claude / GPT (API) | MoE / undisclosed | `Qwen/Qwen2.5-Coder-32B-Instruct`, `deepseek-ai/DeepSeek-Coder-V2-Instruct` | Search HF for **abliterated** or **uncensored** forks of the same coder family; project examples: `tensorblock/*-abliterated-GGUF`, Dolphin-style Qwen coder builds |
| **Reasoning** | OpenAI o-series, Kimi K2 Thinking (API) | Very large total / smaller active | `deepseek-ai/DeepSeek-R1`, R1 **distills** (`deepseek-ai/DeepSeek-R1-Distill-Qwen-7B`, Llama-8B, etc.) | `tensorblock/DeepSeek-R1-Distill-Qwen-32B-abliterated-GGUF` (and similar **tensorblock** / **mlabonne** abliterated GGUFs); always match **exact** HF repo to your stack |
| **Mathematics** | GPT / Claude frontier (API) | Large | `mistralai/Mathstral-7B-v0.1`, `Qwen/Qwen2.5-Math-7B-Instruct`, larger `Qwen2.5-Math-72B` | Same families + community **uncensored** math instructs; Qwen Math instruct is often already capable — “abliterated” mainly for refusal reduction |
| **Law / legal** | Long-context API models (Claude / Gemini class) | Large | `Equall/Saul-7B-Instruct-v1` (legal instruct) | Few “legal-specific” uncensored lines; often use **general abliterated Llama/Qwen** + RAG over statutes/cases; avoid assuming a model is *legally* correct |
| **Management / ops** | GPT / Command R+ class (API + Cohere cloud) | Large | `Salesforce/CoDA-1.7B-Instruct`, `Intel/neural-chat-7b-v3-1` (business-ish chat) | `mlabonne/NeuralDaredevil-8B-abliterated-GGUF`; many teams use **structured-output** instructs (Phi / Qwen) rather than “uncensored” |
| **Chemistry** | Claude / GPT frontier on GPQA-style science (API) | Large | `AI4Chem/ChemLLM-7B-Chat` | Community uncensored **Mistral/Llama** bases fine-tuned for chem; verify domain benchmarks, not just label |
| **Embeddings** | Cohere / OpenAI embedding APIs | N/A (vectors) | `BAAI/bge-m3`, `jinaai/jina-embeddings-v3`, `intfloat/e5-mistral-7b-instruct`, `Alibaba-NLP/gte-Qwen2-7B-instruct` | **N/A** — embeddings are not “censored” in the chat sense; choose multilingual vs English and licence |
| **Classification** | Enterprise API classifiers | Variable | `dmis-lab/biobert-base-cased-v1.2`, `microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext`, `cambridgeltl/SapBERT-from-PubMedBERT-fulltext` | Use **base / task fine-tunes**; “uncensored” rarely applies — watch **label bias** instead |

**Note:** Names like *“Gemini 3 Pro Preview”*, *“GPT-5.x”*, *“Claude 4.x”* in third-party roundups are **vendor marketing** — treat as *class of model* (frontier multimodal / long-context / reasoning API), not stable SKUs.

---

## 2. Smaller high-density / self-hostable (≈1B–14B class)

Good for **single GPU / 8–24 GB VRAM** with **Q4_K_M** (or similar) quants.

| Category | Compact open pick | Size | Why “high density” | Uncensored / abliterated direction |
|----------|-------------------|------|--------------------|--------------------------------------|
| **Coding** | `Qwen/Qwen2.5-Coder-7B-Instruct` | 7B | Strong HumanEval-class coding for size | HF search: same family **abliterated** / **uncensored** forks; `apple/DiffuCoder-7B-Instruct` (project registry) |
| **Reasoning** | `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` | 7B | RL-distilled reasoning trace behaviour | `tensorblock/DeepSeek-R1-Distill-Qwen-32B-abliterated-GGUF` (larger); 7B-level abliterated distills on HF under similar naming |
| **Mathematics** | `mistralai/Mathstral-7B-v0.1`, `Qwen/Qwen2.5-Math-7B-Instruct` | 7B | Math-specialised pretrain / instruct | Prefer **math instruct** + strict eval; uncensored forks optional |
| **Law** | `Equall/Saul-7B-Instruct-v1` | 7B | Legal instruct tuning | General **Llama/Qwen abliterated** + legal RAG if refusals block workflow |
| **Chemistry** | `AI4Chem/ChemLLM-7B-Chat` | 7B | Chemistry chat specialist | Same as above: specialist + optional uncensored base if needed |
| **Management** | `microsoft/Phi-4-mini-instruct` (GGUF e.g. `unsloth/Phi-4-mini-instruct-GGUF`) | ~3.8B | Structured JSON / instructions per param | `unsloth/phi-4-unsloth-bnb-4bit` (project); abliterated small Llama/Qwen for fewer refusals |
| **Classification** | `meta-llama/Llama-3.2-3B-Instruct` + task head / fine-tune | 3B | Fast edge labelling | `tensorblock/Llama-3.2-3B-Instruct-GGUF` (quant); abliterated 3B variants exist on HF |
| **Embeddings** | `BAAI/bge-m3` | ~0.6B | Dense + sparse + multi-vector in one stack | N/A |

**Quant rule of thumb:** ~**4–6 GB** VRAM for 7B Q4; scale up for 32B / 70B distils.

---

## 3. Strategic reasoning & game theory (extended)

Strategic tasks (equilibria, extensive-form games, opponent modelling, negotiation) benefit from **long CoT / verifier-style reasoning** — same family as math olympiad models, plus **explicit prompting** (payoff matrix, players, actions).

| Use case | Frontier / API (reference class) | Open-weight core | Self-hostable distill / SLM | Uncensored / low-refusal open |
|----------|----------------------------------|------------------|-----------------------------|-------------------------------|
| **General strategic reasoning** | o-series–class APIs | `deepseek-ai/DeepSeek-R1` | `DeepSeek-R1-Distill-Qwen-7B` … `14B`, `DeepSeek-R1-Distill-Llama-8B` | **tensorblock** / **mlabonne** abliterated **R1-distill** GGUFs (match exact repo) |
| **Math-heavy game theory** (Nash, zero-sum, proofs) | Same | `DeepSeek-R1` + `Qwen2.5-Math` line | `Qwen2.5-Math-7B-Instruct` + R1-distill for “think then answer” | Abliterated Qwen/Llama if refusals interfere with *toy* violent or taboo game stories |
| **Negotiation / social / deception-heavy games** (Werewolf-style) | Claude-class nuance (API) | Largest open instruct you can run | `Ministral` / `Mistral-Small` class **instruct** (check current Mistral Hub) | **Mistral** ecosystem **uncensored instruct** / abliterated 7B–12B (HF); *evaluate* hallucination vs “freedom” |
| **Branching search** (chess-like planning) | o-series APIs | R1 + strong coder for simulators | R1-distill + small code model for rollouts | Same abliterated stack if you script self-play |

### Prompt pattern (game theory)

1. **Players, actions, information** (perfect / imperfect).  
2. **Payoffs** or preference orderings.  
3. **Solution concept** (Nash, SPE, correlated equilibrium, …).  
4. Ask for **step-by-step** derivation; optionally **self-check** (“verify best responses”).

### Caution

- **Uncensored** models may **hallucinate** equilibria — use **symbolic tools** (Python, Gambit, Nashpy) for verification when possible.  
- **Legal / contractual** “games” still need **human review** — models are not lawyers.

---

## 4. Alignment with this repo

Several IDs above appear in **`model-archival/config/registry-specialists.yaml`** (e.g. Saul-7B, ChemLLM, Mathstral, R1-Distill-Qwen-7B, BioBERT/PubMedBERT/SapBERT, jina-embeddings-v3, tensorblock/unsloth GGUFs).

**P3-on-d3 “finish first” block (2026-03-21+):** in `registry-specialists.yaml`, the four models that were **priority 3 on `d3`** (Gemma-27b GGUF, RomboUltima-32B, two tensorblock abliterated GGUFs) use **`priority: 0`** so they schedule **before** all priority-1+ rows (lower number = sooner in this project).

**Added specialist STEM / medicine (2026-03-21+):** ChemBERTa-Zinc encoder, Qwen2.5-Math-1.5B, DeepSeek-Math-7B-Instruct, Llemma 7B, OLMo-2-1124-7B, BioMedLM, HuatuoGPT2-7B, Bio\_ClinicalBERT — see `registry-specialists.yaml` for `hf_repo` and notes.

**Strategic / game theory — explicitly pinned (2026-03-21):**

| `hf_repo` | Role |
|-----------|------|
| `deepseek-ai/DeepSeek-R1-Distill-Llama-8B` | Small Llama-distill strategic baseline |
| `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B` | Mid R1-distill for longer CoT / games |
| `mistralai/Mistral-Small-24B-Instruct-2501` | Dialogue / negotiation-class instruct (see abliterated GGUF in same registry) |
| `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` | BF16 parent of 32B abliterated GGUF |
| `Qwen/QwQ-32B` | Qwen “QwQ” reasoning line for logic / math-heavy GT |

For a machine-merged flat table across all list docs, see **`MASTER-RECOMMENDATIONS-DATABASE.md`** (regenerate with `build-merged-database.py`).

---

## 5. Sources & maintenance

- User-provided Gemini-oriented roundup + Reddit / blog pointers (uncredited snippets).  
- **You** should re-check: model renames, new `mistralai/*` and `Qwen/*` releases, and HF **abliterated** repo names before pinning in `registry.yaml`.  
- Last updated: **2026-03-21**.
