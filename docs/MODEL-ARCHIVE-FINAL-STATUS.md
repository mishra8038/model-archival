# MODEL-ARCHIVE-FINAL-STATUS

_Generated: 2026-04-04 01:03 UTC_

## Scope

Merged registry IDs from `model-archival/config/registry.yaml`, 
`registry-specialists.yaml`, `registry-legacy.yaml`, `registry_high_risk.yaml`, 
and `final_downloads.yaml` (active queue). 
Download **status** and **bytes** come from `run_state.json` when provided.

### D3 scratch reclaim

`uv run archiver audit-tmp --delete-reclaimable --apply` only removes 
`reclaimable_tmp` (verified complete elsewhere + large leftover scratch). 
If the audit reports **zero** such paths, D3 `.tmp` is mostly `active_partial`, 
`wrong_drive_tmp`, or `metadata_only` — reclaim those only after manual review.

### Falcon-180B partial

Partial `tiiuae/falcon-180B` scratch should live under **`d1/.tmp`** (registry drive d1). 
If still on D5, move: `mv /mnt/models/d5/.tmp/tiiuae_falcon-180B /mnt/models/d1/.tmp/` 
(cross-device move can take many minutes).

**run_state source:** `stdin`

## Summary

- **Distinct model IDs (union):** 257
- **final_downloads.yaml rows:** 137

**run_state status counts:** complete=156, failed=29, in_progress=1, pending=40, skipped=5

## Model table

| id | tier | drive | pri | run_state | total_GiB | on_disk | expected_path | registries |
|---|:-:|:-:|:-:|---|---:|:---:|---|---|
| `01-ai/Yi-34B-Chat` | A | d2 | 2 | pending | 64.1 | n/a | `d2/raw/01-ai/Yi-34B-Chat/main` | `registry.yaml`, `registry-legacy.yaml` |
| `AI4Chem/ChemLLM-7B-Chat` | G | d3 | 1 | complete | 14.4 | n/a | `d3/raw/AI4Chem/ChemLLM-7B-Chat/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `Alibaba-NLP/gte-Qwen2-7B-instruct` | B | d3 | 2 | complete | 28.4 | n/a | `d3/raw/Alibaba-NLP/gte-Qwen2-7B-instruct/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `BAAI/bge-en-icl` | B | d3 | 2 | complete | 26.5 | n/a | `d3/raw/BAAI/bge-en-icl/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `BAAI/bge-large-en-v1.5` | B | d3 | 2 | complete | 2.5 | n/a | `d3/raw/BAAI/bge-large-en-v1.5/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `BAAI/bge-m3` | B | d3 | 1 | complete | 2.2 | n/a | `d3/raw/BAAI/bge-m3/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `CohereForAI/c4ai-command-r-plus` | A | d1 | 2 | — | — | n/a | `d1/raw/CohereForAI/c4ai-command-r-plus/main` | `registry-legacy.yaml` |
| `CohereLabs/c4ai-command-r-plus-08-2024` | A | d2 | 2 | complete | 193.4 | n/a | `d2/raw/CohereLabs/c4ai-command-r-plus-08-2024/e808c1a2249354ca211c9f08d1338e5039f633f8` | `registry.yaml` |
| `CombinHorizon/Josiefied-abliteratedV4-Qwen2.5-14B-Inst-BaseMerge-TIES` | D | d3 | 2 | — | — | n/a | `d3/uncensored/CombinHorizon/Josiefied-abliteratedV4-Qwen2.5-14B-Inst-BaseMerge-TIES/main` | `registry_high_risk.yaml` |
| `CombinHorizon/huihui-ai-abliterated-Qwen2.5-32B-Inst-BaseMerge-TIES` | D | d3 | 2 | — | — | n/a | `d3/uncensored/CombinHorizon/huihui-ai-abliterated-Qwen2.5-32B-Inst-BaseMerge-TIES/main` | `registry_high_risk.yaml` |
| `CombinHorizon/huihui-ai-abliteratedV2-Qwen2.5-14B-Inst-BaseMerge-TIES` | D | d3 | 2 | — | — | n/a | `d3/uncensored/CombinHorizon/huihui-ai-abliteratedV2-Qwen2.5-14B-Inst-BaseMerge-TIES/main` | `registry_high_risk.yaml` |
| `CombinHorizon/zetasepic-abliteratedV2-Qwen2.5-32B-Inst-BaseMerge-TIES` | D | d1 | 2 | complete | 61.0 | n/a | `d1/uncensored/CombinHorizon/zetasepic-abliteratedV2-Qwen2.5-32B-Inst-BaseMerge-TIES/d976a5d6768d54c5e59a88fe63238a055c30c06a` | `registry.yaml`, `registry_high_risk.yaml`, `final_downloads.yaml` |
| `EleutherAI/llemma_7b` | G | d3 | 1 | complete | 25.1 | n/a | `d3/raw/EleutherAI/llemma_7b/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `Equall/Saul-7B-Instruct-v1` | G | d3 | 1 | complete | 27.0 | n/a | `d3/raw/Equall/Saul-7B-Instruct-v1/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `FINGU-AI/Chocolatine-Fusion-14B` | D | d1 | 2 | complete | 9.3 | n/a | `d1/uncensored/FINGU-AI/Chocolatine-Fusion-14B/49b7b720ddd40ccdca303922037a4bb34b1ca33b` | `registry.yaml`, `final_downloads.yaml` |
| `FINGU-AI/RomboUltima-32B` | D | d3 | 2 | complete | 19.3 | n/a | `d3/uncensored/FINGU-AI/RomboUltima-32B/98a732a32e2366a2ab8f08fdc3d668892e7c1f7f` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `FreedomIntelligence/HuatuoGPT2-7B` | G | d3 | 1 | complete | 14.0 | n/a | `d3/raw/FreedomIntelligence/HuatuoGPT2-7B/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `Goekdeniz-Guelmez/Josiefied-Qwen2.5-14B-Instruct-abliterated-v4` | D | d3 | 2 | — | — | n/a | `d3/uncensored/Goekdeniz-Guelmez/Josiefied-Qwen2.5-14B-Instruct-abliterated-v4/main` | `registry_high_risk.yaml` |
| `Goekdeniz-Guelmez/Josiefied-Qwen2.5-7B-Instruct-abliterated-v2` | D | d3 | 2 | — | — | n/a | `d3/uncensored/Goekdeniz-Guelmez/Josiefied-Qwen2.5-7B-Instruct-abliterated-v2/main` | `registry_high_risk.yaml` |
| `HuggingFaceH4/zephyr-7b-beta` | G | d3 | 1 | complete | 27.0 | n/a | `d3/raw/HuggingFaceH4/zephyr-7b-beta/main` | `registry.yaml`, `registry-specialists.yaml`, `registry-legacy.yaml`, `final_downloads.yaml` |
| `HuggingFaceTB/SmolLM2-1.7B-Instruct` | A | d3 | 2 | complete | 3.2 | n/a | `d3/raw/HuggingFaceTB/SmolLM2-1.7B-Instruct/main` | `registry.yaml` |
| `HuggingFaceTB/SmolLM2-360M` | A | d3 | 1 | — | — | n/a | `d3/raw/HuggingFaceTB/SmolLM2-360M/main` | `registry.yaml` |
| `HuggingFaceTB/SmolLM2-360M-Instruct` | A | d3 | 3 | — | — | n/a | `d3/raw/HuggingFaceTB/SmolLM2-360M-Instruct/main` | `registry.yaml` |
| `Intel/neural-chat-7b-v3-1` | G | d3 | 1 | complete | 27.0 | n/a | `d3/raw/Intel/neural-chat-7b-v3-1/main` | `registry.yaml`, `registry-specialists.yaml`, `registry-legacy.yaml`, `final_downloads.yaml` |
| `IntervitensInc/internlm2_5-20b-llamafied` | A | d1 | 2 | pending | 37.0 | n/a | `d1/raw/IntervitensInc/internlm2_5-20b-llamafied/main` | `registry.yaml` |
| `Isaak-Carter/Josiefied-Qwen2.5-7B-Instruct-abliterated-v2` | D | d3 | 2 | — | — | n/a | `d3/uncensored/Isaak-Carter/Josiefied-Qwen2.5-7B-Instruct-abliterated-v2/main` | `registry_high_risk.yaml` |
| `MiniMaxAI/MiniMax-M2.5` | G | d1 | 4 | failed | — | n/a | `d1/raw/MiniMaxAI/MiniMax-M2.5/main` | `registry.yaml` |
| `MiniMaxAI/MiniMax-M2.7` | G | d1 | 2 | skipped | — | n/a | `d1/raw/MiniMaxAI/MiniMax-M2.7/main` | `registry.yaml` |
| `NousResearch/DeepHermes-3-Mistral-24B-Preview` | D | d3 | 2 | — | — | n/a | `d3/uncensored/NousResearch/DeepHermes-3-Mistral-24B-Preview/main` | `registry_high_risk.yaml` |
| `NousResearch/Hermes-3-Llama-3.1-70B` | D | d3 | 1 | — | — | n/a | `d3/uncensored/NousResearch/Hermes-3-Llama-3.1-70B/main` | `registry_high_risk.yaml` |
| `NovaSky-Berkeley/Sky-T1-32B-Preview` | E | d3 | 2 | pending | — | n/a | `d3/raw/NovaSky-Berkeley/Sky-T1-32B-Preview/main` | `registry-legacy.yaml` |
| `OpenDFM/ChemDFM-v1.5-8B` | G | d3 | 0 | complete | 15.0 | n/a | `d3/raw/OpenDFM/ChemDFM-v1.5-8B/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `OpenDFM/ChemDFM-v2.0-14B` | G | d3 | 0 | complete | 27.5 | n/a | `d3/raw/OpenDFM/ChemDFM-v2.0-14B/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `OpenDFM/RetroDFM-R-v0-8B` | G | d3 | 0 | complete | 15.0 | n/a | `d3/raw/OpenDFM/RetroDFM-R-v0-8B/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `Orion-zhen/Qwen2.5-7B-Instruct-Uncensored` | D | d3 | 2 | — | — | n/a | `d3/uncensored/Orion-zhen/Qwen2.5-7B-Instruct-Uncensored/main` | `registry_high_risk.yaml` |
| `Prior-Labs/TabPFN-v2-clf` | G | d3 | 2 | — | — | n/a | `d3/raw/Prior-Labs/TabPFN-v2-clf/main` | `registry.yaml` |
| `Qwen/QwQ-32B` | E | d3 | 1 | complete | 61.0 | n/a | `d3/raw/Qwen/QwQ-32B/976055f8c83f394f35dbd3ab09a285a984907bd0` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `Qwen/QwQ-32B-GGUF` | C | d3 | 1 | complete | 32.4 | n/a | `d3/quantized/Qwen/QwQ-32B-GGUF/8728e66249190b78dee8404869827328527f6b3b` | `registry.yaml`, `final_downloads.yaml` |
| `Qwen/Qwen1.5-110B` | A | d1 | 2 | — | — | n/a | `d1/raw/Qwen/Qwen1.5-110B/main` | `registry-legacy.yaml` |
| `Qwen/Qwen2.5-0.5B` | A | d1 | 1 | — | — | n/a | `d1/raw/Qwen/Qwen2.5-0.5B/main` | `registry.yaml` |
| `Qwen/Qwen2.5-0.5B-Instruct` | A | d2 | 3 | — | — | n/a | `d2/raw/Qwen/Qwen2.5-0.5B-Instruct/main` | `registry.yaml` |
| `Qwen/Qwen2.5-1.5B` | A | d1 | 1 | — | — | n/a | `d1/raw/Qwen/Qwen2.5-1.5B/main` | `registry.yaml` |
| `Qwen/Qwen2.5-1.5B-Instruct` | A | d2 | 3 | — | — | n/a | `d2/raw/Qwen/Qwen2.5-1.5B-Instruct/main` | `registry.yaml` |
| `Qwen/Qwen2.5-14B` | A | d1 | 1 | complete | 27.5 | n/a | `d1/raw/Qwen/Qwen2.5-14B/97e1e76335b7017d8f67c08a19d103c0504298c9` | `registry.yaml` |
| `Qwen/Qwen2.5-14B-Instruct` | A | d2 | 1 | complete | 27.5 | n/a | `d2/raw/Qwen/Qwen2.5-14B-Instruct/cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8` | `registry.yaml` |
| `Qwen/Qwen2.5-14B-Instruct-1M` | A | d2 | 2 | complete | 27.5 | n/a | `d2/raw/Qwen/Qwen2.5-14B-Instruct-1M/620fad32de7bdd2293b3d99b39eba2fe63e97438` | `registry.yaml` |
| `Qwen/Qwen2.5-32B` | A | d1 | 1 | complete | 61.0 | n/a | `d1/raw/Qwen/Qwen2.5-32B/1818d35814b8319459f4bd55ed1ac8709630f003` | `registry.yaml` |
| `Qwen/Qwen2.5-32B-Instruct` | A | d2 | 1 | complete | 61.0 | n/a | `d2/raw/Qwen/Qwen2.5-32B-Instruct/5ede1c97bbab6ce5cda5812749b4c0bdf79b18dd` | `registry.yaml` |
| `Qwen/Qwen2.5-3B` | A | d1 | 1 | complete | 5.8 | n/a | `d1/raw/Qwen/Qwen2.5-3B/main` | `registry.yaml` |
| `Qwen/Qwen2.5-3B-Instruct` | A | d2 | 3 | — | — | n/a | `d2/raw/Qwen/Qwen2.5-3B-Instruct/main` | `registry.yaml` |
| `Qwen/Qwen2.5-72B` | A | d2 | 4 | pending | 135.4 | n/a | `d2/raw/Qwen/Qwen2.5-72B/main` | `registry.yaml` |
| `Qwen/Qwen2.5-72B-Instruct` | A | d2 | 4 | complete | 135.4 | n/a | `d2/raw/Qwen/Qwen2.5-72B-Instruct/495f39366efef23836d0cfae4fbe635880d2be31` | `registry.yaml` |
| `Qwen/Qwen2.5-7B` | A | d1 | 1 | complete | 14.2 | n/a | `d1/raw/Qwen/Qwen2.5-7B/main` | `registry.yaml` |
| `Qwen/Qwen2.5-7B-Instruct` | A | d2 | 2 | complete | 14.2 | n/a | `d2/raw/Qwen/Qwen2.5-7B-Instruct/a09a35458c702b33eeacc393d103063234e8bc28` | `registry.yaml` |
| `Qwen/Qwen2.5-Coder-14B-Instruct` | B | d2 | 3 | — | — | n/a | `d2/raw/Qwen/Qwen2.5-Coder-14B-Instruct/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `Qwen/Qwen2.5-Coder-32B-Instruct` | B | d2 | 1 | complete | 61.0 | n/a | `d2/raw/Qwen/Qwen2.5-Coder-32B-Instruct/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `Qwen/Qwen2.5-Coder-7B-Instruct` | B | d3 | 3 | — | — | n/a | `d3/raw/Qwen/Qwen2.5-Coder-7B-Instruct/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `Qwen/Qwen2.5-Math-1.5B` | G | d3 | 1 | complete | 2.9 | n/a | `d3/raw/Qwen/Qwen2.5-Math-1.5B/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `Qwen/Qwen2.5-Math-72B-Instruct` | G | d5 | 4 | complete | 135.4 | n/a | `d5/raw/Qwen/Qwen2.5-Math-72B-Instruct/main` | `registry.yaml` |
| `Qwen/Qwen2.5-Math-7B-Instruct` | G | d3 | 2 | complete | 14.2 | n/a | `d3/raw/Qwen/Qwen2.5-Math-7B-Instruct/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `Qwen/Qwen2.5-VL-72B-Instruct` | F | d5 | 4 | in_progress | 136.7 | n/a | `d5/raw/Qwen/Qwen2.5-VL-72B-Instruct/main` | `registry.yaml`, `final_downloads.yaml` |
| `Qwen/Qwen2.5-VL-7B-Instruct` | F | d3 | 2 | complete | 15.5 | n/a | `d3/raw/Qwen/Qwen2.5-VL-7B-Instruct/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `Qwen/Qwen3-0.6B` | A | d2 | 3 | — | — | n/a | `d2/raw/Qwen/Qwen3-0.6B/main` | `registry.yaml` |
| `Qwen/Qwen3-0.6B-Base` | A | d2 | 1 | — | — | n/a | `d2/raw/Qwen/Qwen3-0.6B-Base/main` | `registry.yaml` |
| `Qwen/Qwen3-1.7B` | A | d2 | 3 | — | — | n/a | `d2/raw/Qwen/Qwen3-1.7B/main` | `registry.yaml` |
| `Qwen/Qwen3-1.7B-Base` | A | d2 | 1 | — | — | n/a | `d2/raw/Qwen/Qwen3-1.7B-Base/main` | `registry.yaml` |
| `Qwen/Qwen3-14B` | A | d2 | 1 | complete | 27.5 | n/a | `d2/raw/Qwen/Qwen3-14B/40c069824f4251a91eefaf281ebe4c544efd3e18` | `registry.yaml` |
| `Qwen/Qwen3-235B-A22B` | A | d1 | 4 | pending | 437.9 | n/a | `d1/raw/Qwen/Qwen3-235B-A22B/main` | `registry.yaml` |
| `Qwen/Qwen3-30B-A3B` | A | d2 | 2 | complete | 56.9 | n/a | `d2/raw/Qwen/Qwen3-30B-A3B/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39` | `registry.yaml` |
| `Qwen/Qwen3-32B` | A | d1 | 1 | complete | 61.0 | n/a | `d1/raw/Qwen/Qwen3-32B/9216db5781bf21249d130ec9da846c4624c16137` | `registry.yaml` |
| `Qwen/Qwen3-32B-GGUF` | C | d3 | 1 | complete | 32.4 | n/a | `d3/quantized/Qwen/Qwen3-32B-GGUF/938a7432affaec9157f883a87164e2646ae17555` | `registry.yaml`, `final_downloads.yaml` |
| `Qwen/Qwen3-4B-Instruct-2507` | A | d5 | 1 | pending | 7.5 | n/a | `d5/raw/Qwen/Qwen3-4B-Instruct-2507/main` | `registry.yaml`, `final_downloads.yaml` |
| `Qwen/Qwen3-8B` | A | d2 | 1 | complete | 15.3 | n/a | `d2/raw/Qwen/Qwen3-8B/b968826d9c46dd6066d109eabc6255188de91218` | `registry.yaml` |
| `Qwen/Qwen3-Coder-30B-A3B-Instruct` | B | d2 | 1 | complete | 56.9 | n/a | `d2/raw/Qwen/Qwen3-Coder-30B-A3B-Instruct/b2cff646eb4bb1d68355c01b18ae02e7cf42d120` | `registry.yaml` |
| `Qwen/Qwen3.5-122B-A10B` | A | d1 | 4 | pending | — | n/a | `d1/raw/Qwen/Qwen3.5-122B-A10B/main` | `registry.yaml` |
| `Qwen/Qwen3.5-27B` | G | d2 | 2 | complete | 51.8 | n/a | `d2/raw/Qwen/Qwen3.5-27B/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `Qwen/Qwen3.5-35B-A3B` | G | d5 | 2 | pending | — | n/a | `d5/raw/Qwen/Qwen3.5-35B-A3B/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `Qwen/Qwen3.5-35B-A3B-Base` | G | d5 | 2 | pending | — | n/a | `d5/raw/Qwen/Qwen3.5-35B-A3B-Base/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `Qwen/Qwen3.5-397B-A17B` | A | d1 | 4 | pending | — | n/a | `d1/raw/Qwen/Qwen3.5-397B-A17B/main` | `registry.yaml` |
| `Qwen/Qwen3.5-4B` | G | d3 | 1 | complete | 8.7 | n/a | `d3/raw/Qwen/Qwen3.5-4B/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `Qwen/Qwen3.5-4B-Base` | G | d3 | 1 | complete | 8.7 | n/a | `d3/raw/Qwen/Qwen3.5-4B-Base/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `Qwen/Qwen3.5-9B` | G | d3 | 1 | complete | 18.0 | n/a | `d3/raw/Qwen/Qwen3.5-9B/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `Qwen/Qwen3.5-9B-Base` | G | d3 | 1 | complete | 18.0 | n/a | `d3/raw/Qwen/Qwen3.5-9B-Base/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `Salesforce/CoDA-1.7B-Base` | G | d3 | 1 | failed | — | n/a | `d3/raw/Salesforce/CoDA-1.7B-Base/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `Salesforce/CoDA-1.7B-Instruct` | G | d3 | 1 | failed | — | n/a | `d3/raw/Salesforce/CoDA-1.7B-Instruct/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `SinclairSchneider/dbrx-base-quantization-fixed` | C | d3 | 4 | failed | 245.1 | n/a | `d3/quantized/SinclairSchneider/dbrx-base-quantization-fixed/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `SinclairSchneider/dbrx-instruct-quantization-fixed` | C | d3 | 4 | failed | 245.1 | n/a | `d3/quantized/SinclairSchneider/dbrx-instruct-quantization-fixed/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `Skywork/Skywork-Reward-Llama-3.1-70B` | B | d5 | 4 | pending | — | n/a | `d5/raw/Skywork/Skywork-Reward-Llama-3.1-70B/main` | `registry.yaml` |
| `THUDM/glm-4-9b-chat` | A | d2 | 2 | pending | 17.5 | n/a | `d2/raw/THUDM/glm-4-9b-chat/main` | `registry.yaml`, `registry-legacy.yaml` |
| `TinyLlama/TinyLlama-1.1B-Chat-v1.0` | A | d3 | 2 | complete | 2.1 | n/a | `d3/raw/TinyLlama/TinyLlama-1.1B-Chat-v1.0/main` | `registry.yaml`, `registry-legacy.yaml` |
| `Triangle104/Phi-4-AbliteratedRP` | D | d3 | 2 | — | — | n/a | `d3/uncensored/Triangle104/Phi-4-AbliteratedRP/main` | `registry_high_risk.yaml` |
| `Undi95/Phi4-abliterated` | D | d3 | 2 | — | — | n/a | `d3/uncensored/Undi95/Phi4-abliterated/main` | `registry_high_risk.yaml` |
| `Undi95/dbrx-base` | A | d2 | 4 | failed | 245.1 | n/a | `d2/raw/Undi95/dbrx-base/main` | `registry.yaml` |
| `aaditya/Llama3-OpenBioLLM-8B` | G | d3 | 1 | complete | 15.0 | n/a | `d3/raw/aaditya/Llama3-OpenBioLLM-8B/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `allenai/Llama-3.1-Tulu-3-70B` | A | d2 | 4 | complete | 131.4 | n/a | `d2/raw/allenai/Llama-3.1-Tulu-3-70B/cfc1d855e534a0b9b82a9cea6bf9e8dda30b10d7` | `registry.yaml` |
| `allenai/OLMo-2-1124-7B` | G | d3 | 1 | complete | 27.2 | n/a | `d3/raw/allenai/OLMo-2-1124-7B/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `alpindale/WizardLM-2-8x22B` | D | d3 | 1 | — | — | n/a | `d3/uncensored/alpindale/WizardLM-2-8x22B/main` | `registry_high_risk.yaml` |
| `alpindale/dbrx-instruct` | A | d5 | 4 | failed | 245.1 | n/a | `d5/raw/alpindale/dbrx-instruct/main` | `registry.yaml` |
| `apple/DiffuCoder-7B-Base` | G | d3 | 2 | complete | 14.2 | n/a | `d3/raw/apple/DiffuCoder-7B-Base/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `apple/DiffuCoder-7B-Instruct` | G | d3 | 2 | complete | 14.2 | n/a | `d3/raw/apple/DiffuCoder-7B-Instruct/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `apple/DiffuCoder-7B-cpGRPO` | G | d3 | 2 | complete | 14.2 | n/a | `d3/raw/apple/DiffuCoder-7B-cpGRPO/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `bartowski/Codestral-22B-v0.1-GGUF` | C | d3 | 1 | complete | 22.0 | n/a | `d3/quantized/bartowski/Codestral-22B-v0.1-GGUF/0e6abe14d6aeaf2c99d5dc9973205e8e38692d90` | `registry.yaml`, `final_downloads.yaml` |
| `bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF` | C | d3 | 1 | complete | 31.5 | n/a | `d3/quantized/bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF/8f248fa2072348f77a8bc37754e470de1f61866e` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `bartowski/DeepSeek-R1-Distill-Llama-70B-GGUF` | C | d3 | 4 | complete | 69.8 | n/a | `d3/quantized/bartowski/DeepSeek-R1-Distill-Llama-70B-GGUF/1842c5f7280f933ead58adf8afd078672c9f6cd0` | `registry.yaml` |
| `bartowski/DeepSeek-R1-Distill-Qwen-14B-GGUF` | C | d3 | 3 | — | — | n/a | `d3/quantized/bartowski/DeepSeek-R1-Distill-Qwen-14B-GGUF/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `bartowski/DeepSeek-R1-Distill-Qwen-32B-GGUF` | C | d3 | 1 | complete | 32.4 | n/a | `d3/quantized/bartowski/DeepSeek-R1-Distill-Qwen-32B-GGUF/1dc8cf9ffa5dd333057ea1b09ccf4772d8726dec` | `registry.yaml`, `final_downloads.yaml` |
| `bartowski/Llama-3.3-70B-Instruct-GGUF` | C | d3 | 4 | complete | 69.8 | n/a | `d3/quantized/bartowski/Llama-3.3-70B-Instruct-GGUF/b6c5c9f176f3279204034e1d16d393105e95cb88` | `registry.yaml` |
| `bartowski/Meta-Llama-3.1-8B-Instruct-GGUF` | C | d3 | 1 | complete | 8.0 | n/a | `d3/quantized/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/bf5b95e96dac0462e2a09145ec66cae9a3f12067` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `bartowski/Mistral-Small-24B-Instruct-2501-GGUF` | C | d3 | 1 | complete | 23.3 | n/a | `d3/quantized/bartowski/Mistral-Small-24B-Instruct-2501-GGUF/62a613c92d5a5f73bba6d348b51433b232c4640c` | `registry.yaml`, `final_downloads.yaml` |
| `bartowski/Qwen2.5-14B-Instruct-GGUF` | C | d3 | 1 | complete | 14.6 | n/a | `d3/quantized/bartowski/Qwen2.5-14B-Instruct-GGUF/05244aa5d871c661c80082a15d3bce44714d068d` | `registry.yaml`, `final_downloads.yaml` |
| `bartowski/Qwen2.5-32B-Instruct-GGUF` | C | d3 | 1 | complete | 32.4 | n/a | `d3/quantized/bartowski/Qwen2.5-32B-Instruct-GGUF/2116cbb385b8ce3a4d28cf3bf1cd2039a55821a6` | `registry.yaml`, `final_downloads.yaml` |
| `bartowski/Qwen2.5-72B-Instruct-GGUF` | C | d3 | 4 | complete | 72.0 | n/a | `d3/quantized/bartowski/Qwen2.5-72B-Instruct-GGUF/d43fd973131bce821f41e2df3c78c6fe15c5627a` | `registry.yaml` |
| `bartowski/Qwen2.5-7B-Instruct-GGUF` | C | d3 | 1 | complete | 7.5 | n/a | `d3/quantized/bartowski/Qwen2.5-7B-Instruct-GGUF/8911e8a47f92bac19d6f5c64a2e2095bd2f7d031` | `registry.yaml`, `final_downloads.yaml` |
| `bartowski/Qwen2.5-Coder-14B-Instruct-GGUF` | C | d3 | 3 | — | — | n/a | `d3/quantized/bartowski/Qwen2.5-Coder-14B-Instruct-GGUF/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `bartowski/Qwen2.5-Coder-32B-Instruct-GGUF` | C | d3 | 1 | complete | 32.4 | n/a | `d3/quantized/bartowski/Qwen2.5-Coder-32B-Instruct-GGUF/40b525506a4f98ed425882fa6dfc90cc8139065e` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `bartowski/Qwen2.5-Coder-7B-Instruct-GGUF` | C | d3 | 3 | — | — | n/a | `d3/quantized/bartowski/Qwen2.5-Coder-7B-Instruct-GGUF/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `bartowski/deepseek-ai_DeepSeek-R1-0528-Qwen3-8B-GGUF` | C | d3 | 3 | — | — | n/a | `d3/quantized/bartowski/deepseek-ai_DeepSeek-R1-0528-Qwen3-8B-GGUF/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `bartowski/google_gemma-3-27b-it-GGUF` | C | d3 | 1 | complete | 26.7 | n/a | `d3/quantized/bartowski/google_gemma-3-27b-it-GGUF/4a05c54413bd0d87d77a97af403266f69cec0ee6` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `bartowski/google_gemma-4-26B-A4B-it-GGUF` | F | d2 | 3 | — | — | n/a | `d2/raw/bartowski/google_gemma-4-26B-A4B-it-GGUF/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `bartowski/google_gemma-4-31B-it-GGUF` | F | d1 | 3 | — | — | n/a | `d1/raw/bartowski/google_gemma-4-31B-it-GGUF/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `bartowski/google_gemma-4-E2B-it-GGUF` | F | d3 | 3 | — | — | n/a | `d3/raw/bartowski/google_gemma-4-E2B-it-GGUF/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `bartowski/google_gemma-4-E4B-it-GGUF` | F | d3 | 3 | — | — | n/a | `d3/raw/bartowski/google_gemma-4-E4B-it-GGUF/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `bartowski/phi-4-GGUF` | C | d3 | 1 | complete | 14.5 | n/a | `d3/quantized/bartowski/phi-4-GGUF/19cd65f97c2f1712a81c506611d3f9c94b16a1e1` | `registry.yaml`, `final_downloads.yaml` |
| `bartowski/starcoder2-15b-instruct-GGUF` | C | d3 | 3 | — | — | n/a | `d3/quantized/bartowski/starcoder2-15b-instruct-GGUF/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `bigcode/starcoder2-15b` | B | d2 | 2 | complete | 59.5 | n/a | `d2/raw/bigcode/starcoder2-15b/46d44742909c03ac8cee08eb03fdebce02e193ec` | `registry.yaml`, `registry-specialists.yaml`, `registry-legacy.yaml`, `final_downloads.yaml` |
| `cambridgeltl/SapBERT-from-PubMedBERT-fulltext` | G | d3 | 1 | complete | 1.6 | n/a | `d3/raw/cambridgeltl/SapBERT-from-PubMedBERT-fulltext/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `cognitivecomputations/Dolphin3.0-Llama3.1-8B` | D | d2 | 1 | complete | 15.0 | n/a | `d2/uncensored/cognitivecomputations/Dolphin3.0-Llama3.1-8B/f065677950dfc7e708d518d64cf1f5041ee007a0` | `registry.yaml`, `final_downloads.yaml` |
| `cognitivecomputations/dolphin-2.9.2-qwen2-72b` | D | d5 | 4 | pending | 135.4 | n/a | `d5/uncensored/cognitivecomputations/dolphin-2.9.2-qwen2-72b/main` | `registry.yaml`, `final_downloads.yaml` |
| `darkc0de/BuddyGlassUncensored2025.2` | D | d3 | 2 | — | — | n/a | `d3/uncensored/darkc0de/BuddyGlassUncensored2025.2/main` | `registry_high_risk.yaml` |
| `deepseek-ai/DeepSeek-Coder-V2-Instruct` | B | d1 | 1 | complete | 439.1 | n/a | `d1/raw/deepseek-ai/DeepSeek-Coder-V2-Instruct/2453c79a2a0947968a054947b53daa598cb3be52` | `registry.yaml` |
| `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct` | B | d2 | 1 | complete | 29.3 | n/a | `d2/raw/deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct/e434a23f91ba5b4923cf6c9d9a238eb4a08e3a11` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `deepseek-ai/DeepSeek-R1` | A | d1 | 4 | complete | 641.3 | n/a | `d1/raw/deepseek-ai/DeepSeek-R1/56d4cbbb4d29f4355bab4b9a39ccb717a14ad5ad` | `registry.yaml` |
| `deepseek-ai/DeepSeek-R1-0528` | A | d1 | 4 | complete | 641.3 | n/a | `d1/raw/deepseek-ai/DeepSeek-R1-0528/4236a6af538feda4548eca9ab308586007567f52` | `registry.yaml` |
| `deepseek-ai/DeepSeek-R1-0528-Qwen3-8B` | G | d3 | 3 | — | — | n/a | `d3/raw/deepseek-ai/DeepSeek-R1-0528-Qwen3-8B/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `deepseek-ai/DeepSeek-R1-Distill-Llama-70B` | A | d2 | 4 | complete | 131.4 | n/a | `d2/raw/deepseek-ai/DeepSeek-R1-Distill-Llama-70B/b1c0b44b4369b597ad119a196caf79a9c40e141e` | `registry.yaml` |
| `deepseek-ai/DeepSeek-R1-Distill-Llama-8B` | A | d2 | 2 | complete | 15.0 | n/a | `d2/raw/deepseek-ai/DeepSeek-R1-Distill-Llama-8B/6a6f4aa4197940add57724a7707d069478df56b1` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B` | A | d2 | 1 | complete | 27.5 | n/a | `d2/raw/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B/1df8507178afcc1bef68cd8c393f61a886323761` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` | A | d2 | 1 | complete | 61.0 | n/a | `d2/raw/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B/711ad2ea6aa40cfca18895e8aca02ab92df1a746` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` | G | d3 | 2 | complete | 14.2 | n/a | `d3/raw/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `deepseek-ai/DeepSeek-V3` | A | d1 | 2 | complete | 641.3 | n/a | `d1/raw/deepseek-ai/DeepSeek-V3/e815299b0bcbac849fa540c768ef21845365c9eb` | `registry-legacy.yaml` |
| `deepseek-ai/DeepSeek-V3-0324` | A | d1 | 2 | pending | 641.3 | n/a | `d1/raw/deepseek-ai/DeepSeek-V3-0324/main` | `registry-legacy.yaml` |
| `deepseek-ai/DeepSeek-V3-Base` | A | d1 | 4 | pending | 641.3 | n/a | `d1/raw/deepseek-ai/DeepSeek-V3-Base/main` | `registry.yaml` |
| `deepseek-ai/deepseek-coder-33b-instruct` | B | d1 | 1 | complete | 124.2 | n/a | `d1/raw/deepseek-ai/deepseek-coder-33b-instruct/61dc97b922b13995e7f83b7c8397701dbf9cfd4c` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `deepseek-ai/deepseek-coder-6.7b-instruct` | B | d3 | 1 | complete | 25.1 | n/a | `d3/raw/deepseek-ai/deepseek-coder-6.7b-instruct/e5d64addd26a6a1db0f9b863abf6ee3141936807` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `deepseek-ai/deepseek-math-7b-instruct` | G | d3 | 1 | complete | 12.9 | n/a | `d3/raw/deepseek-ai/deepseek-math-7b-instruct/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `deepseek-ai/deepseek-vl2` | F | d5 | 2 | pending | 51.2 | n/a | `d5/raw/deepseek-ai/deepseek-vl2/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `dmis-lab/biobert-base-cased-v1.2` | G | d3 | 1 | complete | 0.4 | n/a | `d3/raw/dmis-lab/biobert-base-cased-v1.2/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `emilyalsentzer/Bio_ClinicalBERT` | B | d3 | 1 | complete | 0.4 | n/a | `d3/raw/emilyalsentzer/Bio_ClinicalBERT/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `failspy/Meta-Llama-3-70B-Instruct-abliterated-v3.5` | D | d3 | 4 | complete | 131.4 | n/a | `d3/uncensored/failspy/Meta-Llama-3-70B-Instruct-abliterated-v3.5/main` | `registry.yaml`, `final_downloads.yaml` |
| `failspy/Phi-3-medium-4k-instruct-abliterated-v3` | D | d3 | 2 | — | — | n/a | `d3/uncensored/failspy/Phi-3-medium-4k-instruct-abliterated-v3/main` | `registry_high_risk.yaml` |
| `failspy/llama-3-70B-Instruct-abliterated` | D | d3 | 1 | — | — | n/a | `d3/uncensored/failspy/llama-3-70B-Instruct-abliterated/main` | `registry_high_risk.yaml` |
| `google/gemini-3-flash-preview` | F | d3 | 2 | skipped | — | n/a | `d3/raw/google/gemini-3-flash-preview/main` | `registry-legacy.yaml` |
| `google/gemini-3.1-flash-lite-preview` | F | d3 | 2 | skipped | — | n/a | `d3/raw/google/gemini-3.1-flash-lite-preview/main` | `registry-legacy.yaml` |
| `google/gemma-3-12b-it` | A | d2 | 2 | complete | 22.7 | n/a | `d2/raw/google/gemma-3-12b-it/main` | `registry.yaml` |
| `google/gemma-3-27b-it` | A | d2 | 2 | complete | 51.1 | n/a | `d2/raw/google/gemma-3-27b-it/main` | `registry.yaml` |
| `google/gemma-3-27b-pt` | A | d2 | 2 | complete | 51.1 | n/a | `d2/raw/google/gemma-3-27b-pt/main` | `registry.yaml` |
| `google/gemma-3-4b-it` | F | d3 | 2 | failed | 8.0 | n/a | `d3/raw/google/gemma-3-4b-it/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `google/gemma-4-26B-A4B` | F | d2 | 1 | failed | — | n/a | `d2/raw/google/gemma-4-26B-A4B/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `google/gemma-4-26B-A4B-it` | F | d2 | 1 | failed | — | n/a | `d2/raw/google/gemma-4-26B-A4B-it/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `google/gemma-4-31B` | F | d1 | 2 | failed | — | n/a | `d1/raw/google/gemma-4-31B/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `google/gemma-4-31B-it` | F | d1 | 2 | failed | — | n/a | `d1/raw/google/gemma-4-31B-it/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `google/gemma-4-E2B` | F | d3 | 1 | failed | — | n/a | `d3/raw/google/gemma-4-E2B/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `google/gemma-4-E2B-it` | F | d3 | 1 | failed | — | n/a | `d3/raw/google/gemma-4-E2B-it/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `google/gemma-4-E4B` | F | d3 | 1 | failed | — | n/a | `d3/raw/google/gemma-4-E4B/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `google/gemma-4-E4B-it` | F | d3 | 1 | failed | — | n/a | `d3/raw/google/gemma-4-E4B-it/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `google/medgemma-27b-it` | F | d3 | 0 | failed | 51.1 | n/a | `d3/raw/google/medgemma-27b-it/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `google/medgemma-27b-text-it` | G | d3 | 0 | complete | 50.3 | n/a | `d3/raw/google/medgemma-27b-text-it/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `google/medgemma-4b-it` | F | d3 | 0 | failed | 8.0 | n/a | `d3/raw/google/medgemma-4b-it/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `huihui-ai/DeepSeek-R1-Distill-Llama-70B-abliterated` | D | d2 | 4 | complete | 131.4 | n/a | `d2/uncensored/huihui-ai/DeepSeek-R1-Distill-Llama-70B-abliterated/116ff0fa55425b094a38a6bbf6faf2f5cafea335` | `registry.yaml`, `final_downloads.yaml` |
| `huihui-ai/DeepSeek-R1-Distill-Qwen-32B-abliterated` | D | d2 | 1 | complete | 61.0 | n/a | `d2/uncensored/huihui-ai/DeepSeek-R1-Distill-Qwen-32B-abliterated/939b7e288235a393e2aac8a16ddc3d48f9406f03` | `registry.yaml`, `final_downloads.yaml` |
| `huihui-ai/Llama-3.3-70B-Instruct-abliterated` | D | d2 | 4 | complete | 131.4 | n/a | `d2/uncensored/huihui-ai/Llama-3.3-70B-Instruct-abliterated/fa13334669544bab573e0e5313cad629a9c02e2c` | `registry.yaml`, `final_downloads.yaml` |
| `huihui-ai/Mistral-Small-24B-Instruct-2501-abliterated` | D | d2 | 1 | complete | 43.9 | n/a | `d2/uncensored/huihui-ai/Mistral-Small-24B-Instruct-2501-abliterated/main` | `registry.yaml`, `final_downloads.yaml` |
| `huihui-ai/Qwen2.5-14B-Instruct-abliterated-v2` | D | d3 | 2 | — | — | n/a | `d3/uncensored/huihui-ai/Qwen2.5-14B-Instruct-abliterated-v2/main` | `registry_high_risk.yaml` |
| `huihui-ai/Qwen2.5-72B-Instruct-abliterated` | D | d3 | 4 | complete | 135.4 | n/a | `d3/uncensored/huihui-ai/Qwen2.5-72B-Instruct-abliterated/ff4f9fe269d95bad2bd741af23b805cd9f449a8b` | `registry.yaml`, `final_downloads.yaml` |
| `huihui-ai/Qwen2.5-7B-Instruct-abliterated` | D | d3 | 2 | — | — | n/a | `d3/uncensored/huihui-ai/Qwen2.5-7B-Instruct-abliterated/main` | `registry_high_risk.yaml` |
| `huihui-ai/Qwen2.5-7B-Instruct-abliterated-v2` | D | d3 | 2 | — | — | n/a | `d3/uncensored/huihui-ai/Qwen2.5-7B-Instruct-abliterated-v2/main` | `registry_high_risk.yaml` |
| `ibm-granite/granite-20b-code-base-8k` | B | d2 | 2 | complete | 37.4 | n/a | `d2/raw/ibm-granite/granite-20b-code-base-8k/main` | `registry.yaml` |
| `ibm-granite/granite-20b-code-instruct-r1.1` | B | d2 | 2 | complete | 37.4 | n/a | `d2/raw/ibm-granite/granite-20b-code-instruct-r1.1/main` | `registry.yaml` |
| `internlm/internlm2_5-20b-chat` | A | d2 | 2 | pending | 37.0 | n/a | `d2/raw/internlm/internlm2_5-20b-chat/main` | `registry.yaml`, `registry-legacy.yaml` |
| `intfloat/e5-large-v2` | B | d3 | 1 | — | — | n/a | `d3/raw/intfloat/e5-large-v2/main` | `registry.yaml` |
| `intfloat/e5-mistral-7b-instruct` | B | d3 | 2 | complete | 26.6 | n/a | `d3/raw/intfloat/e5-mistral-7b-instruct/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `jeffmeloy/Qwen2.5-7B-nerd-uncensored-v0.9` | D | d3 | 2 | — | — | n/a | `d3/uncensored/jeffmeloy/Qwen2.5-7B-nerd-uncensored-v0.9/main` | `registry_high_risk.yaml` |
| `jeffmeloy/Qwen2.5-7B-nerd-uncensored-v1.0` | D | d3 | 2 | — | — | n/a | `d3/uncensored/jeffmeloy/Qwen2.5-7B-nerd-uncensored-v1.0/main` | `registry_high_risk.yaml` |
| `jinaai/jina-embeddings-v3` | B | d3 | 1 | complete | 2.1 | n/a | `d3/raw/jinaai/jina-embeddings-v3/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `meta-llama/Llama-3.1-405B` | A | d1 | 4 | pending | 2275.9 | n/a | `d1/raw/meta-llama/Llama-3.1-405B/b906e4dc842aa489c962f9db26554dcfdde901fe` | `registry.yaml` |
| `meta-llama/Llama-3.1-405B-Instruct` | A | d1 | 4 | pending | 2276.0 | n/a | `d1/raw/meta-llama/Llama-3.1-405B-Instruct/main` | `registry.yaml` |
| `meta-llama/Llama-3.1-70B-Instruct` | A | d3 | 4 | complete | 262.9 | n/a | `d3/raw/meta-llama/Llama-3.1-70B-Instruct/1605565b47bb9346c5515c34102e054115b4f98b` | `registry.yaml` |
| `meta-llama/Llama-3.1-8B-Instruct` | A | d2 | 2 | complete | 29.9 | n/a | `d2/raw/meta-llama/Llama-3.1-8B-Instruct/0e9e39f249a16976918f6564b8830bc894c89659` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `meta-llama/Llama-3.2-11B-Vision-Instruct` | F | d3 | 2 | complete | 39.7 | n/a | `d3/raw/meta-llama/Llama-3.2-11B-Vision-Instruct/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `meta-llama/Llama-3.2-1B` | A | d3 | 2 | complete | 4.6 | n/a | `d3/raw/meta-llama/Llama-3.2-1B/main` | `registry.yaml` |
| `meta-llama/Llama-3.2-1B-Instruct` | A | d3 | 2 | complete | 4.6 | n/a | `d3/raw/meta-llama/Llama-3.2-1B-Instruct/main` | `registry.yaml` |
| `meta-llama/Llama-3.2-3B-Instruct` | A | d2 | 1 | complete | 12.0 | n/a | `d2/raw/meta-llama/Llama-3.2-3B-Instruct/0cb88a4f764b7a12671c53f0838cd831a0843b95` | `registry.yaml` |
| `meta-llama/Llama-3.2-90B-Vision-Instruct` | F | d5 | 4 | pending | 330.5 | n/a | `d5/raw/meta-llama/Llama-3.2-90B-Vision-Instruct/main` | `registry.yaml` |
| `meta-llama/Llama-3.3-70B-Instruct` | A | d1 | 4 | pending | 262.9 | n/a | `d1/raw/meta-llama/Llama-3.3-70B-Instruct/6f6073b423013f6a7d4d9f39144961bfbfbc386b` | `registry.yaml` |
| `meta-llama/Llama-4-Maverick-17B-128E` | A | d1 | 4 | pending | 748.0 | n/a | `d1/raw/meta-llama/Llama-4-Maverick-17B-128E/10751cb97a4d7c90f7ed89196b98eb8220cfa1c2` | `registry.yaml` |
| `meta-llama/Llama-4-Maverick-17B-128E-Instruct` | A | d2 | 4 | — | 748.0 | n/a | `d2/raw/meta-llama/Llama-4-Maverick-17B-128E-Instruct/main` | `registry.yaml` |
| `meta-llama/Llama-4-Scout-17B-16E` | A | d1 | 4 | pending | 202.4 | n/a | `d1/raw/meta-llama/Llama-4-Scout-17B-16E/main` | `registry.yaml` |
| `meta-llama/Llama-4-Scout-17B-16E-Instruct` | A | d2 | 4 | — | 202.4 | n/a | `d2/raw/meta-llama/Llama-4-Scout-17B-16E-Instruct/main` | `registry.yaml` |
| `meta-llama/Llama-Guard-4-12B` | E | d3 | 1 | complete | 22.4 | n/a | `d3/raw/meta-llama/Llama-Guard-4-12B/87acb4b94e930c3d679e6e7ee9d57e2feab9ea71` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `meta-llama/Llama-Prompt-Guard-2-22M` | E | d3 | 1 | complete | 0.3 | n/a | `d3/raw/meta-llama/Llama-Prompt-Guard-2-22M/11614a155199674a0a95e6602d6ab0417b790ed0` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `meta-llama/Llama-Prompt-Guard-2-86M` | E | d3 | 1 | complete | 1.1 | n/a | `d3/raw/meta-llama/Llama-Prompt-Guard-2-86M/a8ded8e697ce7c355e395a0df51f94adb4a2fd27` | `registry.yaml` |
| `microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext` | G | d3 | 1 | complete | 0.8 | n/a | `d3/raw/microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `microsoft/Phi-3-mini-128k-instruct` | A | d3 | 2 | pending | 7.1 | n/a | `d3/raw/microsoft/Phi-3-mini-128k-instruct/main` | `registry.yaml`, `registry-legacy.yaml` |
| `microsoft/Phi-4-mini-instruct` | A | d5 | 1 | complete | 7.2 | n/a | `d5/raw/microsoft/Phi-4-mini-instruct/main` | `registry.yaml` |
| `microsoft/phi-4` | A | d2 | 1 | complete | 27.3 | n/a | `d2/raw/microsoft/phi-4/main` | `registry.yaml` |
| `mistralai/Codestral-22B-v0.1` | B | d2 | 2 | complete | 82.9 | n/a | `d2/raw/mistralai/Codestral-22B-v0.1/28b1c1a51dabe9d86ca8c41420ada1984632498f` | `registry.yaml` |
| `mistralai/Devstral-Small-2507` | B | d2 | 1 | complete | 87.8 | n/a | `d2/raw/mistralai/Devstral-Small-2507/main` | `registry.yaml` |
| `mistralai/Devstral-Small-2507_gguf` | C | d3 | 1 | complete | 23.3 | n/a | `d3/quantized/mistralai/Devstral-Small-2507_gguf/ee2f0c00c5c86862f471fbf533268cf01b80d4a6` | `registry.yaml`, `final_downloads.yaml` |
| `mistralai/Leanstral-120B-A6B` | E | d5 | 4 | failed | — | n/a | `d5/raw/mistralai/Leanstral-120B-A6B/main` | `registry.yaml` |
| `mistralai/Mathstral-7B-v0.1` | G | d3 | 1 | complete | 40.5 | n/a | `d3/raw/mistralai/Mathstral-7B-v0.1/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `mistralai/Mistral-Large-Instruct-2411` | A | d1 | 4 | complete | 456.8 | n/a | `d1/raw/mistralai/Mistral-Large-Instruct-2411/ba78820945ae22361b0274cf0ae6d696c967c1a4` | `registry.yaml` |
| `mistralai/Mistral-Small-24B-Instruct-2501` | A | d2 | 1 | complete | 87.8 | n/a | `d2/raw/mistralai/Mistral-Small-24B-Instruct-2501/9527884be6e5616bdd54de542f9ae13384489724` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `mistralai/Mixtral-8x22B-Instruct-v0.1` | A | d2 | 4 | pending | 261.9 | n/a | `d2/raw/mistralai/Mixtral-8x22B-Instruct-v0.1/cc88a6cc19fbd17d9f1c0ee0b0d70a748dce698d` | `registry.yaml` |
| `mistralai/Mixtral-8x7B-Instruct-v0.1` | A | d2 | 1 | pending | 177.4 | n/a | `d2/raw/mistralai/Mixtral-8x7B-Instruct-v0.1/eba92302a2861cdc0098cc54bc9f17cb2c47eb61` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `mlabonne/Llama-3.1-70B-Instruct-lorablated` | D | d2 | 4 | complete | 131.4 | n/a | `d2/uncensored/mlabonne/Llama-3.1-70B-Instruct-lorablated/main` | `registry.yaml`, `final_downloads.yaml` |
| `mlabonne/NeuralDaredevil-8B-abliterated` | D | d2 | 2 | complete | 15.0 | n/a | `d2/uncensored/mlabonne/NeuralDaredevil-8B-abliterated/main` | `registry.yaml`, `final_downloads.yaml` |
| `mlabonne/NeuralDaredevil-8B-abliterated-GGUF` | D | d3 | 2 | complete | 8.0 | n/a | `d3/uncensored/mlabonne/NeuralDaredevil-8B-abliterated-GGUF/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `mlx-community/dbrx-instruct-4bit` | C | d3 | 4 | failed | 69.8 | n/a | `d3/quantized/mlx-community/dbrx-instruct-4bit/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `mosaicml/mpt-30b` | A | d2 | 2 | failed | — | n/a | `d2/raw/mosaicml/mpt-30b/main` | `registry.yaml` |
| `mosaicml/mpt-30b-instruct` | A | d2 | 2 | failed | — | n/a | `d2/raw/mosaicml/mpt-30b-instruct/main` | `registry.yaml` |
| `mosaicml/mpt-7b` | A | d2 | 2 | failed | — | n/a | `d2/raw/mosaicml/mpt-7b/main` | `registry.yaml` |
| `mosaicml/mpt-7b-instruct` | A | d2 | 2 | failed | — | n/a | `d2/raw/mosaicml/mpt-7b-instruct/main` | `registry.yaml` |
| `nbeerbower/EVA-abliterated-TIES-Qwen2.5-14B` | D | d3 | 2 | — | — | n/a | `d3/uncensored/nbeerbower/EVA-abliterated-TIES-Qwen2.5-14B/main` | `registry_high_risk.yaml` |
| `nbeerbower/Llama-3.1-Nemotron-lorablated-70B` | D | d2 | 4 | — | — | n/a | `d2/uncensored/nbeerbower/Llama-3.1-Nemotron-lorablated-70B/main` | `registry.yaml`, `final_downloads.yaml` |
| `nvidia/Llama-3.1-Nemotron-70B-Instruct` | A | d2 | 4 | complete | 0.0 | n/a | `d2/raw/nvidia/Llama-3.1-Nemotron-70B-Instruct/a83af1f4968437064635f6726fb745e5b615e863` | `registry.yaml` |
| `nvidia/Llama-3_1-Nemotron-Ultra-253B-v1` | D | d1 | 4 | pending | 472.0 | n/a | `d1/uncensored/nvidia/Llama-3_1-Nemotron-Ultra-253B-v1/main` | `registry.yaml`, `final_downloads.yaml` |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` | A | d2 | 3 | complete | 58.8 | n/a | `d2/raw/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-Base-BF16` | A | d2 | 1 | complete | 58.8 | n/a | `d2/raw/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-Base-BF16/97ab8012882a655dc38df4fee47422aca9caca07` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8` | C | d3 | 4 | complete | 30.5 | n/a | `d3/quantized/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4` | C | d3 | 2 | complete | 18.0 | n/a | `d3/quantized/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4/main` | `registry.yaml`, `final_downloads.yaml` |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16` | D | d1 | 4 | failed | 230.3 | n/a | `d1/uncensored/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16/main` | `registry.yaml`, `final_downloads.yaml` |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-Base-BF16` | D | d1 | 4 | failed | 230.3 | n/a | `d1/uncensored/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-Base-BF16/main` | `registry.yaml`, `final_downloads.yaml` |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8` | D | d5 | 4 | failed | 119.6 | n/a | `d5/uncensored/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8/main` | `registry.yaml`, `final_downloads.yaml` |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4` | D | d5 | 4 | complete | 74.8 | n/a | `d5/uncensored/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4/main` | `registry.yaml`, `final_downloads.yaml` |
| `open-r1/OlympicCoder-32B` | B | d2 | 2 | complete | 61.0 | n/a | `d2/raw/open-r1/OlympicCoder-32B/34113aee9d255591a1fa75b60d1e3422e82c3b1f` | `registry.yaml` |
| `rombodawg/Rombos-LLM-V2.5-Qwen-72b` | D | d5 | 4 | pending | 135.4 | n/a | `d5/uncensored/rombodawg/Rombos-LLM-V2.5-Qwen-72b/main` | `registry.yaml`, `final_downloads.yaml` |
| `sentence-transformers/all-mpnet-base-v2` | B | d3 | 3 | — | — | n/a | `d3/raw/sentence-transformers/all-mpnet-base-v2/main` | `registry.yaml` |
| `seyonec/ChemBERTa-zinc-base-v1` | B | d3 | 1 | complete | 0.2 | n/a | `d3/raw/seyonec/ChemBERTa-zinc-base-v1/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `stanford-crfm/BioMedLM` | G | d3 | 1 | complete | 10.0 | n/a | `d3/raw/stanford-crfm/BioMedLM/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `tensorblock/DeepSeek-R1-Distill-Llama-70B-abliterated-GGUF` | D | d3 | 4 | complete | 31.9 | n/a | `d3/uncensored/tensorblock/DeepSeek-R1-Distill-Llama-70B-abliterated-GGUF/89b48f9faec5188e7a05011676538aaf0889ad9a` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `tensorblock/DeepSeek-R1-Distill-Qwen-32B-abliterated-GGUF` | D | d3 | 1 | complete | 14.8 | n/a | `d3/uncensored/tensorblock/DeepSeek-R1-Distill-Qwen-32B-abliterated-GGUF/de00cb261ea6fea79a45ffbb6e583befed7be954` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `tensorblock/Llama-3.2-3B-Instruct-GGUF` | C | d3 | 1 | complete | 1.6 | n/a | `d3/quantized/tensorblock/Llama-3.2-3B-Instruct-GGUF/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `tensorblock/Llama-3.3-70B-Instruct-abliterated-GGUF` | D | d5 | 4 | complete | 31.9 | n/a | `d5/uncensored/tensorblock/Llama-3.3-70B-Instruct-abliterated-GGUF/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `tensorblock/Mistral-Small-24B-Instruct-2501-abliterated-GGUF` | D | d3 | 1 | complete | 10.7 | n/a | `d3/uncensored/tensorblock/Mistral-Small-24B-Instruct-2501-abliterated-GGUF/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `tensorblock/Mixtral-8x7B-Instruct-v0.1-GGUF` | C | d3 | 3 | — | — | n/a | `d3/quantized/tensorblock/Mixtral-8x7B-Instruct-v0.1-GGUF/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `tensorblock/deepseek-coder-33b-instruct-GGUF` | C | d3 | 3 | — | — | n/a | `d3/quantized/tensorblock/deepseek-coder-33b-instruct-GGUF/main` | `registry-specialists.yaml`, `final_downloads.yaml` |
| `tiiuae/Falcon3-10B-Instruct` | A | d1 | 2 | pending | 19.2 | n/a | `d1/raw/tiiuae/Falcon3-10B-Instruct/main` | `registry.yaml`, `registry-legacy.yaml` |
| `tiiuae/falcon-180B` | A | d5 | 4 | failed | 334.4 | n/a | `d5/raw/tiiuae/falcon-180B/main` | `registry.yaml` |
| `tiiuae/falcon-180B-chat` | A | d2 | 4 | pending | 334.4 | n/a | `d2/raw/tiiuae/falcon-180B-chat/main` | `registry.yaml` |
| `tiiuae/falcon-40b-instruct` | A | d2 | 2 | complete | 77.9 | n/a | `d2/raw/tiiuae/falcon-40b-instruct/main` | `registry.yaml` |
| `unsloth/DeepSeek-V3-GGUF` | C | d1 | 2 | pending | 376.7 | n/a | `d1/quantized/unsloth/DeepSeek-V3-GGUF/main` | `registry-legacy.yaml`, `final_downloads.yaml` |
| `unsloth/Phi-4-mini-instruct-GGUF` | C | d3 | 1 | complete | 3.8 | n/a | `d3/quantized/unsloth/Phi-4-mini-instruct-GGUF/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `unsloth/Qwen3-4B-Instruct-2507-GGUF` | C | d3 | 1 | complete | 4.0 | n/a | `d3/quantized/unsloth/Qwen3-4B-Instruct-2507-GGUF/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `unsloth/phi-4-unsloth-bnb-4bit` | C | d3 | 1 | complete | 9.7 | n/a | `d3/quantized/unsloth/phi-4-unsloth-bnb-4bit/main` | `registry.yaml`, `registry-specialists.yaml`, `final_downloads.yaml` |
| `upstage/solar-pro-preview-instruct` | A | d1 | 2 | pending | 41.2 | n/a | `d1/raw/upstage/solar-pro-preview-instruct/main` | `registry.yaml`, `registry-legacy.yaml` |
| `zetasepic/Qwen2.5-32B-Instruct-abliterated-v2` | D | d3 | 2 | — | — | n/a | `d3/uncensored/zetasepic/Qwen2.5-32B-Instruct-abliterated-v2/main` | `registry_high_risk.yaml` |
| `zetasepic/Qwen2.5-72B-Instruct-abliterated` | D | d3 | 4 | — | — | n/a | `d3/uncensored/zetasepic/Qwen2.5-72B-Instruct-abliterated/main` | `registry.yaml`, `final_downloads.yaml` |

