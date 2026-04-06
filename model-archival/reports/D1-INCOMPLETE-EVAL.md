# D1 evaluation — registry `drive: d1` models

- Main registry: `/home/x/dev/model-archival/model-archiver/config/registry.yaml`
- D1 mount: `/mnt/models/d1`
- Narrow list: `/home/x/dev/model-archival/model-archiver/config/registry-d1-manifest-incomplete.yaml` (18 ids)
- HF_TOKEN: set

## Summary

| Metric | Value |
|--------|------:|
| D1 models in main registry | 29 |
| Manifest-complete on D1 (any revision dir) | 11 |
| Incomplete (no complete manifest) | 18 |
| Incomplete + in narrow + **HF estimate OK** | 17 |
| Incomplete + in narrow + **HF resolve error** | 1 |
| Incomplete + **not** in narrow + estimate OK | 0 |
| Approx. remaining download (narrow ∩ incomplete, estimated rows) | 7349.34 GiB |
| Approx. remaining download (incomplete **not** in narrow) | 0.00 GiB |
| Rows with HF resolve errors (any) | 1 |

**Narrow run coverage:** Models in the narrow file that are already manifest-complete are not listed below; the archiver will skip them quickly. Rows with **HF resolve error** are still incomplete on disk but need token/access or repo fix before any bytes move.

**Interpretation:** The narrow archiver run (`-r registry-d1-manifest-incomplete.yaml`) will only process models **listed in that file**. Incomplete D1 models **not** in the narrow list stay unfinished until you add them or run the full registry.

Estimates use HF file sizes minus bytes found under the revision dir, any sibling revision, and `d1/.tmp/<slug>/`. XET partials in the HF hub cache are not counted — a few repos may download less than shown.

## Incomplete models (detail)

| Model | Tier | Narrow? | Remaining (GiB) | HF total (GiB) | Sidecar-done files | Commit | Error |
|-------|------|---------|-----------------:|---------------:|-------------------:|--------|-------|
| `meta-llama/Llama-3.1-405B-Instruct` | A | yes | 2275.95 | 2275.95 | 0 | `be673f326cab` | — |
| `deepseek-ai/DeepSeek-V3-Base` | A | yes | 641.31 | 641.31 | 0 | `afb92e1fa402` | — |
| `nvidia/Llama-3_1-Nemotron-Ultra-253B-v1` | D | yes | 472.01 | 472.01 | 0 | `5b47def5b895` | — |
| `Qwen/Qwen3-235B-A22B` | A | yes | 437.92 | 437.92 | 0 | `8efa61729e24` | — |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-Base-BF16` | D | yes | 197.72 | 230.27 | 14 | `46cc6113d364` | — |
| `unsloth/DeepSeek-V3-GGUF` | C | yes | 166.32 | 376.65 | 5 | `6b9a45d8a30b` | — |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16` | D | yes | 141.90 | 230.27 | 28 | `7e74fe9a5a62` | — |
| `deepseek-ai/DeepSeek-V3-0324` | A | yes | 106.10 | 641.31 | 139 | `e9b33add7688` | — |
| `CombinHorizon/zetasepic-abliteratedV2-Qwen2.5-32B-Inst-BaseMerge-TIES` | D | yes | 61.04 | 61.04 | 0 | `d976a5d6768d` | — |
| `Qwen/Qwen2.5-32B` | A | yes | 61.04 | 61.04 | 0 | `1818d35814b8` | — |
| `upstage/solar-pro-preview-instruct` | A | yes | 41.24 | 41.24 | 0 | `dd4bcf7006df` | — |
| `tiiuae/Falcon3-10B-Instruct` | A | yes | 19.21 | 19.21 | 0 | `8799bc6aec01` | — |
| `meta-llama/Llama-3.3-70B-Instruct` | A | yes | 16.43 | 262.87 | 45 | `6f6073b42301` | — |
| `FINGU-AI/Chocolatine-Fusion-14B` | D | yes | 9.26 | 9.26 | 0 | `49b7b720ddd4` | — |
| `IntervitensInc/internlm2_5-20b-llamafied` | A | yes | 0.00 | 37.00 | 6 | `0b6fc3cc0b9b` | — |
| `MiniMaxAI/MiniMax-M2.7` | G | yes | — | — | — | `—` | 404 Client Error. (Request ID: Root=1-69d2d396-1747cba65dd852842096c0e9;2160d... |

## Complete on D1 (skipped above)

Count: **11** (at least one revision passes manifest + sidecar check).

