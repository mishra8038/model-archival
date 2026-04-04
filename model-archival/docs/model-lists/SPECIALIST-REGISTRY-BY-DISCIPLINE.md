# Specialist registry (`registry-specialists.yaml`) — models by discipline

**72 models** (as of registry in repo). Columns: **`id`** · **tier** · **drive** · **priority** (0 = queue-first block on d3; lower = sooner).

---

## Biomedical & life-science NLP

| Model | T | Drv | P |
|-------|---|-----|---|
| `aaditya/Llama3-OpenBioLLM-8B` | G | d3 | 1 |
| `cambridgeltl/SapBERT-from-PubMedBERT-fulltext` | G | d3 | 1 |
| `dmis-lab/biobert-base-cased-v1.2` | G | d3 | 1 |
| `microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext` | G | d3 | 1 |
| `stanford-crfm/BioMedLM` | G | d3 | 1 |

---

## Medicine & clinical (chat + clinical encoders)

| Model | T | Drv | P |
|-------|---|-----|---|
| `FreedomIntelligence/HuatuoGPT2-7B` | G | d3 | 1 |
| `emilyalsentzer/Bio_ClinicalBERT` | B | d3 | 1 |

---

## Chemistry

| Model | T | Drv | P |
|-------|---|-----|---|
| `AI4Chem/ChemLLM-7B-Chat` | G | d3 | 1 |
| `seyonec/ChemBERTa-zinc-base-v1` | B | d3 | 1 |

---

## Mathematics

| Model | T | Drv | P |
|-------|---|-----|---|
| `mistralai/Mathstral-7B-v0.1` | G | d3 | 1 |
| `Qwen/Qwen2.5-Math-1.5B` | G | d3 | 1 |
| `deepseek-ai/deepseek-math-7b-instruct` | G | d3 | 1 |
| `EleutherAI/llemma_7b` | G | d3 | 1 |
| `Qwen/Qwen2.5-Math-7B-Instruct` | G | d3 | 2 |
| `Qwen/Qwen2.5-Math-72B-Instruct` | G | d5 | 4 |

---

## Science (open / reproducible LM)

| Model | T | Drv | P |
|-------|---|-----|---|
| `allenai/OLMo-2-1124-7B` | G | d3 | 1 |

---

## Legal

| Model | T | Drv | P |
|-------|---|-----|---|
| `Equall/Saul-7B-Instruct-v1` | G | d3 | 1 |

---

## Reasoning, strategic reasoning & game theory

| Model | T | Drv | P |
|-------|---|-----|---|
| `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` | G | d3 | 1 |
| `deepseek-ai/DeepSeek-R1-Distill-Llama-8B` | G | d3 | 2 |
| `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B` | G | d3 | 2 |
| `mistralai/Mistral-Small-24B-Instruct-2501` | G | d5 | 2 |
| `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` | G | d5 | 3 |
| `Qwen/QwQ-32B` | G | d5 | 3 |
| `unsloth/DeepSeek-R1-GGUF` | C | d5 | 4 |
| `tensorblock/DeepSeek-R1-Distill-Qwen-32B-abliterated-GGUF` | D | d3 | 0 |
| `tensorblock/DeepSeek-R1-Distill-Llama-70B-abliterated-GGUF` | D | d5 | 4 |

---

## Coding & code-generation (incl. diffusion-code research)

| Model | T | Drv | P |
|-------|---|-----|---|
| `deepseek-ai/deepseek-coder-6.7b-instruct` | B | d3 | 2 |
| `Salesforce/CoDA-1.7B-Base` | G | d3 | 1 |
| `Salesforce/CoDA-1.7B-Instruct` | G | d3 | 1 |
| `apple/DiffuCoder-7B-Base` | G | d3 | 2 |
| `apple/DiffuCoder-7B-cpGRPO` | G | d3 | 2 |
| `apple/DiffuCoder-7B-Instruct` | G | d3 | 2 |
| `mistralai/Leanstral-120B-A6B` | E | d3 | 2 |

---

## Formal proofs / Lean (overlaps coding & math)

*Listed under coding above:* `mistralai/Leanstral-120B-A6B`

---

## Embeddings & retrieval

| Model | T | Drv | P |
|-------|---|-----|---|
| `jinaai/jina-embeddings-v3` | B | d3 | 1 |
| `Alibaba-NLP/gte-Qwen2-7B-instruct` | B | d3 | 2 |
| `intfloat/e5-mistral-7b-instruct` | B | d3 | 2 |
| `BAAI/bge-en-icl` | B | d5 | 4 |
| `BAAI/bge-large-en-v1.5` | B | d5 | 4 |
| `BAAI/bge-m3` | B | d5 | 4 |

---

## Vision & multimodal

| Model | T | Drv | P |
|-------|---|-----|---|
| `google/gemma-3-4b-it` | F | d3 | 1 |
| `meta-llama/Llama-3.2-11B-Vision-Instruct` | F | d3 | 2 |
| `Qwen/Qwen2.5-VL-7B-Instruct` | F | d3 | 2 |
| `deepseek-ai/deepseek-vl2` | F | d5 | 4 |
| `Qwen/Qwen2.5-VL-72B-Instruct` | F | d5 | 4 |
| `meta-llama/Llama-3.2-90B-Vision-Instruct` | F | d5 | 4 |

---

## Small instruct / GGUF (general-purpose, size-constrained)

| Model | T | Drv | P |
|-------|---|-----|---|
| `tensorblock/Llama-3.2-3B-Instruct-GGUF` | C | d3 | 1 |
| `unsloth/Qwen3-4B-Instruct-2507-GGUF` | C | d3 | 1 |
| `unsloth/Phi-4-mini-instruct-GGUF` | C | d3 | 2 |
| `unsloth/phi-4-unsloth-bnb-4bit` | C | d5 | 4 |
| `bartowski/google_gemma-3-27b-it-GGUF` | C | d3 | 0 |

---

## Chat / alignment baselines (preference-style, reference chats)

| Model | T | Drv | P |
|-------|---|-----|---|
| `HuggingFaceH4/zephyr-7b-beta` | G | d3 | 2 |
| `Intel/neural-chat-7b-v3-1` | G | d3 | 2 |

---

## Uncensored / abliterated / merges (general)

| Model | T | Drv | P |
|-------|---|-----|---|
| `FINGU-AI/RomboUltima-32B` | D | d3 | 0 |
| `mlabonne/NeuralDaredevil-8B-abliterated-GGUF` | D | d3 | 2 |
| `tensorblock/Mistral-Small-24B-Instruct-2501-abliterated-GGUF` | D | d3 | 0 |
| `cognitivecomputations/dolphin-2.9.2-qwen2-72b` | D | d5 | 4 |
| `failspy/Meta-Llama-3-70B-Instruct-abliterated-v3.5` | D | d5 | 4 |
| `rombodawg/Rombos-LLM-V2.5-Qwen-72b` | D | d5 | 4 |
| `tensorblock/Llama-3.3-70B-Instruct-abliterated-GGUF` | D | d5 | 4 |

---

## Safety & moderation

| Model | T | Drv | P |
|-------|---|-----|---|
| `meta-llama/Llama-Guard-4-12B` | E | d3 | 2 |
| `meta-llama/Llama-Prompt-Guard-2-22M` | E | d5 | 4 |

---

## Reward / RLHF infrastructure

| Model | T | Drv | P |
|-------|---|-----|---|
| `Skywork/Skywork-Reward-Llama-3.1-70B` | B | d5 | 4 |

---

## Agents / long-context MoE foundations (Nemotron family)

| Model | T | Drv | P |
|-------|---|-----|---|
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-Base-BF16` | A | d3 | 1 |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` | A | d3 | 1 |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8` | C | d3 | 1 |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-Base-BF16` | D | d5 | 4 |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16` | D | d5 | 4 |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8` | D | d5 | 4 |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4` | D | d5 | 4 |

---

## Very large / deprioritised frontier-style

| Model | T | Drv | P |
|-------|---|-----|---|
| `unsloth/DeepSeek-V3-GGUF` | C | d5 | 4 |

---

## Notes

- **Duplicates across sections** are intentional only where a model truly spans roles (e.g. Leanstral: code + formal proof).
- **CoDA** entries are currently **404 on Hugging Face** under these IDs — fix or remove in registry when you have canonical `hf_repo` values.
- Source of truth: `model-archival/config/registry-specialists.yaml`.

_Regenerated from registry contents; adjust sections when you add `discipline:` tags in YAML._
