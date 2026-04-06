# final_downloads.yaml — size estimate

**Source:** `config/final_downloads.yaml` — **133** models (active final queue per `scripts/generate_final_archiver_artifacts.py`).

## Method

For each `hf_repo`, sum `size` of repo files whose names end in: `.safetensors`, `.bin`, `.gguf`, `.pt`, `.pth`, `.h5`, `.msgpack`, `.onnx`, `.npz`, `.ckpt` (Hugging Face `repo_info(..., files_metadata=True)`).

**Caveats:**

- Approximate: excludes XET-only layouts without sizes, optional LFS metadata gaps, and any files the archiver skips via its own filters.
- **GGUF** repos often ship **many** quants; this sums **all** `.gguf` in the repo (upper bound if you only pull one quant).
- **Gated** repos may return errors without `HF_TOKEN` (counted as unknown).
- Single snapshot on `main` / default revision; not per-commit pin.

## Totals

| Metric | Value |
|--------|-------|
| Models in file | 133 |
| Size resolved | 131 |
| Size unresolved (API/error) | 2 |
| **Sum (resolved only)** | **~11184.754 GiB** (12,009,537,843,015 bytes) |

| **Heuristic “one quant per tier C row”** | **~6557.28 GiB** |

The second row counts the same weight-file suffixes, but for **tier C** rows that define **`quant_levels`**, only **`.gguf`** files whose names appear to match a listed quant (e.g. `Q4_K_M`) are summed; other tiers and tier C without `quant_levels` still sum **all** matching weight files in the repo. This is closer to “what you might actually keep per registry row” but **not** identical to `resolve_model_archive_files()` in the downloader.

*Rough extrapolation* if unresolved rows matched resolved average (~85.38 GiB each): **~11355.513 GiB** (all-files method only).

**Unresolved (no size):** `Salesforce/CoDA-1.7B-Base`, `Salesforce/CoDA-1.7B-Instruct` — HF API **401** without credentials (may be gated or renamed).

## Per model

| id | drive | tier | weight files | approx GiB | note |
|----|-------|------|--------------|------------|------|
| `bartowski/google_gemma-4-31B-it-GGUF` | d1 | F | 32 | 500.133 |  |
| `bartowski/Qwen2.5-32B-Instruct-GGUF` | d3 | C | 28 | 498.8 |  |
| `bartowski/DeepSeek-R1-Distill-Qwen-32B-GGUF` | d3 | C | 27 | 483.34 |  |
| `bartowski/Qwen2.5-Coder-32B-Instruct-GGUF` | d3 | C | 28 | 467.121 |  |
| `bartowski/Mistral-Small-24B-Instruct-2501-GGUF` | d3 | C | 28 | 430.397 |  |
| `bartowski/google_gemma-4-26B-A4B-it-GGUF` | d2 | F | 31 | 414.797 |  |
| `bartowski/google_gemma-3-27b-it-GGUF` | d3 | C | 30 | 408.491 |  |
| `bartowski/DeepSeek-R1-Distill-Qwen-14B-GGUF` | d3 | C | 27 | 273.487 |  |
| `bartowski/phi-4-GGUF` | d3 | C | 27 | 269.829 |  |
| `bartowski/Codestral-22B-v0.1-GGUF` | d3 | C | 20 | 269.53 |  |
| `bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF` | d3 | C | 23 | 251.879 |  |
| `SinclairSchneider/dbrx-base-quantization-fixed` | d3 | C | 61 | 245.118 |  |
| `SinclairSchneider/dbrx-instruct-quantization-fixed` | d3 | C | 61 | 245.118 |  |
| `bartowski/Qwen2.5-Coder-14B-Instruct-GGUF` | d3 | C | 27 | 233.51 |  |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-Base-BF16` | d1 | D | 50 | 230.249 |  |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16` | d1 | D | 50 | 230.249 |  |
| `bartowski/Qwen2.5-14B-Instruct-GGUF` | d3 | C | 24 | 216.507 |  |
| `Qwen/QwQ-32B-GGUF` | d3 | C | 22 | 179.74 |  |
| `mistralai/Mixtral-8x7B-Instruct-v0.1` | d2 | A | 27 | 177.4 |  |
| `bartowski/starcoder2-15b-instruct-GGUF` | d3 | C | 13 | 143.323 |  |
| `Qwen/Qwen2.5-VL-72B-Instruct` | d5 | F | 38 | 136.738 |  |
| `rombodawg/Rombos-LLM-V2.5-Qwen-72b` | d5 | D | 31 | 135.426 |  |
| `cognitivecomputations/dolphin-2.9.2-qwen2-72b` | d5 | D | 31 | 135.426 |  |
| `huihui-ai/Qwen2.5-72B-Instruct-abliterated` | d3 | D | 31 | 135.426 |  |
| `zetasepic/Qwen2.5-72B-Instruct-abliterated` | d3 | D | 31 | 135.426 |  |
| `bartowski/Meta-Llama-3.1-8B-Instruct-GGUF` | d3 | C | 24 | 133.597 |  |
| `mlabonne/Llama-3.1-70B-Instruct-lorablated` | d2 | D | 30 | 131.417 |  |
| `nbeerbower/Llama-3.1-Nemotron-lorablated-70B` | d2 | D | 30 | 131.417 |  |
| `failspy/Meta-Llama-3-70B-Instruct-abliterated-v3.5` | d3 | D | 30 | 131.417 |  |
| `huihui-ai/DeepSeek-R1-Distill-Llama-70B-abliterated` | d2 | D | 30 | 131.417 |  |
| `huihui-ai/Llama-3.3-70B-Instruct-abliterated` | d2 | D | 30 | 131.417 |  |
| `bartowski/google_gemma-4-E4B-it-GGUF` | d3 | F | 26 | 128.816 |  |
| `deepseek-ai/deepseek-coder-33b-instruct` | d1 | B | 14 | 124.213 |  |
| `bartowski/deepseek-ai_DeepSeek-R1-0528-Qwen3-8B-GGUF` | d3 | C | 24 | 120.872 |  |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8` | d5 | D | 26 | 119.535 |  |
| `Qwen/Qwen3-32B-GGUF` | d3 | C | 5 | 118.57 |  |
| `bartowski/Qwen2.5-Coder-7B-Instruct-GGUF` | d3 | C | 24 | 112.741 |  |
| `bartowski/Qwen2.5-7B-Instruct-GGUF` | d3 | C | 24 | 112.741 |  |
| `mistralai/Devstral-Small-2507_gguf` | d3 | C | 4 | 96.211 |  |
| `mistralai/Mistral-Small-24B-Instruct-2501` | d5 | G | 11 | 87.814 |  |
| `bartowski/google_gemma-4-E2B-it-GGUF` | d3 | F | 26 | 83.865 |  |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4` | d5 | D | 17 | 74.802 |  |
| `mlx-community/dbrx-instruct-4bit` | d3 | C | 14 | 69.766 |  |
| `Qwen/Qwen3.5-35B-A3B` | d5 | G | 14 | 66.966 |  |
| `Qwen/Qwen3.5-35B-A3B-Base` | d5 | G | 14 | 66.966 |  |
| `unsloth/Qwen3-4B-Instruct-2507-GGUF` | d3 | C | 26 | 63.171 |  |
| `Qwen/QwQ-32B` | d5 | G | 14 | 61.028 |  |
| `Qwen/Qwen2.5-Coder-32B-Instruct` | d2 | B | 14 | 61.028 |  |
| `huihui-ai/DeepSeek-R1-Distill-Qwen-32B-abliterated` | d2 | D | 14 | 61.028 |  |
| `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` | d5 | G | 8 | 61.028 |  |
| `bigcode/starcoder2-15b` | d2 | B | 14 | 59.448 |  |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` | d3 | A | 13 | 58.819 |  |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-Base-BF16` | d3 | A | 13 | 58.819 |  |
| `google/gemma-4-31B` | d1 | F | 2 | 58.251 |  |
| `google/gemma-4-31B-it` | d1 | F | 2 | 58.251 |  |
| `tensorblock/Llama-3.3-70B-Instruct-abliterated-GGUF` | d5 | D | 2 | 56.478 |  |
| `tensorblock/DeepSeek-R1-Distill-Llama-70B-abliterated-GGUF` | d3 | D | 2 | 56.478 |  |
| `Qwen/Qwen3.5-27B` | d2 | G | 11 | 51.747 |  |
| `deepseek-ai/deepseek-vl2` | d3 | F | 8 | 51.187 |  |
| `google/medgemma-27b-it` | d3 | F | 12 | 51.097 |  |
| `google/medgemma-27b-text-it` | d3 | G | 11 | 50.308 |  |
| `google/gemma-4-26B-A4B` | d2 | F | 2 | 48.067 |  |
| `google/gemma-4-26B-A4B-it` | d2 | F | 2 | 48.067 |  |
| `huihui-ai/Mistral-Small-24B-Instruct-2501-abliterated` | d2 | D | 10 | 43.907 |  |
| `mistralai/Mathstral-7B-v0.1` | d3 | G | 7 | 40.502 |  |
| `meta-llama/Llama-3.2-11B-Vision-Instruct` | d3 | F | 6 | 39.673 |  |
| `tensorblock/Mixtral-8x7B-Instruct-v0.1-GGUF` | d3 | C | 2 | 37.12 |  |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8` | d3 | C | 10 | 30.438 |  |
| `meta-llama/Llama-3.1-8B-Instruct` | d2 | A | 5 | 29.915 |  |
| `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct` | d2 | B | 4 | 29.256 |  |
| `Alibaba-NLP/gte-Qwen2-7B-instruct` | d3 | B | 7 | 28.359 |  |
| `OpenDFM/ChemDFM-v2.0-14B` | d3 | G | 6 | 27.511 |  |
| `Qwen/Qwen2.5-Coder-14B-Instruct` | d2 | B | 6 | 27.511 |  |
| `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B` | d3 | G | 4 | 27.511 |  |
| `allenai/OLMo-2-1124-7B` | d3 | G | 6 | 27.19 |  |
| `Intel/neural-chat-7b-v3-1` | d3 | G | 4 | 26.978 |  |
| `HuggingFaceH4/zephyr-7b-beta` | d3 | G | 16 | 26.978 |  |
| `Equall/Saul-7B-Instruct-v1` | d3 | G | 6 | 26.978 |  |
| `intfloat/e5-mistral-7b-instruct` | d3 | B | 5 | 26.646 |  |
| `tensorblock/deepseek-coder-33b-instruct-GGUF` | d3 | C | 2 | 26.494 |  |
| `BAAI/bge-en-icl` | d3 | B | 3 | 26.489 |  |
| `tensorblock/DeepSeek-R1-Distill-Qwen-32B-abliterated-GGUF` | d3 | D | 2 | 26.308 |  |
| `deepseek-ai/deepseek-coder-6.7b-instruct` | d3 | B | 4 | 25.11 |  |
| `EleutherAI/llemma_7b` | d3 | G | 3 | 25.103 |  |
| `unsloth/Phi-4-mini-instruct-GGUF` | d3 | C | 8 | 23.976 |  |
| `meta-llama/Llama-Guard-4-12B` | d3 | E | 5 | 22.354 |  |
| `FINGU-AI/RomboUltima-32B` | d3 | D | 5 | 19.243 |  |
| `tensorblock/Mistral-Small-24B-Instruct-2501-abliterated-GGUF` | d3 | D | 2 | 18.966 |  |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4` | d3 | C | 5 | 18.014 |  |
| `Qwen/Qwen3.5-9B` | d3 | G | 4 | 17.98 |  |
| `Qwen/Qwen3.5-9B-Base` | d3 | G | 4 | 17.98 |  |
| `Qwen/Qwen2.5-VL-7B-Instruct` | d3 | F | 5 | 15.445 |  |
| `deepseek-ai/DeepSeek-R1-0528-Qwen3-8B` | d3 | G | 2 | 15.256 |  |
| `OpenDFM/ChemDFM-v1.5-8B` | d3 | G | 4 | 14.958 |  |
| `aaditya/Llama3-OpenBioLLM-8B` | d3 | G | 4 | 14.958 |  |
| `cognitivecomputations/Dolphin3.0-Llama3.1-8B` | d2 | D | 4 | 14.958 |  |
| `OpenDFM/RetroDFM-R-v0-8B` | d3 | G | 4 | 14.958 |  |
| `deepseek-ai/DeepSeek-R1-Distill-Llama-8B` | d3 | G | 2 | 14.958 |  |
| `mlabonne/NeuralDaredevil-8B-abliterated` | d2 | D | 4 | 14.958 |  |
| `google/gemma-4-E4B` | d3 | F | 1 | 14.894 |  |
| `google/gemma-4-E4B-it` | d3 | F | 1 | 14.894 |  |
| `AI4Chem/ChemLLM-7B-Chat` | d3 | G | 2 | 14.413 |  |
| `apple/DiffuCoder-7B-cpGRPO` | d3 | G | 5 | 14.185 |  |
| `Qwen/Qwen2.5-Math-7B-Instruct` | d3 | G | 4 | 14.185 |  |
| `Qwen/Qwen2.5-Coder-7B-Instruct` | d3 | B | 4 | 14.185 |  |
| `apple/DiffuCoder-7B-Instruct` | d3 | G | 4 | 14.185 |  |
| `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` | d3 | G | 2 | 14.185 |  |
| `apple/DiffuCoder-7B-Base` | d3 | G | 4 | 14.185 |  |
| `FreedomIntelligence/HuatuoGPT2-7B` | d3 | G | 2 | 13.981 |  |
| `deepseek-ai/deepseek-math-7b-instruct` | d3 | G | 2 | 12.872 |  |
| `stanford-crfm/BioMedLM` | d3 | G | 1 | 9.971 |  |
| `unsloth/phi-4-unsloth-bnb-4bit` | d3 | C | 3 | 9.678 |  |
| `google/gemma-4-E2B` | d3 | F | 1 | 9.543 |  |
| `google/gemma-4-E2B-it` | d3 | F | 1 | 9.543 |  |
| `Qwen/Qwen3.5-4B` | d3 | G | 2 | 8.68 |  |
| `Qwen/Qwen3.5-4B-Base` | d3 | G | 2 | 8.68 |  |
| `mlabonne/NeuralDaredevil-8B-abliterated-GGUF` | d3 | D | 2 | 8.195 |  |
| `google/gemma-3-4b-it` | d3 | F | 2 | 8.01 |  |
| `google/medgemma-4b-it` | d3 | F | 2 | 8.01 |  |
| `Qwen/Qwen3-4B-Instruct-2507` | d5 | A | 3 | 7.492 |  |
| `BAAI/bge-large-en-v1.5` | d3 | B | 3 | 3.742 |  |
| `jinaai/jina-embeddings-v3` | d3 | B | 4 | 3.202 |  |
| `Qwen/Qwen2.5-Math-1.5B` | d3 | G | 1 | 2.875 |  |
| `tensorblock/Llama-3.2-3B-Instruct-GGUF` | d3 | C | 2 | 2.842 |  |
| `BAAI/bge-m3` | d3 | B | 4 | 2.118 |  |
| `cambridgeltl/SapBERT-from-PubMedBERT-fulltext` | d3 | G | 4 | 1.632 |  |
| `emilyalsentzer/Bio_ClinicalBERT` | d3 | B | 3 | 1.3 |  |
| `microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext` | d3 | G | 2 | 0.818 |  |
| `dmis-lab/biobert-base-cased-v1.2` | d3 | G | 1 | 0.406 |  |
| `seyonec/ChemBERTa-zinc-base-v1` | d3 | B | 2 | 0.331 |  |
| `meta-llama/Llama-Prompt-Guard-2-22M` | d3 | E | 1 | 0.264 |  |
| `Salesforce/CoDA-1.7B-Base` | d3 | G | 0 | — | RepositoryNotFoundError: 401 Client Error. (Request ID: Root=1-69d3135a-56184101 |
| `Salesforce/CoDA-1.7B-Instruct` | d3 | G | 0 | — | RepositoryNotFoundError: 401 Client Error. (Request ID: Root=1-69d3135a-090155e7 |
