# D1 prune candidates — below progress threshold

- Threshold: **<60.0%** downloaded (HF file set, sidecar-complete = done)
- HF resolve errors treated as prune: **True**
- D1 models manifest-complete (skipped): **11**
- Incomplete rows: **18**
- **Prune candidates: 12**
- Mode: **dry-run**

## Candidates

| Model | Progress % | Remaining GiB | HF total GiB | HF error (truncated) |
|-------|-----------:|---------------:|-------------:|----------------------|
| `MiniMaxAI/MiniMax-M2.7` | — | — | — | 404 Client Error. (Request ID: Root=1-69d2d5bd-2523fe3369d30 |
| `CombinHorizon/zetasepic-abliteratedV2-Qwen2.5-32B-Inst-BaseMerge-TIES` | 0.0 | 61.04 | 61.04 | — |
| `FINGU-AI/Chocolatine-Fusion-14B` | 0.0 | 9.26 | 9.26 | — |
| `Qwen/Qwen2.5-32B` | 0.0 | 61.04 | 61.04 | — |
| `Qwen/Qwen3-235B-A22B` | 0.0 | 437.92 | 437.92 | — |
| `deepseek-ai/DeepSeek-V3-Base` | 0.0 | 641.31 | 641.31 | — |
| `meta-llama/Llama-3.1-405B-Instruct` | 0.0 | 2275.95 | 2275.95 | — |
| `nvidia/Llama-3_1-Nemotron-Ultra-253B-v1` | 0.0 | 472.01 | 472.01 | — |
| `tiiuae/Falcon3-10B-Instruct` | 0.0 | 19.21 | 19.21 | — |
| `upstage/solar-pro-preview-instruct` | 0.0 | 41.24 | 41.24 | — |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-Base-BF16` | 14.1 | 197.72 | 230.27 | — |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16` | 38.4 | 141.90 | 230.27 | — |

## Disk paths (``rm -rf`` targets)

- `/mnt/models/d1/uncensored/CombinHorizon/zetasepic-abliteratedV2-Qwen2.5-32B-Inst-BaseMerge-TIES`
- `/mnt/models/d1/.tmp/CombinHorizon_zetasepic-abliteratedV2-Qwen2.5-32B-Inst-BaseMerge-TIES` (if present)
- `/mnt/models/d1/uncensored/FINGU-AI/Chocolatine-Fusion-14B`
- `/mnt/models/d1/.tmp/FINGU-AI_Chocolatine-Fusion-14B` (if present)
- `/mnt/models/d1/raw/MiniMaxAI/MiniMax-M2.7`
- `/mnt/models/d1/.tmp/MiniMaxAI_MiniMax-M2.7` (if present)
- `/mnt/models/d1/raw/Qwen/Qwen2.5-32B`
- `/mnt/models/d1/.tmp/Qwen_Qwen2.5-32B` (if present)
- `/mnt/models/d1/raw/Qwen/Qwen3-235B-A22B`
- `/mnt/models/d1/.tmp/Qwen_Qwen3-235B-A22B` (if present)
- `/mnt/models/d1/raw/deepseek-ai/DeepSeek-V3-Base`
- `/mnt/models/d1/.tmp/deepseek-ai_DeepSeek-V3-Base` (if present)
- `/mnt/models/d1/raw/meta-llama/Llama-3.1-405B-Instruct`
- `/mnt/models/d1/.tmp/meta-llama_Llama-3.1-405B-Instruct` (if present)
- `/mnt/models/d1/uncensored/nvidia/Llama-3_1-Nemotron-Ultra-253B-v1`
- `/mnt/models/d1/.tmp/nvidia_Llama-3_1-Nemotron-Ultra-253B-v1` (if present)
- `/mnt/models/d1/uncensored/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16`
- `/mnt/models/d1/.tmp/nvidia_NVIDIA-Nemotron-3-Super-120B-A12B-BF16` (if present)
- `/mnt/models/d1/uncensored/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-Base-BF16`
- `/mnt/models/d1/.tmp/nvidia_NVIDIA-Nemotron-3-Super-120B-A12B-Base-BF16` (if present)
- `/mnt/models/d1/raw/tiiuae/Falcon3-10B-Instruct`
- `/mnt/models/d1/.tmp/tiiuae_Falcon3-10B-Instruct` (if present)
- `/mnt/models/d1/raw/upstage/solar-pro-preview-instruct`
- `/mnt/models/d1/.tmp/upstage_solar-pro-preview-instruct` (if present)

