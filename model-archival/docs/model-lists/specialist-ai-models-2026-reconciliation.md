# Specialist AI Models 2026 - Reconciliation

Date: 2026-03-21

Sources reviewed:
- `/home/x/Downloads/specialist_ai_models_2026.md`
- `/home/x/Downloads/specialist_ai_models_2026.txt`
- `model-archival/config/registry.yaml`
- VM run state snapshot: `/mnt/models/d5/run_state.json`

## Summary

- Source list entries found: 73
- Entries mapped to this project registry: 15 (includes duplicate naming variants)
- Entries not currently in registry: 58

Status buckets used:
- `have`: at least one mapped model is `complete`
- `planned`: mapped model(s) exist and are `pending` / `in_progress` but none complete
- `not being downloaded`: not in registry (or only absent aliases)

## Mapped Models (have/planned)

| Source Item | Project Mapping (registry IDs) | Status | Estimated Size |
|---|---|---|---|
| Llama 4 Scout | `meta-llama/Llama-4-Scout-17B-16E` (failed / purged — `failed-models-registry.yaml`), `meta-llama/Llama-4-Scout-17B-16E-Instruct` | instruct planned | ~202.4 GB each |
| Gemma 3 | `google/gemma-3-4b-it`, `google/gemma-3-12b-it`, `google/gemma-3-27b-it`, `bartowski/google_gemma-3-27b-it-GGUF` | have | 8.0 / 22.7 / 51.1 / 26.7 GB |
| Qwen3 (0.6B-8B) | `Qwen/Qwen3-8B`, `Qwen/Qwen3-4B-Instruct-2507`, `unsloth/Qwen3-4B-Instruct-2507-GGUF` | have | 15.3 / 7.5 / 4.0 GB |
| Phi-3.5 Mini | `microsoft/Phi-3-mini-128k-instruct` | planned | 7.1 GB |
| Llama 3.2 (1B-3B) | `meta-llama/Llama-3.2-1B`, `meta-llama/Llama-3.2-1B-Instruct`, `meta-llama/Llama-3.2-3B-Instruct`, `tensorblock/Llama-3.2-3B-Instruct-GGUF` | have | 4.6 / 4.6 / 12.0 / 1.6 GB |
| Mistral Small 3 (closest mapping) | `mistralai/Mistral-Small-24B-Instruct-2501`, `bartowski/Mistral-Small-24B-Instruct-2501-GGUF` | have | 87.8 / 23.3 GB |
| SmolLM3 (closest mapping) | `HuggingFaceTB/SmolLM2-1.7B-Instruct` | have | 3.2 GB |
| DeepSeek V3 / R1-Distill | `deepseek-ai/DeepSeek-V3`, `deepseek-ai/DeepSeek-V3-0324`, `deepseek-ai/DeepSeek-R1-Distill-*` | have | up to 641.3 GB (V3 family) |
| DeepSeek-R1 / R1-Distill | `deepseek-ai/DeepSeek-R1`, `deepseek-ai/DeepSeek-R1-0528`, `deepseek-ai/DeepSeek-R1-Distill-*`, `unsloth/DeepSeek-R1-GGUF` | have | 14.2 GB to 641.3 GB |
| Qwen3 (thinking mode) | `Qwen/Qwen3-8B`, `Qwen/Qwen3-14B`, `Qwen/Qwen3-32B`, `Qwen/Qwen3-235B-A22B` | have | 15.3 / 27.5 / 61.0 / 437.9 GB |
| Phi-4 Mini | `microsoft/Phi-4-mini-instruct`, `unsloth/Phi-4-mini-instruct-GGUF` | have | 7.2 / 3.8 GB |

Notes:
- "Estimated Size" uses completed `run_state` byte totals where available.
- For partial/unavailable totals, estimates come from known family sizes or registry notes.
- Some source items are conceptual families; mapped rows represent the nearest IDs in this project.

## Not Currently Being Downloaded (Not in Registry)

These items from the Claude list are not present in `model-archival/config/registry.yaml` currently:

- Closed/proprietary/API tools: `Claude (Sonnet/Opus)`, `GPT-5.2`, `Gemini 2.5 Pro`, `Cursor`, `Claude Code`, `GitHub Copilot`, `BloombergGPT (50B)`
- Legal domain: `LegalBERT`, `DISC-LawLLM`, `LawGPT / LawGPT-zh`, `Llama-LegalBar`
- Math specialists: `DeepSeekMath-V2`, `Llemma`, `InternLM-Math`, `MathCoder`, `AM-Thinking-v1`
- Chemistry/biomedical: `ChemCrow`, `ChemAgent`, `Darwin 1.5`, `MolBERT / ChemBERTa`, `BioGPT`, `BioMedLM`, `HuatuoGPT`, `ESM-2`
- Translation: `NLLB-200`, `GemmaX2-28`, `TowerInstruct`, `Aya Expanse`
- Finance/cyber/science: `FinGPT`, `FinBERT`, `SecureFalcon`, `AstroLLaMA`, `GeoGPT`
- Materials stack: `MatSciBERT`, `LLaMat`, `MaterialsBERT`, `ChemDFM`, `MatterSim`, `MACE-MP-0`, `GNoME`, `AtomGPT`, `LLaMP`, `MatterGen`, `MatterGPT`, `CrysVCD`, `CrystaLLM`, `ChatMOF`, `LLMatDesign`, `MatPilot`, `Molecular Transformer`, `ChemFormer`, `AlloyGAN`, `nach0`, `MatterChat`, `Hybrid-LLM-GNN`

## Recommendation

If you want these imported into active archival planning, next step is to create a curated `registry-specialists-2026.yaml` with:
- priority-1 smallest self-hostable open models first,
- priority-2 high-value specialist models (math/biomed/materials),
- explicit exclusions for closed/API-only entries.
