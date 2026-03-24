# Archived models — inventory

This document summarises what the **model-archival** monorepo is configured to preserve.
**Authoritative sources** are the YAML registries; this file can be regenerated from the repository root with:

`uv run --directory model-archival python3 ../scripts/generate-archived-models-doc.py`

**Last regenerated:** 2026-03-24

---

## Scope across subprojects

| Subproject | What is archived | Authoritative file | Scale (this snapshot) |
| ---------- | ---------------- | ------------------ | --------------------- |
| **model-archival** | Full Hugging Face weight trees (safetensors / GGUF) | `model-archival/config/registry.yaml` | **171** registry rows (**170** unique `id` values) |
| **model-archival** (legacy queue) | Older or superseded chat models (optional `--registry` / `--include-legacy`) | `model-archival/config/registry-legacy.yaml` | **13** models |
| **model-archival** (specialist queue) | STEM, biomedical, legal, math, vision, reward, extended niche targets | `model-archival/config/registry-specialists.yaml` | **83** models |
| **fingerprints** | LFS SHA-256 fingerprints only (no weights) | `fingerprints/config/registry.yaml` | **~2,769** repos (see file header; leaderboard-scale) |
| **code-archival** | GitHub tarballs + shallow clones of AI tooling | `code-archival/registry.yaml` | **245** projects |
| **gdrive-archival** | Optional cloud replica of selected trees | `gdrive-archival/gdrive-registry.yaml`, staging dirs | varies |

**Download state** (pending / complete / failed) for weights lives on the metadata drive in `run_state.json`, not in this repo.

---

## Tier counts (master weight registry)

Distribution of `tier` in `registry.yaml` (rows, not unique ids):

| Tier | Role (summary) | Count |
| ---- | -------------- | ----- |
| **A** | Frontier general / instruct / MoE bases | 69 |
| **B** | Code models, embeddings, some tabular | 20 |
| **C** | GGUF quant checkpoints (bartowski / unsloth / tensorblock / Qwen releases) | 28 |
| **D** | Uncensored / abliterated / merges + some large Nemotron (drive placement) | 24 |
| **E** | Reasoning, long-CoT, guards | 6 |
| **F** | Vision, multimodal, medical VL | 8 |
| **G** | Math, chemistry, diffusion code, research | 16 |


> **Note:** The master registry has `171` rows but only `170` distinct `id` values (`open-r1/OlympicCoder-32B` appears twice). Consider deduplicating `registry.yaml`.

---

## Uncensored, abliterated, and alignment-relaxed weights

These are **community or merge models** aimed at reduced refusals, abliterated instruction tuning,
Dolphin-family uncensored chat, or related GGUF packs. They are the subset of **tier D** that matches
abliteration / Dolphin / huihui-ai / tensorblock / similar naming (**19** models).

- `CombinHorizon/zetasepic-abliteratedV2-Qwen2.5-32B-Inst-BaseMerge-TIES`
- `FINGU-AI/Chocolatine-Fusion-14B`
- `FINGU-AI/RomboUltima-32B`
- `cognitivecomputations/Dolphin3.0-Llama3.1-8B`
- `cognitivecomputations/dolphin-2.9.2-qwen2-72b`
- `failspy/Meta-Llama-3-70B-Instruct-abliterated-v3.5`
- `huihui-ai/DeepSeek-R1-Distill-Llama-70B-abliterated`
- `huihui-ai/DeepSeek-R1-Distill-Qwen-32B-abliterated`
- `huihui-ai/Llama-3.3-70B-Instruct-abliterated`
- `huihui-ai/Mistral-Small-24B-Instruct-2501-abliterated`
- `huihui-ai/Qwen2.5-72B-Instruct-abliterated`
- `mlabonne/Llama-3.1-70B-Instruct-lorablated`
- `mlabonne/NeuralDaredevil-8B-abliterated`
- `mlabonne/NeuralDaredevil-8B-abliterated-GGUF`
- `rombodawg/Rombos-LLM-V2.5-Qwen-72b`
- `tensorblock/DeepSeek-R1-Distill-Llama-70B-abliterated-GGUF`
- `tensorblock/DeepSeek-R1-Distill-Qwen-32B-abliterated-GGUF`
- `tensorblock/Llama-3.3-70B-Instruct-abliterated-GGUF`
- `tensorblock/Mistral-Small-24B-Instruct-2501-abliterated-GGUF`

### Tier D — large checkpoints (not “uncensored” branding)

The remaining **tier D** rows are **NVIDIA Nemotron** scale checkpoints grouped on tier D for capacity / policy; they are not abliterated variants.

- `nvidia/Llama-3_1-Nemotron-Ultra-253B-v1`
- `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16`
- `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-Base-BF16`
- `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8`
- `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4`

---

## Specialty and domain models

### By tier in the master registry

**Tier E — reasoning, games / long CoT**

- `Qwen/QwQ-32B`
- `mistralai/Leanstral-120B-A6B`
- `open-r1/OlympicCoder-32B`

**Tier E — safety / guardrails**

- `meta-llama/Llama-Guard-4-12B`
- `meta-llama/Llama-Prompt-Guard-2-22M`
- `meta-llama/Llama-Prompt-Guard-2-86M`

**Tier F — vision, multimodal, medical VL**

- `Qwen/Qwen2.5-VL-72B-Instruct`
- `Qwen/Qwen2.5-VL-7B-Instruct`
- `deepseek-ai/deepseek-vl2`
- `google/gemma-3-4b-it`
- `google/medgemma-27b-it`
- `google/medgemma-4b-it`
- `meta-llama/Llama-3.2-11B-Vision-Instruct`
- `meta-llama/Llama-3.2-90B-Vision-Instruct`

**Tier G — math, chemistry, code-diffusion, tabular, research**

- `HuggingFaceH4/zephyr-7b-beta`
- `Intel/neural-chat-7b-v3-1`
- `OpenDFM/ChemDFM-v1.5-8B`
- `OpenDFM/ChemDFM-v2.0-14B`
- `OpenDFM/RetroDFM-R-v0-8B`
- `Prior-Labs/TabPFN-v2-clf`
- `Qwen/Qwen2.5-Math-72B-Instruct`
- `Qwen/Qwen2.5-Math-7B-Instruct`
- `Salesforce/CoDA-1.7B-Base`
- `Salesforce/CoDA-1.7B-Instruct`
- `apple/DiffuCoder-7B-Base`
- `apple/DiffuCoder-7B-Instruct`
- `apple/DiffuCoder-7B-cpGRPO`
- `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B`
- `google/medgemma-27b-text-it`
- `xai-org/grok-2`

### Specialist registry (`registry-specialists.yaml`)

Curated queue for **biomedical**, **chemistry**, **legal**, **math**, **embeddings**, **vision**,
**reward models**, **DBRX**, **Grok**, Nemotron variants, and related GGUF / abliterated complements.
Many entries overlap the master list; use this file when running a **specialist-first** download pass.

- `AI4Chem/ChemLLM-7B-Chat`
- `Alibaba-NLP/gte-Qwen2-7B-instruct`
- `BAAI/bge-en-icl`
- `BAAI/bge-large-en-v1.5`
- `BAAI/bge-m3`
- `EleutherAI/llemma_7b`
- `Equall/Saul-7B-Instruct-v1`
- `FINGU-AI/RomboUltima-32B`
- `FreedomIntelligence/HuatuoGPT2-7B`
- `HuggingFaceH4/zephyr-7b-beta`
- `Intel/neural-chat-7b-v3-1`
- `OpenDFM/ChemDFM-v1.5-8B`
- `OpenDFM/ChemDFM-v2.0-14B`
- `OpenDFM/RetroDFM-R-v0-8B`
- `Qwen/QwQ-32B`
- `Qwen/Qwen2.5-Math-1.5B`
- `Qwen/Qwen2.5-Math-72B-Instruct`
- `Qwen/Qwen2.5-Math-7B-Instruct`
- `Qwen/Qwen2.5-VL-72B-Instruct`
- `Qwen/Qwen2.5-VL-7B-Instruct`
- `Salesforce/CoDA-1.7B-Base`
- `Salesforce/CoDA-1.7B-Instruct`
- `SinclairSchneider/dbrx-base-quantization-fixed`
- `SinclairSchneider/dbrx-instruct-quantization-fixed`
- `Skywork/Skywork-Reward-Llama-3.1-70B`
- `Undi95/dbrx-base`
- `aaditya/Llama3-OpenBioLLM-8B`
- `allenai/OLMo-2-1124-7B`
- `alpindale/dbrx-instruct`
- `apple/DiffuCoder-7B-Base`
- `apple/DiffuCoder-7B-Instruct`
- `apple/DiffuCoder-7B-cpGRPO`
- `bartowski/google_gemma-3-27b-it-GGUF`
- `cambridgeltl/SapBERT-from-PubMedBERT-fulltext`
- `cognitivecomputations/dolphin-2.9.2-qwen2-72b`
- `deepseek-ai/DeepSeek-R1-Distill-Llama-8B`
- `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B`
- `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B`
- `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B`
- `deepseek-ai/deepseek-coder-6.7b-instruct`
- `deepseek-ai/deepseek-math-7b-instruct`
- `deepseek-ai/deepseek-vl2`
- `dmis-lab/biobert-base-cased-v1.2`
- `emilyalsentzer/Bio_ClinicalBERT`
- `failspy/Meta-Llama-3-70B-Instruct-abliterated-v3.5`
- `google/gemma-3-4b-it`
- `google/medgemma-27b-it`
- `google/medgemma-27b-text-it`
- `google/medgemma-4b-it`
- `intfloat/e5-mistral-7b-instruct`
- `jinaai/jina-embeddings-v3`
- `meta-llama/Llama-3.2-11B-Vision-Instruct`
- `meta-llama/Llama-3.2-90B-Vision-Instruct`
- `meta-llama/Llama-Guard-4-12B`
- `meta-llama/Llama-Prompt-Guard-2-22M`
- `microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext`
- `mistralai/Leanstral-120B-A6B`
- `mistralai/Mathstral-7B-v0.1`
- `mistralai/Mistral-Small-24B-Instruct-2501`
- `mlabonne/NeuralDaredevil-8B-abliterated-GGUF`
- `mlx-community/dbrx-instruct-4bit`
- `nvidia/Llama-3_1-Nemotron-Ultra-253B-v1`
- `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16`
- `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-Base-BF16`
- `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8`
- `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16`
- `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-Base-BF16`
- `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8`
- `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4`
- `rombodawg/Rombos-LLM-V2.5-Qwen-72b`
- `seyonec/ChemBERTa-zinc-base-v1`
- `stanford-crfm/BioMedLM`
- `tensorblock/DeepSeek-R1-Distill-Llama-70B-abliterated-GGUF`
- `tensorblock/DeepSeek-R1-Distill-Qwen-32B-abliterated-GGUF`
- `tensorblock/Llama-3.2-3B-Instruct-GGUF`
- `tensorblock/Llama-3.3-70B-Instruct-abliterated-GGUF`
- `tensorblock/Mistral-Small-24B-Instruct-2501-abliterated-GGUF`
- `unsloth/DeepSeek-R1-GGUF`
- `unsloth/DeepSeek-V3-GGUF`
- `unsloth/Phi-4-mini-instruct-GGUF`
- `unsloth/Qwen3-4B-Instruct-2507-GGUF`
- `unsloth/phi-4-unsloth-bnb-4bit`
- `xai-org/grok-2`

---

## Legacy registry (`registry-legacy.yaml`)

Excluded from default `--all` runs unless you pass the legacy registry and `--include-legacy`.
**13** models:

- `01-ai/Yi-34B-Chat`
- `CohereForAI/c4ai-command-r-plus`
- `HuggingFaceH4/zephyr-7b-beta`
- `Intel/neural-chat-7b-v3-1`
- `NovaSky-Berkeley/Sky-T1-32B-Preview`
- `Qwen/Qwen1.5-110B`
- `THUDM/glm-4-9b-chat`
- `TinyLlama/TinyLlama-1.1B-Chat-v1.0`
- `bigcode/starcoder2-15b`
- `internlm/internlm2_5-20b-chat`
- `microsoft/Phi-3-mini-128k-instruct`
- `tiiuae/Falcon3-10B-Instruct`
- `upstage/solar-pro-preview-instruct`

---

## Complete master list (`registry.yaml`)

All **unique** `id` values in the master registry (**170** models):

- `01-ai/Yi-34B-Chat`
- `Alibaba-NLP/gte-Qwen2-7B-instruct`
- `BAAI/bge-en-icl`
- `BAAI/bge-large-en-v1.5`
- `BAAI/bge-m3`
- `CohereLabs/c4ai-command-r-plus-08-2024`
- `CombinHorizon/zetasepic-abliteratedV2-Qwen2.5-32B-Inst-BaseMerge-TIES`
- `FINGU-AI/Chocolatine-Fusion-14B`
- `FINGU-AI/RomboUltima-32B`
- `HuggingFaceH4/zephyr-7b-beta`
- `HuggingFaceTB/SmolLM2-1.7B-Instruct`
- `Intel/neural-chat-7b-v3-1`
- `IntervitensInc/internlm2_5-20b-llamafied`
- `OpenDFM/ChemDFM-v1.5-8B`
- `OpenDFM/ChemDFM-v2.0-14B`
- `OpenDFM/RetroDFM-R-v0-8B`
- `Prior-Labs/TabPFN-v2-clf`
- `Qwen/QwQ-32B`
- `Qwen/QwQ-32B-GGUF`
- `Qwen/Qwen2.5-14B`
- `Qwen/Qwen2.5-14B-Instruct`
- `Qwen/Qwen2.5-14B-Instruct-1M`
- `Qwen/Qwen2.5-32B`
- `Qwen/Qwen2.5-32B-Instruct`
- `Qwen/Qwen2.5-3B`
- `Qwen/Qwen2.5-72B`
- `Qwen/Qwen2.5-72B-Instruct`
- `Qwen/Qwen2.5-7B`
- `Qwen/Qwen2.5-7B-Instruct`
- `Qwen/Qwen2.5-Coder-32B-Instruct`
- `Qwen/Qwen2.5-Math-72B-Instruct`
- `Qwen/Qwen2.5-Math-7B-Instruct`
- `Qwen/Qwen2.5-VL-72B-Instruct`
- `Qwen/Qwen2.5-VL-7B-Instruct`
- `Qwen/Qwen3-14B`
- `Qwen/Qwen3-235B-A22B`
- `Qwen/Qwen3-30B-A3B`
- `Qwen/Qwen3-32B`
- `Qwen/Qwen3-32B-GGUF`
- `Qwen/Qwen3-4B-Instruct-2507`
- `Qwen/Qwen3-8B`
- `Qwen/Qwen3-Coder-30B-A3B-Instruct`
- `Salesforce/CoDA-1.7B-Base`
- `Salesforce/CoDA-1.7B-Instruct`
- `SinclairSchneider/dbrx-base-quantization-fixed`
- `SinclairSchneider/dbrx-instruct-quantization-fixed`
- `Skywork/Skywork-Reward-Llama-3.1-70B`
- `THUDM/glm-4-9b-chat`
- `TinyLlama/TinyLlama-1.1B-Chat-v1.0`
- `Undi95/dbrx-base`
- `allenai/Llama-3.1-Tulu-3-70B`
- `alpindale/dbrx-instruct`
- `apple/DiffuCoder-7B-Base`
- `apple/DiffuCoder-7B-Instruct`
- `apple/DiffuCoder-7B-cpGRPO`
- `bartowski/Codestral-22B-v0.1-GGUF`
- `bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF`
- `bartowski/DeepSeek-R1-Distill-Llama-70B-GGUF`
- `bartowski/DeepSeek-R1-Distill-Qwen-32B-GGUF`
- `bartowski/Llama-3.3-70B-Instruct-GGUF`
- `bartowski/Meta-Llama-3.1-8B-Instruct-GGUF`
- `bartowski/Mistral-Small-24B-Instruct-2501-GGUF`
- `bartowski/Qwen2.5-14B-Instruct-GGUF`
- `bartowski/Qwen2.5-32B-Instruct-GGUF`
- `bartowski/Qwen2.5-72B-Instruct-GGUF`
- `bartowski/Qwen2.5-7B-Instruct-GGUF`
- `bartowski/Qwen2.5-Coder-32B-Instruct-GGUF`
- `bartowski/google_gemma-3-27b-it-GGUF`
- `bartowski/phi-4-GGUF`
- `bigcode/starcoder2-15b`
- `cognitivecomputations/Dolphin3.0-Llama3.1-8B`
- `cognitivecomputations/dolphin-2.9.2-qwen2-72b`
- `deepseek-ai/DeepSeek-Coder-V2-Instruct`
- `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct`
- `deepseek-ai/DeepSeek-R1`
- `deepseek-ai/DeepSeek-R1-0528`
- `deepseek-ai/DeepSeek-R1-Distill-Llama-70B`
- `deepseek-ai/DeepSeek-R1-Distill-Llama-8B`
- `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B`
- `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B`
- `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B`
- `deepseek-ai/DeepSeek-V3`
- `deepseek-ai/DeepSeek-V3-0324`
- `deepseek-ai/DeepSeek-V3-Base`
- `deepseek-ai/deepseek-coder-33b-instruct`
- `deepseek-ai/deepseek-coder-6.7b-instruct`
- `deepseek-ai/deepseek-vl2`
- `failspy/Meta-Llama-3-70B-Instruct-abliterated-v3.5`
- `google/gemma-3-12b-it`
- `google/gemma-3-27b-it`
- `google/gemma-3-27b-pt`
- `google/gemma-3-4b-it`
- `google/medgemma-27b-it`
- `google/medgemma-27b-text-it`
- `google/medgemma-4b-it`
- `huihui-ai/DeepSeek-R1-Distill-Llama-70B-abliterated`
- `huihui-ai/DeepSeek-R1-Distill-Qwen-32B-abliterated`
- `huihui-ai/Llama-3.3-70B-Instruct-abliterated`
- `huihui-ai/Mistral-Small-24B-Instruct-2501-abliterated`
- `huihui-ai/Qwen2.5-72B-Instruct-abliterated`
- `ibm-granite/granite-20b-code-base-8k`
- `ibm-granite/granite-20b-code-instruct-r1.1`
- `internlm/internlm2_5-20b-chat`
- `intfloat/e5-large-v2`
- `intfloat/e5-mistral-7b-instruct`
- `meta-llama/Llama-3.1-405B`
- `meta-llama/Llama-3.1-405B-Instruct`
- `meta-llama/Llama-3.1-70B-Instruct`
- `meta-llama/Llama-3.1-8B-Instruct`
- `meta-llama/Llama-3.2-11B-Vision-Instruct`
- `meta-llama/Llama-3.2-1B`
- `meta-llama/Llama-3.2-1B-Instruct`
- `meta-llama/Llama-3.2-3B-Instruct`
- `meta-llama/Llama-3.2-90B-Vision-Instruct`
- `meta-llama/Llama-3.3-70B-Instruct`
- `meta-llama/Llama-4-Maverick-17B-128E`
- `meta-llama/Llama-4-Maverick-17B-128E-Instruct`
- `meta-llama/Llama-4-Scout-17B-16E`
- `meta-llama/Llama-4-Scout-17B-16E-Instruct`
- `meta-llama/Llama-Guard-4-12B`
- `meta-llama/Llama-Prompt-Guard-2-22M`
- `meta-llama/Llama-Prompt-Guard-2-86M`
- `microsoft/Phi-3-mini-128k-instruct`
- `microsoft/Phi-4-mini-instruct`
- `microsoft/phi-4`
- `mistralai/Codestral-22B-v0.1`
- `mistralai/Devstral-Small-2507`
- `mistralai/Devstral-Small-2507_gguf`
- `mistralai/Leanstral-120B-A6B`
- `mistralai/Mistral-Large-Instruct-2411`
- `mistralai/Mistral-Small-24B-Instruct-2501`
- `mistralai/Mixtral-8x22B-Instruct-v0.1`
- `mistralai/Mixtral-8x7B-Instruct-v0.1`
- `mlabonne/Llama-3.1-70B-Instruct-lorablated`
- `mlabonne/NeuralDaredevil-8B-abliterated`
- `mlabonne/NeuralDaredevil-8B-abliterated-GGUF`
- `mlx-community/dbrx-instruct-4bit`
- `mosaicml/mpt-30b`
- `mosaicml/mpt-30b-instruct`
- `mosaicml/mpt-7b`
- `mosaicml/mpt-7b-instruct`
- `nvidia/Llama-3.1-Nemotron-70B-Instruct`
- `nvidia/Llama-3_1-Nemotron-Ultra-253B-v1`
- `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16`
- `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-Base-BF16`
- `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8`
- `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4`
- `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16`
- `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-Base-BF16`
- `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8`
- `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4`
- `open-r1/OlympicCoder-32B`
- `rombodawg/Rombos-LLM-V2.5-Qwen-72b`
- `sentence-transformers/all-mpnet-base-v2`
- `tensorblock/DeepSeek-R1-Distill-Llama-70B-abliterated-GGUF`
- `tensorblock/DeepSeek-R1-Distill-Qwen-32B-abliterated-GGUF`
- `tensorblock/Llama-3.2-3B-Instruct-GGUF`
- `tensorblock/Llama-3.3-70B-Instruct-abliterated-GGUF`
- `tensorblock/Mistral-Small-24B-Instruct-2501-abliterated-GGUF`
- `tiiuae/Falcon3-10B-Instruct`
- `tiiuae/falcon-180B`
- `tiiuae/falcon-180B-chat`
- `tiiuae/falcon-40b-instruct`
- `unsloth/DeepSeek-R1-GGUF`
- `unsloth/DeepSeek-V3-GGUF`
- `unsloth/Phi-4-mini-instruct-GGUF`
- `unsloth/Qwen3-4B-Instruct-2507-GGUF`
- `unsloth/phi-4-unsloth-bnb-4bit`
- `upstage/solar-pro-preview-instruct`
- `xai-org/grok-2`
