# Archived models — inventory

This document summarises what the **model-archival** monorepo is configured to preserve.
**Authoritative sources** are the YAML registries; this file can be regenerated from the repository root with:

`uv run --directory model-archival python3 ../scripts/generate-archived-models-doc.py`

Optional: point at your archive host’s state and mounts:

`ARCHIVER_RUN_STATE=/mnt/models/d5/run_state.json ARCHIVER_MODELS_MOUNT=/mnt/models uv run --directory model-archival python3 ../scripts/generate-archived-models-doc.py`

**Machine-readable inventory (per-drive JSON, manifest digests, disk scan, code-archival list):** [`docs/archive-inventory/`](archive-inventory/README.md) — regenerate with `uv run --directory model-archival python3 ../scripts/generate-archive-inventory.py`.

**Last regenerated:** 2026-03-24

---

## Scope across subprojects

| Subproject | What is archived | Authoritative file | Scale (this snapshot) |
| ---------- | ---------------- | ------------------ | --------------------- |
| **model-archival** | Full Hugging Face weight trees (safetensors / GGUF) | `model-archival/config/registry.yaml` | **170** registry rows (**170** unique `id` values) |
| **model-archival** (legacy queue) | Older or superseded chat models (optional `--registry` / `--include-legacy`) | `model-archival/config/registry-legacy.yaml` | **13** models |
| **model-archival** (specialist queue) | STEM, biomedical, legal, math, vision, reward, extended niche targets | `model-archival/config/registry-specialists.yaml` | **83** models |
| **fingerprints** | LFS SHA-256 fingerprints only (no weights) | `fingerprints/config/registry.yaml` | **~2,769** repos (see file header; leaderboard-scale) |
| **code-archival** | GitHub tarballs + shallow clones of AI tooling | `code-archival/registry.yaml` | **245** projects |
| **gdrive-archival** | Optional cloud replica of selected trees | `gdrive-archival/gdrive-registry.yaml`, staging dirs | varies |

Live **per-model download status** is normally on the metadata drive: `run_state.json`. This doc embeds a snapshot when that file (and optionally the GDrive tracker) is visible to the generator.

---

## Tier counts (master weight registry)

Distribution of `tier` in `registry.yaml` (rows, not unique ids):

| Tier | Role (summary) | Count |
| ---- | -------------- | ----- |
| **A** | Frontier general / instruct / MoE bases | 69 |
| **B** | Code models, embeddings, some tabular | 20 |
| **C** | GGUF quant checkpoints (bartowski / unsloth / tensorblock / Qwen releases) | 28 |
| **D** | Uncensored / abliterated / merges + some large Nemotron (drive placement) | 24 |
| **E** | Reasoning, long-CoT, guards | 5 |
| **F** | Vision, multimodal, medical VL | 8 |
| **G** | Math, chemistry, diffusion code, research | 16 |

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

## Paths, download status, and Google Drive

Expected layout matches `ModelEntry.model_dir` in the archiver: `<models_mount>/<drive>/<raw|quantized|uncensored>/<org>/<repo>/<rev>` where `rev` is `commit_sha` or `main` when still unpinned.

| Item | Value |
|------|-------|
| `models_mount` (this run) | `/mnt/models` |
| `run_state.json` | `/mnt/models/d5/run_state.json` *(missing on this host — no Download column)* |
| GDrive tracker | `gdrive-archival/logs/registry-upload-state.json` *(missing — no GDrive column)* |

| Model `id` | Tier | Path on disk | Dir | `manifest.json` |
| --- | --- | --- | --- | --- |
| `01-ai/Yi-34B-Chat` | A | `/mnt/models/d2/raw/01-ai/Yi-34B-Chat/main` | no | no |
| `Alibaba-NLP/gte-Qwen2-7B-instruct` | B | `/mnt/models/d3/raw/Alibaba-NLP/gte-Qwen2-7B-instruct/main` | no | no |
| `BAAI/bge-en-icl` | B | `/mnt/models/d3/raw/BAAI/bge-en-icl/main` | no | no |
| `BAAI/bge-large-en-v1.5` | B | `/mnt/models/d3/raw/BAAI/bge-large-en-v1.5/main` | no | no |
| `BAAI/bge-m3` | B | `/mnt/models/d3/raw/BAAI/bge-m3/main` | no | no |
| `CohereLabs/c4ai-command-r-plus-08-2024` | A | `/mnt/models/d2/raw/CohereLabs/c4ai-command-r-plus-08-2024/e808c1a2249354ca211c9f08d1338e5039f633f8` | no | no |
| `CombinHorizon/zetasepic-abliteratedV2-Qwen2.5-32B-Inst-BaseMerge-TIES` | D | `/mnt/models/d1/uncensored/CombinHorizon/zetasepic-abliteratedV2-Qwen2.5-32B-Inst-BaseMerge-TIES/d976a5d6768d54c5e59a88fe63238a055c30c06a` | no | no |
| `FINGU-AI/Chocolatine-Fusion-14B` | D | `/mnt/models/d1/uncensored/FINGU-AI/Chocolatine-Fusion-14B/49b7b720ddd40ccdca303922037a4bb34b1ca33b` | no | no |
| `FINGU-AI/RomboUltima-32B` | D | `/mnt/models/d3/uncensored/FINGU-AI/RomboUltima-32B/98a732a32e2366a2ab8f08fdc3d668892e7c1f7f` | no | no |
| `HuggingFaceH4/zephyr-7b-beta` | G | `/mnt/models/d3/raw/HuggingFaceH4/zephyr-7b-beta/main` | no | no |
| `HuggingFaceTB/SmolLM2-1.7B-Instruct` | A | `/mnt/models/d3/raw/HuggingFaceTB/SmolLM2-1.7B-Instruct/main` | no | no |
| `Intel/neural-chat-7b-v3-1` | G | `/mnt/models/d3/raw/Intel/neural-chat-7b-v3-1/main` | no | no |
| `IntervitensInc/internlm2_5-20b-llamafied` | A | `/mnt/models/d1/raw/IntervitensInc/internlm2_5-20b-llamafied/main` | no | no |
| `OpenDFM/ChemDFM-v1.5-8B` | G | `/mnt/models/d3/raw/OpenDFM/ChemDFM-v1.5-8B/main` | no | no |
| `OpenDFM/ChemDFM-v2.0-14B` | G | `/mnt/models/d3/raw/OpenDFM/ChemDFM-v2.0-14B/main` | no | no |
| `OpenDFM/RetroDFM-R-v0-8B` | G | `/mnt/models/d3/raw/OpenDFM/RetroDFM-R-v0-8B/main` | no | no |
| `Prior-Labs/TabPFN-v2-clf` | G | `/mnt/models/d3/raw/Prior-Labs/TabPFN-v2-clf/main` | no | no |
| `Qwen/QwQ-32B` | E | `/mnt/models/d3/raw/Qwen/QwQ-32B/976055f8c83f394f35dbd3ab09a285a984907bd0` | no | no |
| `Qwen/QwQ-32B-GGUF` | C | `/mnt/models/d3/quantized/Qwen/QwQ-32B-GGUF/8728e66249190b78dee8404869827328527f6b3b` | no | no |
| `Qwen/Qwen2.5-14B` | A | `/mnt/models/d1/raw/Qwen/Qwen2.5-14B/97e1e76335b7017d8f67c08a19d103c0504298c9` | no | no |
| `Qwen/Qwen2.5-14B-Instruct` | A | `/mnt/models/d2/raw/Qwen/Qwen2.5-14B-Instruct/cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8` | no | no |
| `Qwen/Qwen2.5-14B-Instruct-1M` | A | `/mnt/models/d2/raw/Qwen/Qwen2.5-14B-Instruct-1M/620fad32de7bdd2293b3d99b39eba2fe63e97438` | no | no |
| `Qwen/Qwen2.5-32B` | A | `/mnt/models/d1/raw/Qwen/Qwen2.5-32B/1818d35814b8319459f4bd55ed1ac8709630f003` | no | no |
| `Qwen/Qwen2.5-32B-Instruct` | A | `/mnt/models/d2/raw/Qwen/Qwen2.5-32B-Instruct/5ede1c97bbab6ce5cda5812749b4c0bdf79b18dd` | no | no |
| `Qwen/Qwen2.5-3B` | A | `/mnt/models/d1/raw/Qwen/Qwen2.5-3B/main` | no | no |
| `Qwen/Qwen2.5-72B` | A | `/mnt/models/d2/raw/Qwen/Qwen2.5-72B/main` | no | no |
| `Qwen/Qwen2.5-72B-Instruct` | A | `/mnt/models/d2/raw/Qwen/Qwen2.5-72B-Instruct/495f39366efef23836d0cfae4fbe635880d2be31` | no | no |
| `Qwen/Qwen2.5-7B` | A | `/mnt/models/d1/raw/Qwen/Qwen2.5-7B/main` | no | no |
| `Qwen/Qwen2.5-7B-Instruct` | A | `/mnt/models/d2/raw/Qwen/Qwen2.5-7B-Instruct/a09a35458c702b33eeacc393d103063234e8bc28` | no | no |
| `Qwen/Qwen2.5-Coder-32B-Instruct` | B | `/mnt/models/d2/raw/Qwen/Qwen2.5-Coder-32B-Instruct/main` | no | no |
| `Qwen/Qwen2.5-Math-72B-Instruct` | G | `/mnt/models/d5/raw/Qwen/Qwen2.5-Math-72B-Instruct/main` | no | no |
| `Qwen/Qwen2.5-Math-7B-Instruct` | G | `/mnt/models/d3/raw/Qwen/Qwen2.5-Math-7B-Instruct/main` | no | no |
| `Qwen/Qwen2.5-VL-72B-Instruct` | F | `/mnt/models/d5/raw/Qwen/Qwen2.5-VL-72B-Instruct/main` | no | no |
| `Qwen/Qwen2.5-VL-7B-Instruct` | F | `/mnt/models/d3/raw/Qwen/Qwen2.5-VL-7B-Instruct/main` | no | no |
| `Qwen/Qwen3-14B` | A | `/mnt/models/d2/raw/Qwen/Qwen3-14B/40c069824f4251a91eefaf281ebe4c544efd3e18` | no | no |
| `Qwen/Qwen3-235B-A22B` | A | `/mnt/models/d1/raw/Qwen/Qwen3-235B-A22B/main` | no | no |
| `Qwen/Qwen3-30B-A3B` | A | `/mnt/models/d2/raw/Qwen/Qwen3-30B-A3B/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39` | no | no |
| `Qwen/Qwen3-32B` | A | `/mnt/models/d1/raw/Qwen/Qwen3-32B/9216db5781bf21249d130ec9da846c4624c16137` | no | no |
| `Qwen/Qwen3-32B-GGUF` | C | `/mnt/models/d3/quantized/Qwen/Qwen3-32B-GGUF/938a7432affaec9157f883a87164e2646ae17555` | no | no |
| `Qwen/Qwen3-4B-Instruct-2507` | A | `/mnt/models/d5/raw/Qwen/Qwen3-4B-Instruct-2507/main` | no | no |
| `Qwen/Qwen3-8B` | A | `/mnt/models/d2/raw/Qwen/Qwen3-8B/b968826d9c46dd6066d109eabc6255188de91218` | no | no |
| `Qwen/Qwen3-Coder-30B-A3B-Instruct` | B | `/mnt/models/d2/raw/Qwen/Qwen3-Coder-30B-A3B-Instruct/b2cff646eb4bb1d68355c01b18ae02e7cf42d120` | no | no |
| `Salesforce/CoDA-1.7B-Base` | G | `/mnt/models/d3/raw/Salesforce/CoDA-1.7B-Base/main` | no | no |
| `Salesforce/CoDA-1.7B-Instruct` | G | `/mnt/models/d3/raw/Salesforce/CoDA-1.7B-Instruct/main` | no | no |
| `SinclairSchneider/dbrx-base-quantization-fixed` | C | `/mnt/models/d3/quantized/SinclairSchneider/dbrx-base-quantization-fixed/main` | no | no |
| `SinclairSchneider/dbrx-instruct-quantization-fixed` | C | `/mnt/models/d3/quantized/SinclairSchneider/dbrx-instruct-quantization-fixed/main` | no | no |
| `Skywork/Skywork-Reward-Llama-3.1-70B` | B | `/mnt/models/d5/raw/Skywork/Skywork-Reward-Llama-3.1-70B/main` | no | no |
| `THUDM/glm-4-9b-chat` | A | `/mnt/models/d2/raw/THUDM/glm-4-9b-chat/main` | no | no |
| `TinyLlama/TinyLlama-1.1B-Chat-v1.0` | A | `/mnt/models/d3/raw/TinyLlama/TinyLlama-1.1B-Chat-v1.0/main` | no | no |
| `Undi95/dbrx-base` | A | `/mnt/models/d5/raw/Undi95/dbrx-base/main` | no | no |
| `allenai/Llama-3.1-Tulu-3-70B` | A | `/mnt/models/d2/raw/allenai/Llama-3.1-Tulu-3-70B/cfc1d855e534a0b9b82a9cea6bf9e8dda30b10d7` | no | no |
| `alpindale/dbrx-instruct` | A | `/mnt/models/d5/raw/alpindale/dbrx-instruct/main` | no | no |
| `apple/DiffuCoder-7B-Base` | G | `/mnt/models/d3/raw/apple/DiffuCoder-7B-Base/main` | no | no |
| `apple/DiffuCoder-7B-Instruct` | G | `/mnt/models/d3/raw/apple/DiffuCoder-7B-Instruct/main` | no | no |
| `apple/DiffuCoder-7B-cpGRPO` | G | `/mnt/models/d3/raw/apple/DiffuCoder-7B-cpGRPO/main` | no | no |
| `bartowski/Codestral-22B-v0.1-GGUF` | C | `/mnt/models/d3/quantized/bartowski/Codestral-22B-v0.1-GGUF/0e6abe14d6aeaf2c99d5dc9973205e8e38692d90` | no | no |
| `bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF` | C | `/mnt/models/d3/quantized/bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF/8f248fa2072348f77a8bc37754e470de1f61866e` | no | no |
| `bartowski/DeepSeek-R1-Distill-Llama-70B-GGUF` | C | `/mnt/models/d3/quantized/bartowski/DeepSeek-R1-Distill-Llama-70B-GGUF/1842c5f7280f933ead58adf8afd078672c9f6cd0` | no | no |
| `bartowski/DeepSeek-R1-Distill-Qwen-32B-GGUF` | C | `/mnt/models/d3/quantized/bartowski/DeepSeek-R1-Distill-Qwen-32B-GGUF/1dc8cf9ffa5dd333057ea1b09ccf4772d8726dec` | no | no |
| `bartowski/Llama-3.3-70B-Instruct-GGUF` | C | `/mnt/models/d3/quantized/bartowski/Llama-3.3-70B-Instruct-GGUF/b6c5c9f176f3279204034e1d16d393105e95cb88` | no | no |
| `bartowski/Meta-Llama-3.1-8B-Instruct-GGUF` | C | `/mnt/models/d3/quantized/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/bf5b95e96dac0462e2a09145ec66cae9a3f12067` | no | no |
| `bartowski/Mistral-Small-24B-Instruct-2501-GGUF` | C | `/mnt/models/d3/quantized/bartowski/Mistral-Small-24B-Instruct-2501-GGUF/62a613c92d5a5f73bba6d348b51433b232c4640c` | no | no |
| `bartowski/Qwen2.5-14B-Instruct-GGUF` | C | `/mnt/models/d3/quantized/bartowski/Qwen2.5-14B-Instruct-GGUF/05244aa5d871c661c80082a15d3bce44714d068d` | no | no |
| `bartowski/Qwen2.5-32B-Instruct-GGUF` | C | `/mnt/models/d3/quantized/bartowski/Qwen2.5-32B-Instruct-GGUF/2116cbb385b8ce3a4d28cf3bf1cd2039a55821a6` | no | no |
| `bartowski/Qwen2.5-72B-Instruct-GGUF` | C | `/mnt/models/d3/quantized/bartowski/Qwen2.5-72B-Instruct-GGUF/d43fd973131bce821f41e2df3c78c6fe15c5627a` | no | no |
| `bartowski/Qwen2.5-7B-Instruct-GGUF` | C | `/mnt/models/d3/quantized/bartowski/Qwen2.5-7B-Instruct-GGUF/8911e8a47f92bac19d6f5c64a2e2095bd2f7d031` | no | no |
| `bartowski/Qwen2.5-Coder-32B-Instruct-GGUF` | C | `/mnt/models/d3/quantized/bartowski/Qwen2.5-Coder-32B-Instruct-GGUF/40b525506a4f98ed425882fa6dfc90cc8139065e` | no | no |
| `bartowski/google_gemma-3-27b-it-GGUF` | C | `/mnt/models/d3/quantized/bartowski/google_gemma-3-27b-it-GGUF/4a05c54413bd0d87d77a97af403266f69cec0ee6` | no | no |
| `bartowski/phi-4-GGUF` | C | `/mnt/models/d3/quantized/bartowski/phi-4-GGUF/19cd65f97c2f1712a81c506611d3f9c94b16a1e1` | no | no |
| `bigcode/starcoder2-15b` | B | `/mnt/models/d2/raw/bigcode/starcoder2-15b/46d44742909c03ac8cee08eb03fdebce02e193ec` | no | no |
| `cognitivecomputations/Dolphin3.0-Llama3.1-8B` | D | `/mnt/models/d2/uncensored/cognitivecomputations/Dolphin3.0-Llama3.1-8B/f065677950dfc7e708d518d64cf1f5041ee007a0` | no | no |
| `cognitivecomputations/dolphin-2.9.2-qwen2-72b` | D | `/mnt/models/d5/uncensored/cognitivecomputations/dolphin-2.9.2-qwen2-72b/main` | no | no |
| `deepseek-ai/DeepSeek-Coder-V2-Instruct` | B | `/mnt/models/d1/raw/deepseek-ai/DeepSeek-Coder-V2-Instruct/2453c79a2a0947968a054947b53daa598cb3be52` | no | no |
| `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct` | B | `/mnt/models/d2/raw/deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct/e434a23f91ba5b4923cf6c9d9a238eb4a08e3a11` | no | no |
| `deepseek-ai/DeepSeek-R1` | A | `/mnt/models/d1/raw/deepseek-ai/DeepSeek-R1/56d4cbbb4d29f4355bab4b9a39ccb717a14ad5ad` | no | no |
| `deepseek-ai/DeepSeek-R1-0528` | A | `/mnt/models/d1/raw/deepseek-ai/DeepSeek-R1-0528/4236a6af538feda4548eca9ab308586007567f52` | no | no |
| `deepseek-ai/DeepSeek-R1-Distill-Llama-70B` | A | `/mnt/models/d2/raw/deepseek-ai/DeepSeek-R1-Distill-Llama-70B/b1c0b44b4369b597ad119a196caf79a9c40e141e` | no | no |
| `deepseek-ai/DeepSeek-R1-Distill-Llama-8B` | A | `/mnt/models/d2/raw/deepseek-ai/DeepSeek-R1-Distill-Llama-8B/6a6f4aa4197940add57724a7707d069478df56b1` | no | no |
| `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B` | A | `/mnt/models/d2/raw/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B/1df8507178afcc1bef68cd8c393f61a886323761` | no | no |
| `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` | A | `/mnt/models/d2/raw/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B/711ad2ea6aa40cfca18895e8aca02ab92df1a746` | no | no |
| `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` | G | `/mnt/models/d3/raw/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B/main` | no | no |
| `deepseek-ai/DeepSeek-V3` | A | `/mnt/models/d1/raw/deepseek-ai/DeepSeek-V3/e815299b0bcbac849fa540c768ef21845365c9eb` | no | no |
| `deepseek-ai/DeepSeek-V3-0324` | A | `/mnt/models/d1/raw/deepseek-ai/DeepSeek-V3-0324/main` | no | no |
| `deepseek-ai/DeepSeek-V3-Base` | A | `/mnt/models/d1/raw/deepseek-ai/DeepSeek-V3-Base/main` | no | no |
| `deepseek-ai/deepseek-coder-33b-instruct` | B | `/mnt/models/d1/raw/deepseek-ai/deepseek-coder-33b-instruct/61dc97b922b13995e7f83b7c8397701dbf9cfd4c` | no | no |
| `deepseek-ai/deepseek-coder-6.7b-instruct` | B | `/mnt/models/d3/raw/deepseek-ai/deepseek-coder-6.7b-instruct/e5d64addd26a6a1db0f9b863abf6ee3141936807` | no | no |
| `deepseek-ai/deepseek-vl2` | F | `/mnt/models/d5/raw/deepseek-ai/deepseek-vl2/main` | no | no |
| `failspy/Meta-Llama-3-70B-Instruct-abliterated-v3.5` | D | `/mnt/models/d5/uncensored/failspy/Meta-Llama-3-70B-Instruct-abliterated-v3.5/main` | no | no |
| `google/gemma-3-12b-it` | A | `/mnt/models/d2/raw/google/gemma-3-12b-it/main` | no | no |
| `google/gemma-3-27b-it` | A | `/mnt/models/d2/raw/google/gemma-3-27b-it/main` | no | no |
| `google/gemma-3-27b-pt` | A | `/mnt/models/d2/raw/google/gemma-3-27b-pt/main` | no | no |
| `google/gemma-3-4b-it` | F | `/mnt/models/d3/raw/google/gemma-3-4b-it/main` | no | no |
| `google/medgemma-27b-it` | F | `/mnt/models/d3/raw/google/medgemma-27b-it/main` | no | no |
| `google/medgemma-27b-text-it` | G | `/mnt/models/d3/raw/google/medgemma-27b-text-it/main` | no | no |
| `google/medgemma-4b-it` | F | `/mnt/models/d3/raw/google/medgemma-4b-it/main` | no | no |
| `huihui-ai/DeepSeek-R1-Distill-Llama-70B-abliterated` | D | `/mnt/models/d2/uncensored/huihui-ai/DeepSeek-R1-Distill-Llama-70B-abliterated/116ff0fa55425b094a38a6bbf6faf2f5cafea335` | no | no |
| `huihui-ai/DeepSeek-R1-Distill-Qwen-32B-abliterated` | D | `/mnt/models/d2/uncensored/huihui-ai/DeepSeek-R1-Distill-Qwen-32B-abliterated/939b7e288235a393e2aac8a16ddc3d48f9406f03` | no | no |
| `huihui-ai/Llama-3.3-70B-Instruct-abliterated` | D | `/mnt/models/d2/uncensored/huihui-ai/Llama-3.3-70B-Instruct-abliterated/fa13334669544bab573e0e5313cad629a9c02e2c` | no | no |
| `huihui-ai/Mistral-Small-24B-Instruct-2501-abliterated` | D | `/mnt/models/d2/uncensored/huihui-ai/Mistral-Small-24B-Instruct-2501-abliterated/main` | no | no |
| `huihui-ai/Qwen2.5-72B-Instruct-abliterated` | D | `/mnt/models/d3/uncensored/huihui-ai/Qwen2.5-72B-Instruct-abliterated/ff4f9fe269d95bad2bd741af23b805cd9f449a8b` | no | no |
| `ibm-granite/granite-20b-code-base-8k` | B | `/mnt/models/d2/raw/ibm-granite/granite-20b-code-base-8k/main` | no | no |
| `ibm-granite/granite-20b-code-instruct-r1.1` | B | `/mnt/models/d2/raw/ibm-granite/granite-20b-code-instruct-r1.1/main` | no | no |
| `internlm/internlm2_5-20b-chat` | A | `/mnt/models/d2/raw/internlm/internlm2_5-20b-chat/main` | no | no |
| `intfloat/e5-large-v2` | B | `/mnt/models/d3/raw/intfloat/e5-large-v2/main` | no | no |
| `intfloat/e5-mistral-7b-instruct` | B | `/mnt/models/d3/raw/intfloat/e5-mistral-7b-instruct/main` | no | no |
| `meta-llama/Llama-3.1-405B` | A | `/mnt/models/d1/raw/meta-llama/Llama-3.1-405B/b906e4dc842aa489c962f9db26554dcfdde901fe` | no | no |
| `meta-llama/Llama-3.1-405B-Instruct` | A | `/mnt/models/d1/raw/meta-llama/Llama-3.1-405B-Instruct/main` | no | no |
| `meta-llama/Llama-3.1-70B-Instruct` | A | `/mnt/models/d2/raw/meta-llama/Llama-3.1-70B-Instruct/1605565b47bb9346c5515c34102e054115b4f98b` | no | no |
| `meta-llama/Llama-3.1-8B-Instruct` | A | `/mnt/models/d2/raw/meta-llama/Llama-3.1-8B-Instruct/0e9e39f249a16976918f6564b8830bc894c89659` | no | no |
| `meta-llama/Llama-3.2-11B-Vision-Instruct` | F | `/mnt/models/d3/raw/meta-llama/Llama-3.2-11B-Vision-Instruct/main` | no | no |
| `meta-llama/Llama-3.2-1B` | A | `/mnt/models/d3/raw/meta-llama/Llama-3.2-1B/main` | no | no |
| `meta-llama/Llama-3.2-1B-Instruct` | A | `/mnt/models/d3/raw/meta-llama/Llama-3.2-1B-Instruct/main` | no | no |
| `meta-llama/Llama-3.2-3B-Instruct` | A | `/mnt/models/d2/raw/meta-llama/Llama-3.2-3B-Instruct/0cb88a4f764b7a12671c53f0838cd831a0843b95` | no | no |
| `meta-llama/Llama-3.2-90B-Vision-Instruct` | F | `/mnt/models/d5/raw/meta-llama/Llama-3.2-90B-Vision-Instruct/main` | no | no |
| `meta-llama/Llama-3.3-70B-Instruct` | A | `/mnt/models/d1/raw/meta-llama/Llama-3.3-70B-Instruct/6f6073b423013f6a7d4d9f39144961bfbfbc386b` | no | no |
| `meta-llama/Llama-4-Maverick-17B-128E` | A | `/mnt/models/d1/raw/meta-llama/Llama-4-Maverick-17B-128E/10751cb97a4d7c90f7ed89196b98eb8220cfa1c2` | no | no |
| `meta-llama/Llama-4-Maverick-17B-128E-Instruct` | A | `/mnt/models/d2/raw/meta-llama/Llama-4-Maverick-17B-128E-Instruct/main` | no | no |
| `meta-llama/Llama-4-Scout-17B-16E` | A | `/mnt/models/d1/raw/meta-llama/Llama-4-Scout-17B-16E/main` | no | no |
| `meta-llama/Llama-4-Scout-17B-16E-Instruct` | A | `/mnt/models/d2/raw/meta-llama/Llama-4-Scout-17B-16E-Instruct/main` | no | no |
| `meta-llama/Llama-Guard-4-12B` | E | `/mnt/models/d3/raw/meta-llama/Llama-Guard-4-12B/87acb4b94e930c3d679e6e7ee9d57e2feab9ea71` | no | no |
| `meta-llama/Llama-Prompt-Guard-2-22M` | E | `/mnt/models/d3/raw/meta-llama/Llama-Prompt-Guard-2-22M/11614a155199674a0a95e6602d6ab0417b790ed0` | no | no |
| `meta-llama/Llama-Prompt-Guard-2-86M` | E | `/mnt/models/d3/raw/meta-llama/Llama-Prompt-Guard-2-86M/a8ded8e697ce7c355e395a0df51f94adb4a2fd27` | no | no |
| `microsoft/Phi-3-mini-128k-instruct` | A | `/mnt/models/d3/raw/microsoft/Phi-3-mini-128k-instruct/main` | no | no |
| `microsoft/Phi-4-mini-instruct` | A | `/mnt/models/d5/raw/microsoft/Phi-4-mini-instruct/main` | no | no |
| `microsoft/phi-4` | A | `/mnt/models/d2/raw/microsoft/phi-4/main` | no | no |
| `mistralai/Codestral-22B-v0.1` | B | `/mnt/models/d2/raw/mistralai/Codestral-22B-v0.1/28b1c1a51dabe9d86ca8c41420ada1984632498f` | no | no |
| `mistralai/Devstral-Small-2507` | B | `/mnt/models/d2/raw/mistralai/Devstral-Small-2507/main` | no | no |
| `mistralai/Devstral-Small-2507_gguf` | C | `/mnt/models/d3/quantized/mistralai/Devstral-Small-2507_gguf/ee2f0c00c5c86862f471fbf533268cf01b80d4a6` | no | no |
| `mistralai/Leanstral-120B-A6B` | E | `/mnt/models/d5/raw/mistralai/Leanstral-120B-A6B/main` | no | no |
| `mistralai/Mistral-Large-Instruct-2411` | A | `/mnt/models/d1/raw/mistralai/Mistral-Large-Instruct-2411/ba78820945ae22361b0274cf0ae6d696c967c1a4` | no | no |
| `mistralai/Mistral-Small-24B-Instruct-2501` | A | `/mnt/models/d2/raw/mistralai/Mistral-Small-24B-Instruct-2501/9527884be6e5616bdd54de542f9ae13384489724` | no | no |
| `mistralai/Mixtral-8x22B-Instruct-v0.1` | A | `/mnt/models/d2/raw/mistralai/Mixtral-8x22B-Instruct-v0.1/cc88a6cc19fbd17d9f1c0ee0b0d70a748dce698d` | no | no |
| `mistralai/Mixtral-8x7B-Instruct-v0.1` | A | `/mnt/models/d2/raw/mistralai/Mixtral-8x7B-Instruct-v0.1/eba92302a2861cdc0098cc54bc9f17cb2c47eb61` | no | no |
| `mlabonne/Llama-3.1-70B-Instruct-lorablated` | D | `/mnt/models/d2/uncensored/mlabonne/Llama-3.1-70B-Instruct-lorablated/main` | no | no |
| `mlabonne/NeuralDaredevil-8B-abliterated` | D | `/mnt/models/d2/uncensored/mlabonne/NeuralDaredevil-8B-abliterated/main` | no | no |
| `mlabonne/NeuralDaredevil-8B-abliterated-GGUF` | D | `/mnt/models/d3/uncensored/mlabonne/NeuralDaredevil-8B-abliterated-GGUF/main` | no | no |
| `mlx-community/dbrx-instruct-4bit` | C | `/mnt/models/d3/quantized/mlx-community/dbrx-instruct-4bit/main` | no | no |
| `mosaicml/mpt-30b` | A | `/mnt/models/d2/raw/mosaicml/mpt-30b/main` | no | no |
| `mosaicml/mpt-30b-instruct` | A | `/mnt/models/d2/raw/mosaicml/mpt-30b-instruct/main` | no | no |
| `mosaicml/mpt-7b` | A | `/mnt/models/d2/raw/mosaicml/mpt-7b/main` | no | no |
| `mosaicml/mpt-7b-instruct` | A | `/mnt/models/d2/raw/mosaicml/mpt-7b-instruct/main` | no | no |
| `nvidia/Llama-3.1-Nemotron-70B-Instruct` | A | `/mnt/models/d2/raw/nvidia/Llama-3.1-Nemotron-70B-Instruct/a83af1f4968437064635f6726fb745e5b615e863` | no | no |
| `nvidia/Llama-3_1-Nemotron-Ultra-253B-v1` | D | `/mnt/models/d1/uncensored/nvidia/Llama-3_1-Nemotron-Ultra-253B-v1/main` | no | no |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` | A | `/mnt/models/d2/raw/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16/main` | no | no |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-Base-BF16` | A | `/mnt/models/d2/raw/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-Base-BF16/97ab8012882a655dc38df4fee47422aca9caca07` | no | no |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8` | C | `/mnt/models/d3/quantized/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8/main` | no | no |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4` | C | `/mnt/models/d3/quantized/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4/main` | no | no |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16` | D | `/mnt/models/d5/uncensored/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16/main` | no | no |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-Base-BF16` | D | `/mnt/models/d5/uncensored/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-Base-BF16/main` | no | no |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8` | D | `/mnt/models/d5/uncensored/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8/main` | no | no |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4` | D | `/mnt/models/d5/uncensored/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4/main` | no | no |
| `open-r1/OlympicCoder-32B` | B | `/mnt/models/d2/raw/open-r1/OlympicCoder-32B/34113aee9d255591a1fa75b60d1e3422e82c3b1f` | no | no |
| `rombodawg/Rombos-LLM-V2.5-Qwen-72b` | D | `/mnt/models/d5/uncensored/rombodawg/Rombos-LLM-V2.5-Qwen-72b/main` | no | no |
| `sentence-transformers/all-mpnet-base-v2` | B | `/mnt/models/d3/raw/sentence-transformers/all-mpnet-base-v2/main` | no | no |
| `tensorblock/DeepSeek-R1-Distill-Llama-70B-abliterated-GGUF` | D | `/mnt/models/d5/uncensored/tensorblock/DeepSeek-R1-Distill-Llama-70B-abliterated-GGUF/89b48f9faec5188e7a05011676538aaf0889ad9a` | no | no |
| `tensorblock/DeepSeek-R1-Distill-Qwen-32B-abliterated-GGUF` | D | `/mnt/models/d3/uncensored/tensorblock/DeepSeek-R1-Distill-Qwen-32B-abliterated-GGUF/de00cb261ea6fea79a45ffbb6e583befed7be954` | no | no |
| `tensorblock/Llama-3.2-3B-Instruct-GGUF` | C | `/mnt/models/d3/quantized/tensorblock/Llama-3.2-3B-Instruct-GGUF/main` | no | no |
| `tensorblock/Llama-3.3-70B-Instruct-abliterated-GGUF` | D | `/mnt/models/d5/uncensored/tensorblock/Llama-3.3-70B-Instruct-abliterated-GGUF/main` | no | no |
| `tensorblock/Mistral-Small-24B-Instruct-2501-abliterated-GGUF` | D | `/mnt/models/d3/uncensored/tensorblock/Mistral-Small-24B-Instruct-2501-abliterated-GGUF/main` | no | no |
| `tiiuae/Falcon3-10B-Instruct` | A | `/mnt/models/d1/raw/tiiuae/Falcon3-10B-Instruct/main` | no | no |
| `tiiuae/falcon-180B` | A | `/mnt/models/d1/raw/tiiuae/falcon-180B/main` | no | no |
| `tiiuae/falcon-180B-chat` | A | `/mnt/models/d1/raw/tiiuae/falcon-180B-chat/main` | no | no |
| `tiiuae/falcon-40b-instruct` | A | `/mnt/models/d2/raw/tiiuae/falcon-40b-instruct/main` | no | no |
| `unsloth/DeepSeek-R1-GGUF` | C | `/mnt/models/d5/quantized/unsloth/DeepSeek-R1-GGUF/main` | no | no |
| `unsloth/DeepSeek-V3-GGUF` | C | `/mnt/models/d5/quantized/unsloth/DeepSeek-V3-GGUF/main` | no | no |
| `unsloth/Phi-4-mini-instruct-GGUF` | C | `/mnt/models/d3/quantized/unsloth/Phi-4-mini-instruct-GGUF/main` | no | no |
| `unsloth/Qwen3-4B-Instruct-2507-GGUF` | C | `/mnt/models/d3/quantized/unsloth/Qwen3-4B-Instruct-2507-GGUF/main` | no | no |
| `unsloth/phi-4-unsloth-bnb-4bit` | C | `/mnt/models/d3/quantized/unsloth/phi-4-unsloth-bnb-4bit/main` | no | no |
| `upstage/solar-pro-preview-instruct` | A | `/mnt/models/d1/raw/upstage/solar-pro-preview-instruct/main` | no | no |
| `xai-org/grok-2` | G | `/mnt/models/d5/raw/xai-org/grok-2/main` | no | no |

**Columns:** **Path on disk** — canonical archiver destination under `models_mount`. **Dir** / **`manifest.json`** — checked on the host that ran this generator.


---

## Master registry index (`id` only)

Sorted **unique** `id` values (**170** models):

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
