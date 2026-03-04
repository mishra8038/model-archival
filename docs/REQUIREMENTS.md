# Model Archival — Requirements

**Status:** Draft v0.5 — 2026-03-04  
**Purpose:** Offline archival of open-source LLM/LRM weights for long-term preservation, reproducibility, and offline inference. Four tiers: raw full-precision general/reasoning models (A), raw code-specialist models (B), quantized GGUF models (C), and uncensored/abliterated variants (D).

---

## 1. Goals

1. Download the definitive open-source LLMs, LRMs, and code models in their highest-fidelity published precision (BF16/FP16 safetensors) from Hugging Face — referred to as the **Major Models** list.
2. Download top code-specialist models as a dedicated **Code Models** sub-list under the same raw-weight standard.
3. Download a curated set of **Quantized Models** (GGUF, Q4_K_M and Q8_0) sourced from Hugging Face (bartowski / unsloth / lmstudio-community) and directly from Ollama's library, for convenient offline inference.
4. Download curated **Uncensored / Abliterated** variants of the major models (Tier D) — abliterated weights sourced from established HF authors (huihui-ai, mlabonne, cognitivecomputations) mapped to their parent models in the registry.
5. Store all weights in a structured, self-describing directory hierarchy spread across the available drive inventory.
6. Record and verify cryptographic checksums (SHA-256) for every file at download time and on demand thereafter.
7. Make all downloads resumable, idempotent, and recoverable — interrupted downloads restart without re-fetching whole files.
8. Maintain a canonical **model registry** (YAML) as the single source of truth: model ID → HF repo → pinned commit SHA → tier → licence → auth requirements → assigned drive.
9. Provide a CLI (`archiver`) with sub-commands: `download`, `verify`, `status`, `list`, `pin`.

---

## 2. Non-Goals

- No quantization or format conversion by this tool — quantized files are sourced as-is.
- No automatic version upgrades; new versions are added deliberately via registry edits.
- No inference, serving, or cloud sync.

---

## 3. Model Tiers

### Tier A — Major Models (raw BF16 full-precision)

The union of the former Priority-1 and Priority-2 lists. Selected on: open-weights licence, frontier capability at time of archival, architectural diversity.

#### Tier A1 — General / Reasoning

Models are listed in **download order** (registry `priority` field). Token-free models run first; gated models that require an HF token are deferred to the end of the queue so the archive progresses immediately while tokens are being obtained.

**Token-free (download first — priority 1):**

| Pri | Model | HF Repo | Est. Size | Licence |
|-----|-------|---------|-----------|---------|
| 1 | DeepSeek-V3 | `deepseek-ai/DeepSeek-V3` | ~1,340 GB | MIT |
| 1 | DeepSeek-R1 | `deepseek-ai/DeepSeek-R1` | ~850 GB | MIT |
| 1 | DeepSeek-R1-Distill-Llama-70B | `deepseek-ai/DeepSeek-R1-Distill-Llama-70B` | ~140 GB | MIT |
| 1 | DeepSeek-R1-Distill-Qwen-32B | `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` | ~64 GB | MIT |
| 1 | Qwen2.5 72B Instruct | `Qwen/Qwen2.5-72B-Instruct` | ~144 GB | Qwen |
| 1 | Qwen2.5 32B Instruct | `Qwen/Qwen2.5-32B-Instruct` | ~64 GB | Apache 2.0 |
| 1 | Qwen2.5 7B Instruct | `Qwen/Qwen2.5-7B-Instruct` | ~15 GB | Apache 2.0 |
| 1 | Mistral 7B v0.3 | `mistralai/Mistral-7B-Instruct-v0.3` | ~14 GB | Apache 2.0 |
| 1 | Phi-4 (14B) | `microsoft/phi-4` | ~28 GB | MIT |
| 1 | Command R+ (104B) | `CohereForAI/c4ai-command-r-plus` | ~208 GB | CC-BY-NC |

**Gated — HF token required (download last — priority 2):**

| Pri | Model | HF Repo | Est. Size | Licence | Token needed |
|-----|-------|---------|-----------|---------|-------------|
| 2 | Llama 3.1 405B Instruct | `meta-llama/Llama-3.1-405B-Instruct` | ~756 GB | Llama 3.1 | Meta Llama |
| 2 | Llama 3.1 70B Instruct | `meta-llama/Llama-3.1-70B-Instruct` | ~140 GB | Llama 3.1 | Meta Llama |
| 2 | Llama 3.3 70B Instruct | `meta-llama/Llama-3.3-70B-Instruct` | ~140 GB | Llama 3.3 | Meta Llama |
| 2 | Llama 3.1 8B Instruct | `meta-llama/Llama-3.1-8B-Instruct` | ~16 GB | Llama 3.1 | Meta Llama |
| 2 | Gemma 3 27B IT | `google/gemma-3-27b-it` | ~54 GB | Gemma ToU | Google Gemma |
| 2 | Gemma 3 27B PT | `google/gemma-3-27b-pt` | ~54 GB | Gemma ToU | Google Gemma |
| 2 | Gemma 3 12B IT | `google/gemma-3-12b-it` | ~24 GB | Gemma ToU | Google Gemma |
| 2 | Mistral Large 2 (2407) | `mistralai/Mistral-Large-Instruct-2407` | ~246 GB | Mistral Research | Mistral |

**Tier A1 subtotal: ~4,341 GB (~4.2 TB)**

---

### Tier B — Code Models (raw BF16 full-precision)

Frontier code-generation and software-engineering specialist models.  
**Selection criteria:** must appear at or near the top of at least two established code benchmarks (HumanEval, MBPP+, SWE-bench Verified, LiveCodeBench) and have a clear, well-recognised reputation for code output quality. Models that are merely "decent at code" are excluded — Tier A general models already cover that use case.

**Token-free (priority 1):**

| Pri | Model | HF Repo | Params | Est. Size | Licence | Key Benchmarks |
|-----|-------|---------|--------|-----------|---------|----------------|
| 1 | **Qwen2.5-Coder 32B Instruct** | `Qwen/Qwen2.5-Coder-32B-Instruct` | 32B | ~64 GB | Apache 2.0 | 90% HumanEval; #2 Python coding open leaderboard; 92 langs |
| 1 | **DeepSeek-Coder-V2-Instruct** | `deepseek-ai/DeepSeek-Coder-V2-Instruct` | 236B MoE | ~440 GB | DeepSeek | 90.2% HumanEval; 338 langs; 128K ctx; matches GPT-4-Turbo on code |
| 1 | **DeepSeek-Coder-V2-Lite-Instruct** | `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct` | 16B MoE | ~30 GB | DeepSeek | 81.1% HumanEval; 2.4B active params; best efficiency ratio in class |
| 1 | **Devstral Small 2507** | `mistralai/Devstral-Small-2507` | 24B | ~48 GB | Apache 2.0 | 52.4% SWE-bench Verified; best open model for agentic repo-level coding |

**Gated — HF token required (priority 2):**

| Pri | Model | HF Repo | Params | Est. Size | Licence | Token needed |
|-----|-------|---------|--------|-----------|---------|-------------|
| 2 | **Codestral 22B v0.1** | `mistralai/Codestral-22B-v0.1` | 22B | ~44 GB | Mistral MNPL | Mistral |

**Tier B subtotal: ~626 GB**

**Removed from earlier draft and why:**
- **Qwen2.5-Coder 7B** — solid but not a quality leader; small-size coverage already provided by Tier A (Mistral 7B, Llama 8B) and Tier C quants.
- **Phi-4 Mini (3.8B)** — general-purpose small model; code scores unremarkable vs dedicated code models. Not benchmark-established as a code specialist.
- **Devstral Small 2505** → superseded by **2507** (+5.6 pp SWE-bench); 2505 dropped.
- **Gemma 3 27B IT** — already in Tier A; not a recognised code specialist by benchmark.

**Complementary roles within Tier B:**
- Qwen2.5-Coder 32B → best pure code generation / completion at practical size
- DeepSeek-Coder-V2 → maximum benchmark performance; the frontier open code model
- DeepSeek-Coder-V2-Lite → efficient daily driver (MoE, 2.4B active)
- Codestral 22B → IDE integration / FIM / autocomplete specialist
- Devstral Small 2507 → agentic SWE tasks; repo-level reasoning; OpenHands/agent frameworks

---

### Tier C — Quantized Models (GGUF)

Curated set of GGUF quantizations for offline inference without full-precision hardware requirements. Two quantization levels per model where available:
- **Q4_K_M** — best quality/size balance; ~75% size reduction; default for Ollama
- **Q8_0** — near-lossless quality; ~50% size reduction; preferred when storage permits

**Sources (in preference order):**
1. `bartowski/<model>-GGUF` on HuggingFace — most comprehensive, well-tagged
2. `unsloth/<model>-GGUF` — Dynamic 2.0 quants; superior calibration for MoE models
3. `lmstudio-community/<model>-GGUF` — alternative for some models
4. Ollama library (`ollama pull <name>`) — for models with official Ollama manifests

> All Tier C GGUF repos (bartowski, unsloth, mistralai official GGUF) are public — no HF token required. All priority 1.

#### Tier C — General / Reasoning

| # | Model | Source Repo | Q4_K_M | Q8_0 |
|---|-------|------------|--------|------|
| 1 | Llama 3.3 70B Instruct | `bartowski/Llama-3.3-70B-Instruct-GGUF` | ~43 GB | ~75 GB |
| 2 | Llama 3.1 8B Instruct | `bartowski/Meta-Llama-3.1-8B-Instruct-GGUF` | ~5 GB | ~9 GB |
| 3 | DeepSeek-R1 671B | `unsloth/DeepSeek-R1-GGUF` | ~340 GB | ~680 GB |
| 4 | DeepSeek-R1-Distill-Qwen-32B | `bartowski/DeepSeek-R1-Distill-Qwen-32B-GGUF` | ~19 GB | ~35 GB |
| 5 | DeepSeek-R1-Distill-Llama-70B | `bartowski/DeepSeek-R1-Distill-Llama-70B-GGUF` | ~43 GB | ~75 GB |
| 6 | DeepSeek-V3 671B | `unsloth/DeepSeek-V3-GGUF` | ~340 GB | ~680 GB |
| 7 | Qwen2.5 72B Instruct | `bartowski/Qwen2.5-72B-Instruct-GGUF` | ~44 GB | ~77 GB |
| 8 | Qwen2.5 32B Instruct | `bartowski/Qwen2.5-32B-Instruct-GGUF` | ~20 GB | ~34 GB |
| 9 | Qwen2.5 7B Instruct | `bartowski/Qwen2.5-7B-Instruct-GGUF` | ~5 GB | ~8 GB |
| 10 | Mistral 7B v0.3 | `bartowski/Mistral-7B-Instruct-v0.3-GGUF` | ~4 GB | ~8 GB |
| 11 | Gemma 3 27B IT | `bartowski/gemma-3-27b-it-GGUF` | ~17 GB | ~29 GB |
| 12 | Phi-4 14B | `bartowski/phi-4-GGUF` | ~9 GB | ~15 GB |

#### Tier C — Code Models

Mirrors Tier B exactly — only models with established code benchmark credentials.

| # | Model | Source Repo | Q4_K_M | Q8_0 |
|---|-------|------------|--------|------|
| 1 | Qwen2.5-Coder 32B Instruct | `bartowski/Qwen2.5-Coder-32B-Instruct-GGUF` | ~20 GB | ~34 GB |
| 2 | DeepSeek-Coder-V2-Lite Instruct | `bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF` | ~9 GB | ~17 GB |
| 3 | Codestral 22B v0.1 | `bartowski/Codestral-22B-v0.1-GGUF` | ~13 GB | ~24 GB |
| 4 | Devstral Small 2507 | `mistralai/Devstral-Small-2507_gguf` | ~13 GB | ~24 GB |

> Devstral 2507 has an official Mistral GGUF repo; prefer it over community re-quantizations.  
> DeepSeek-Coder-V2-Instruct (236B) has no practical GGUF at Q8_0 (~480 GB); Q4_K_M (~120 GB) available via `unsloth/DeepSeek-Coder-V2-Instruct-GGUF` if desired — deferred to optional.

> **Tier C storage note:** The 671B GGUF quants (DeepSeek-V3 and R1) are very large even at Q4.  
> It is recommended to archive Q4_K_M only for the 671B models and Q8_0 for all others (≤72B), since the quality loss from Q4 is negligible at 72B+ but significant at smaller sizes.

**Tier C subtotal (Q4_K_M 671B + Q8_0 others): ~1,090 GB (~1.1 TB)**

---

### Tier D — Uncensored / Abliterated Models

Abliterated variants of the major models in our archive. "Abliteration" removes the refusal direction from a model's residual stream without retraining, producing weights that are otherwise identical in quality to the source model. These are sourced from well-established HF authors with high download counts and documented methodology.

**Curation policy:** Only archive a Tier D variant when its **parent model is already in Tier A or Tier B**. The abliterated weight is treated as an alternate version of the same model — same tier assignment, stored under `models/uncensored/`.

**Primary sources:**
- `huihui-ai` — largest systematic abliteration collection; covers Llama, DeepSeek, Qwen, Mistral
- `mlabonne` — original abliteration method author; Llama 3.x lorablated variants
- `cognitivecomputations` — Dolphin series; supervised uncensored fine-tunes (not abliteration)

> All Tier D repos (huihui-ai, mlabonne, cognitivecomputations) are public — no HF token required. All priority 1.

#### Tier D — Raw BF16 (abliterated, maps to parent in Tier A/B)

| # | Model | HF Repo | Parent | Est. Size | Licence | Method |
|---|-------|---------|--------|-----------|---------|--------|
| 1 | Llama-3.3-70B-Instruct-abliterated | `huihui-ai/Llama-3.3-70B-Instruct-abliterated` | Llama 3.3 70B | ~140 GB | Llama 3.3 | Abliteration |
| 2 | Llama-3.1-70B-Instruct-lorablated | `mlabonne/Llama-3.1-70B-Instruct-lorablated` | Llama 3.1 70B | ~140 GB | Llama 3.1 | LoRA abliteration |
| 3 | DeepSeek-R1-Distill-Llama-70B-abliterated | `huihui-ai/DeepSeek-R1-Distill-Llama-70B-abliterated` | DS-R1-Distill-L70B | ~140 GB | MIT | Abliteration |
| 4 | DeepSeek-R1-Distill-Qwen-32B-abliterated | `huihui-ai/DeepSeek-R1-Distill-Qwen-32B-abliterated` | DS-R1-Distill-Q32B | ~64 GB | MIT | Abliteration |
| 5 | Dolphin3.0-Llama3.1-8B | `cognitivecomputations/Dolphin3.0-Llama3.1-8B` | Llama 3.1 8B | ~16 GB | Llama 3.1 | Supervised FT |
| 6 | NeuralDaredevil-8B-abliterated | `mlabonne/NeuralDaredevil-8B-abliterated` | Llama 3.1 8B base | ~16 GB | Llama 3.1 | DPO + abliteration |
| 7 | Mistral-Small-24B-abliterated | `huihui-ai/Mistral-Small-24B-Instruct-2501-abliterated` | Mistral Small 24B | ~48 GB | Apache 2.0 | Abliteration |

**Tier D raw subtotal: ~564 GB**

#### Tier D — GGUF (Q8_0 preferred, Q4_K_M where large)

| # | Model | Source Repo | Q4_K_M | Q8_0 |
|---|-------|------------|--------|------|
| 1 | Llama-3.3-70B-abliterated | `huihui-ai/Llama-3.3-70B-Instruct-abliterated-GGUF` | ~43 GB | ~75 GB |
| 2 | DeepSeek-R1-Distill-Llama-70B-abliterated | `huihui-ai/DeepSeek-R1-Distill-Llama-70B-abliterated-GGUF` | ~43 GB | ~75 GB |
| 3 | DeepSeek-R1-Distill-Qwen-32B-abliterated | `huihui-ai/DeepSeek-R1-Distill-Qwen-32B-abliterated-GGUF` | ~19 GB | ~35 GB |
| 4 | Dolphin3.0-Llama3.1-8B | via bartowski / community GGUF | ~5 GB | ~9 GB |
| 5 | NeuralDaredevil-8B-abliterated | `mlabonne/NeuralDaredevil-8B-abliterated-GGUF` | ~5 GB | ~9 GB |
| 6 | Mistral-Small-24B-abliterated | `huihui-ai/Mistral-Small-24B-abliterated-GGUF` | ~14 GB | ~25 GB |

**Tier D GGUF subtotal (Q8_0): ~228 GB**

> Note: Abliterated variants of the 671B DeepSeek models (V3, R1) exist  
> (`huihui-ai/DeepSeek-R1-671b-abliterated`, `huihui-ai/DeepSeek-V3-abliterated`) but are  
> each ~850–1,340 GB raw. Given storage constraints, these are **deferred** — archive the  
> standard Tier A versions first; add abliterated 671B variants in a future expansion.

---

## 4. Aggregate Storage Estimate

| Tier | Content | Count | Est. Size |
|------|---------|-------|-----------|
| A — Major Models (raw BF16) | General + reasoning | 18 models | ~4.3 TB |
| B — Code Models (raw BF16) | Benchmark-established specialists | 5 models | ~0.6 TB |
| C — Quantized GGUF (general + code) | Q4_K_M / Q8_0 | 16 model sets | ~1.1 TB |
| D — Uncensored raw BF16 | Abliterated / Dolphin variants | 7 models | ~0.6 TB |
| D — Uncensored GGUF | Q8_0 abliterated quants | 6 model sets | ~0.2 TB |
| Overhead (logs, manifests, .tmp scratch) | — | — | ~20 GB |
| **Total** | | **52 entries** | **~6.8 TB** |

---

## 5. Physical Drive Allocation

### Drive Inventory

Labelled capacity ≠ usable capacity. Drive manufacturers use SI (1 TB = 10¹² bytes) while
Linux reports in GiB (2³⁰ bytes), and ext4 reserves ~1% for root. Realistic usable figures:

| Label | Labelled | Raw GiB (lsblk) | Usable after ext4 | Assigned Role |
|-------|----------|-----------------|-------------------|---------------|
| D1 | 6 TB | ~5,400–5,590 GiB | **~5.3 TB** | Raw giants: DeepSeek-V3, DeepSeek-R1, Llama 405B, DeepSeek-Coder-V2 |
| D2 | 3 TB | ~2,700–2,800 GiB | **~2.6 TB** | Raw mid-size: Tier A remainder + Tier B code + **Tier D uncensored raw BF16** |
| D3 | 3 TB | ~2,700–2,800 GiB | **~2.6 TB** | Tier C (all GGUF) + Tier D GGUF |
| D5 | 1 TB | ~850–960 GiB | **~0.87 TB** | Primary archive/ (registry, checksums, manifests), logs |

> **Note:** The 2 TB drive (formerly D4) has been removed from the plan due to hardware issues.
> The ~564 GB of Tier D raw BF16 models have been moved to D2, which has sufficient headroom.
>
> **`.tmp` scratch** (in-progress downloads) was moved from D5 to **D1** (`/mnt/models/d1/.tmp`).
> D1 has ~1.9 TB usable headroom after all planned downloads — far safer than D5's ~0.82 TB total.

### Detailed Allocation

#### D1 — 6 TB (`/mnt/d1`) — Raw Giants

Usable capacity assumed: **~5,300 GB** (conservative, post-format on a 6 TB drive).

| Model | Size | Running Total |
|-------|------|---------------|
| DeepSeek-V3 (Tier A) | ~1,340 GB | 1,340 GB |
| DeepSeek-R1 (Tier A) | ~850 GB | 2,190 GB |
| Llama 3.1 405B Instruct (Tier A) | ~756 GB | 2,946 GB |
| DeepSeek-Coder-V2-Instruct (Tier B) | ~440 GB | 3,386 GB |
| **Free** | | **~1,914 GB** (~1.9 TB — hosts `.tmp` scratch for in-progress downloads) |

#### D2 — 3 TB (`/mnt/d2`) — Raw Mid-Size + Tier D Uncensored

Usable capacity assumed: **~2,600 GB** (conservative, post-format on a 3 TB drive).

| Model | Tier | Size | Running Total |
|-------|------|------|---------------|
| Mistral Large 2 246B | A | ~246 GB | 246 GB |
| Command R+ 104B | A | ~208 GB | 454 GB |
| Llama 3.1 70B Instruct | A | ~140 GB | 594 GB |
| Llama 3.3 70B Instruct | A | ~140 GB | 734 GB |
| DeepSeek-R1-Distill-Llama-70B | A | ~140 GB | 874 GB |
| Qwen2.5 72B Instruct | A | ~144 GB | 1,018 GB |
| DeepSeek-R1-Distill-Qwen-32B | A | ~64 GB | 1,082 GB |
| Qwen2.5 32B Instruct | A | ~64 GB | 1,146 GB |
| Gemma 3 27B IT | A | ~54 GB | 1,200 GB |
| Gemma 3 27B PT | A | ~54 GB | 1,254 GB |
| Gemma 3 12B IT | A | ~24 GB | 1,278 GB |
| Phi-4 14B | A | ~28 GB | 1,306 GB |
| Qwen2.5 7B Instruct | A | ~15 GB | 1,321 GB |
| Mistral 7B v0.3 | A | ~14 GB | 1,335 GB |
| Llama 3.1 8B Instruct | A | ~16 GB | 1,351 GB |
| Qwen2.5-Coder 32B Instruct | B | ~64 GB | 1,415 GB |
| DeepSeek-Coder-V2-Lite Instruct | B | ~30 GB | 1,445 GB |
| Codestral 22B v0.1 | B | ~44 GB | 1,489 GB |
| Devstral Small 2507 | B | ~48 GB | 1,537 GB |
| Llama-3.3-70B-abliterated | D | ~140 GB | 1,677 GB |
| Llama-3.1-70B-lorablated | D | ~140 GB | 1,817 GB |
| DS-R1-Distill-Llama-70B-abliterated | D | ~140 GB | 1,957 GB |
| DS-R1-Distill-Qwen-32B-abliterated | D | ~64 GB | 2,021 GB |
| Mistral-Small-24B-abliterated | D | ~48 GB | 2,069 GB |
| Dolphin3.0-Llama3.1-8B | D | ~16 GB | 2,085 GB |
| NeuralDaredevil-8B-abliterated | D | ~16 GB | 2,101 GB |
| **Free** | | | **~499 GB** (~0.5 TB headroom — based on 2,600 GB usable) |

#### D3 — 3 TB (`/mnt/d3`) — Quantized GGUF (Tier C + D-quants)

Usable capacity assumed: **~2,600 GB** (conservative, post-format on a 3 TB drive).

| Model | Q-level | Size | Running Total |
|-------|---------|------|---------------|
| DeepSeek-R1 671B | Q4_K_M | ~340 GB | 340 GB |
| DeepSeek-V3 671B | Q4_K_M | ~340 GB | 680 GB |
| Llama 3.3 70B | Q8_0 | ~75 GB | 755 GB |
| DeepSeek-R1-Distill-Llama-70B | Q8_0 | ~75 GB | 830 GB |
| Qwen2.5 72B | Q8_0 | ~77 GB | 907 GB |
| Qwen2.5 32B | Q8_0 | ~34 GB | 941 GB |
| DeepSeek-R1-Distill-Qwen-32B | Q8_0 | ~35 GB | 976 GB |
| Qwen2.5-Coder 32B | Q8_0 | ~34 GB | 1,010 GB |
| Gemma 3 27B IT | Q8_0 | ~29 GB | 1,039 GB |
| Phi-4 14B | Q8_0 | ~15 GB | 1,054 GB |
| Codestral 22B | Q8_0 | ~24 GB | 1,078 GB |
| Devstral Small 2507 | Q8_0 | ~24 GB | 1,102 GB |
| DeepSeek-Coder-V2-Lite | Q8_0 | ~17 GB | 1,119 GB |
| Llama 3.1 8B | Q8_0 | ~9 GB | 1,128 GB |
| Qwen2.5 7B | Q8_0 | ~8 GB | 1,136 GB |
| Mistral 7B v0.3 | Q8_0 | ~8 GB | 1,144 GB |
| Llama-3.3-70B-abliterated | Q8_0 | ~75 GB | 1,219 GB |
| DS-R1-Distill-L70B-abliterated | Q8_0 | ~75 GB | 1,294 GB |
| DS-R1-Distill-Q32B-abliterated | Q8_0 | ~35 GB | 1,329 GB |
| NeuralDaredevil-8B-abliterated | Q8_0 | ~9 GB | 1,338 GB |
| Dolphin3.0-Llama3.1-8B | Q8_0 | ~9 GB | 1,347 GB |
| Mistral-Small-24B-abliterated | Q8_0 | ~25 GB | 1,372 GB |
| **Free** | | | **~1,228 GB** (~1.2 TB headroom — based on 2,600 GB usable) |

#### D5 — 1 TB (`/mnt/d5`) — Infrastructure & Scratch

Usable capacity assumed: **~870 GB** (conservative, post-format on a 1 TB drive).

```
/mnt/models/d5/
├── archive/           ← canonical copy; replicated to d1–d3/archive/ after every download
│   ├── registry.yaml
│   ├── checksums/
│   │   └── global_index.jsonl
│   └── manifests/
├── logs/
├── run_state.json
└── STATUS.md
```

> **`.tmp/` scratch has been moved to D1** (`/mnt/models/d1/.tmp`).  
> D1 has ~1.9 TB of headroom post-downloads; D5's ~870 GB total is insufficient  
> to buffer a large model (DeepSeek-R1 = 850 GB) mid-download.  
> After each successful model download, `archive/` is synced from D5 to D1–D3.

### Mount Points Summary

| Drive | Device (placeholder) | Mount Point | Role |
|-------|----------------------|-------------|------|
| D1 | `[DEVICE_D1]` | `/mnt/models/d1` | Raw giants + `.tmp` scratch |
| D2 | `[DEVICE_D2]` | `/mnt/models/d2` | Raw mid-size + Tier D uncensored raw |
| D3 | `[DEVICE_D3]` | `/mnt/models/d3` | GGUF quants |
| D5 | `[DEVICE_D5]` | `/mnt/models/d5` | Primary archive/ + logs + run_state |

All mounts: ext4, `noatime,nodiratime,defaults`, `large_file` support enabled (default `mkfs.ext4`).

### Headroom Summary

Using **conservative usable figures** (actual formatted space on real drives is typically
5–8% below labelled capacity):

| Drive | Used | Labelled | Usable (realistic) | Free |
|-------|------|----------|--------------------|------|
| D1 | ~3.4 TB | 6 TB | **~5.3 TB** | **~1.9 TB** (hosts `.tmp`) |
| D2 | ~2.1 TB | 3 TB | **~2.6 TB** | **~0.5 TB** |
| D3 | ~1.4 TB | 3 TB | **~2.6 TB** | **~1.2 TB** |
| D5 | ~0.05 TB | 1 TB | **~0.87 TB** | **~0.82 TB** |
| **Total** | **~6.9 TB** | **13 TB** | **~11.4 TB** | **~4.4 TB** |

> D4 (2 TB Seagate) removed from plan due to hardware issues. Total array capacity reduced from 15 TB to 13 TB.

The ~4.4 TB of free space (conservative) is sufficient to add:
- Abliterated 671B DeepSeek models on D1 (~850 GB each, fits in D1 headroom)
- Future major model releases (D3 has ~1.2 TB headroom)

> **D2 is the tightest drive** (~0.5 TB headroom). If a gated model is larger than
> expected, reduce the Tier D allocation or offload some mid-size models to D3.

---

## 5. Gated Model Access — Token Setup

The following models require accepting a licence on the HF model page **and** authenticating with an `HF_TOKEN` env variable:

| Model family | HF model page to visit | Licence to accept |
|---|---|---|
| Llama 3.x | `meta-llama/Llama-3.1-405B-Instruct` (and others) | Meta Llama 3 Community |
| Gemma 3 | `google/gemma-3-27b-it` | Google Gemma Terms of Use |
| Mistral Large 2 | `mistralai/Mistral-Large-Instruct-2407` | Mistral Research Licence |
| Codestral | `mistralai/Codestral-22B-v0.1` | Mistral AI Non-Production Licence |

**Steps to get access (one-time setup):**
1. Create a Hugging Face account at [huggingface.co](https://huggingface.co).
2. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) → create a **read** token.
3. Visit each gated model page above and click "Agree and access repository".  
   Llama and Gemma approvals are typically automatic (instant). Mistral models may take minutes.
4. Store the token: `export HF_TOKEN=hf_...` (the archiver will read this env variable).

No separate Mistral account is needed — HF is the canonical distribution channel for Mistral open weights.

---

## 6. Storage Layout

Five drives, unified namespace under `/mnt/models/`. Each drive mounted at its own subdirectory; the registry records which drive each model resides on.

```
/mnt/models/
├── d1/                                # 6 TB — raw giants (Tier A large + Tier B large)
│   ├── raw/
│   │   └── <org>/<model-name>/<commit-sha>/
│   │       ├── manifest.json
│   │       ├── model-*.safetensors
│   │       └── model-*.safetensors.sha256
│   └── archive/                       # replicated on every drive (tiny)
│       ├── registry.yaml
│       ├── checksums/
│       │   └── global_index.jsonl
│       └── manifests/
│
├── d2/                                # 3 TB — raw mid-size (Tier A remainder + Tier B small + Tier D uncensored)
│   ├── raw/
│   │   └── <org>/<model-name>/<commit-sha>/  (same structure)
│   └── archive/                       # replicated checksum/registry copy
│       ├── registry.yaml
│       ├── checksums/
│       │   └── global_index.jsonl
│       └── manifests/
│
├── d3/                                # 3 TB — GGUF quantized (Tier C + D-quants)
│   ├── quantized/
│   │   └── <org>/<model-name>/<commit-sha>/
│   │       ├── manifest.json
│   │       ├── <model>.Q4_K_M.gguf + .sha256
│   │       └── <model>.Q8_0.gguf   + .sha256
│   └── archive/                       # replicated checksum/registry copy
│       ├── registry.yaml
│       ├── checksums/
│       │   └── global_index.jsonl
│       └── manifests/
│
└── d5/                                # 1 TB — infra, scratch, primary archive
    ├── archive/                       # canonical (primary) copy
    │   ├── registry.yaml
    │   ├── checksums/
    │   │   └── global_index.jsonl
    │   └── manifests/
    ├── logs/
    │   └── YYYY-MM-DD_download.log
    └── .tmp/                          # all in-progress downloads land here first
        └── <org>/<model-name>/<commit-sha>/
```

**Design decisions:**
- `archive/` is replicated to every drive after each successful model download. It contains only `registry.yaml`, `checksums/global_index.jsonl`, and per-model `manifest.json` files — total size is well under 1 GB even for the full archive. Any single surviving drive gives you the complete verification record.
- D5 holds the canonical (primary) `archive/`; all other drives hold replicas. The archiver writes to D5 first, then syncs to D1–D4 as a post-download step.
- All partial/in-progress downloads land on D5 (`.tmp/`), then are atomically moved to the target drive on successful verification. No partial files ever exist on D1–D4.
- Directory key is the HF commit SHA — bit-reproducible, never a floating `main`.
- Each drive's top-level content directory (`raw/`, `quantized/`, `uncensored/`) is self-contained — rsync or backup of a single tier touches only one drive.
- Symlink `<drive>/raw/<org>/<model>/latest` → `<commit-sha>` for convenience; never used for verification.
- The registry `drive` field records which physical drive each model lives on, so the archiver always knows where to look without scanning.

---

## 7. Download Subsystem

### 7.1 Tool Stack

| Layer | Library / Tool | Rationale |
|-------|---------------|-----------|
| HF metadata | `huggingface_hub` ≥ 0.23 | Resolves commit SHAs, file lists, blob LFS URLs, etags — the authoritative HF API client |
| **HTTP transfers (primary)** | **`aria2c` via `aria2p`** | Battle-tested multi-connection downloader; native resume via `.aria2` control files; per-file parallel chunks; handles HTTP 429 / Retry-After; JSON-RPC interface for Python control |
| HTTP transfers (fast-path) | `hf_transfer` ≥ 0.1.4 (opt-in) | Rust-backed; can exceed 500 MB/s; **does not support resume** — only used when `--fast` flag is set and connection is known stable |
| HTTP transfers (fallback) | `httpx` async streaming | Pure-Python fallback if aria2c not installed; handles Range requests for manual resume |
| Concurrency | `asyncio` + `ThreadPoolExecutor` | Per-drive download workers; bandwidth probe thread |
| Checksum | `hashlib` SHA-256 | Stdlib; no extra dep |
| Progress / CLI | `rich` Live layout | Multi-panel live display in TTY mode |
| Status page | Plain string formatting | Written to `STATUS.md` in execution directory |
| Config | `PyYAML` | Registry and manifest format |
| Drive monitoring | `psutil` | Disk free space; per-drive throughput sampling |

#### Why aria2c + aria2p as the primary transfer engine

`aria2c` is a standalone C++ download daemon controlled over JSON-RPC. `aria2p` is its Python client library. Together they give us:

- **True resumability**: aria2c writes a `.aria2` control file alongside each partial download that survives process restarts, reboots, and crashes. Re-running picks up exactly where it stopped at the byte level — no re-download of already-fetched chunks.
- **Multi-connection per file**: configurable connections per file (default 8) — splits a single 5 GB shard across 8 parallel HTTP Range requests, saturating the link from one file alone.
- **Built-in retry + rate-limit handling**: respects `Retry-After`, configurable retry count, backoff — no custom retry logic needed in our code.
- **Per-file speed limiting**: useful when running parallel drive workers so no single file monopolises bandwidth.
- **Battle-tested at scale**: aria2 is a 15-year-old project specifically built for exactly this problem (large unattended parallel downloads).

#### Why NOT hf_transfer as primary

`hf_transfer` (Rust, from HuggingFace) is fast but has a critical limitation for our use case: **it does not support resuming interrupted downloads** ([confirmed issue](https://github.com/huggingface/hf_transfer/issues/30)). For a 1.3 TB model downloaded over many hours, a single network hiccup or power event without resume means restarting from zero. It remains available as an opt-in fast-path for stable high-bandwidth environments.

#### Integration architecture

```
archiver (Python)
    │
    ├── huggingface_hub      →  resolve file list, LFS URLs, commit SHA, etags
    │
    ├── aria2p (JSON-RPC)    →  submit download tasks to aria2c daemon
    │       │
    │       └── aria2c       →  actual HTTP transfer engine
    │             ├── .aria2 control files (resume state, per file)
    │             └── downloads land in d5/.tmp/ → verified → moved to target drive
    │
    └── hashlib              →  SHA-256 verify after move
```

aria2c runs as a background daemon (started by the archiver on launch, stopped on exit). Each file is submitted as a separate aria2 task with its LFS URL and target path. The archiver polls task status via `aria2p` and drives the state machine.

### 7.2 Parallel Download Strategy

Downloads across **different drives** run concurrently. Downloads targeting the **same drive** are serialised (one active download per drive at a time) to avoid thrashing the drive's sequential throughput.

```
Drive slots:   D1 [ worker ]   D2 [ worker ]   D3 [ worker ]   D4 [ worker ]
                    │                │                │                │
               model A shard   model B shard   model C GGUF    model D raw
               (sequential     (sequential     (sequential     (sequential
                within D1)      within D2)      within D3)      within D4)
```

**Bandwidth gating:** before starting a second model on a drive, the archiver measures the current aggregate throughput (sampled every 10 s). A new parallel slot on a different drive is opened only if current total throughput is below `max_bandwidth_mbps × 0.85` (configurable; default: unlimited — no artificial cap). This prevents parallel downloads from each getting a poor share of a narrow uplink.

**Concurrency limits (defaults, all configurable):**
- `max_drive_workers`: 1 per drive (serialised within a drive)
- `max_parallel_drives`: 4 (all 4 content drives active simultaneously)
- `max_chunks_per_file`: 8 (within a single file via `hf_transfer`)
- `bandwidth_headroom_pct`: 85 — only start new drive slot if utilisation < 85%

### 7.3 Download Algorithm (per model version)

The archiver runs fully unattended. There is no interactive prompt at any point after launch.

```
1. Resolve commit SHA from registry (must be pinned; refuse to float on `main`)
2. Query HF API for file list + blob SHAs + sizes for that commit
3. For each file:
   a. <file>.sha256 exists and matches → skip (idempotent), log SKIP
   b. Partial file in .tmp/ exists → resume with HTTP Range, log RESUME
   c. Otherwise → fresh download to .tmp/, log START
   d. On completion → SHA-256 verify:
      - PASS → atomic move to final path → write .sha256 sidecar → log OK
      - FAIL → delete partial, log ERROR, schedule retry
4. All files complete → write manifest.json → append to global_index.jsonl
5. Sync archive/ from D5 to all other drives
6. Atomically update `latest` symlink
7. Log model COMPLETE with total bytes, elapsed time, file count
8. Refresh STATUS.md and console display
```

### 7.4 Retry and Error Policy (unattended)

Per-file retry behaviour:
- **Checksum mismatch or network error**: retry up to **5×** with exponential backoff (30 s, 60 s, 120 s, 300 s, 600 s).
- **HTTP 429 / rate-limit**: honour `Retry-After` header; back off at least 5 minutes.
- **HTTP 401 / 403**: do not retry — log `AUTH_FAIL`, skip model, continue with next. (Token issue requires human intervention.)
- **Disk full**: log `DISK_FULL`, abort current model cleanly (partial files stay in `.tmp/` for resume), skip remaining models assigned to that drive, continue downloads on other drives.
- **5 consecutive failures on same file**: mark model as `FAILED` in `run_state.json`, skip, continue. Never hang indefinitely.

After all models attempted, the archiver writes a **run summary** to `d5/logs/` and exits with a non-zero code if any model is in `FAILED` state.

### 7.5 Logging (unattended)

```
d5/logs/
├── YYYY-MM-DD_HH-MM_download.log    # human-readable run log (one per invocation)
├── YYYY-MM-DD_HH-MM_download.jsonl  # machine-readable structured JSONL (same events)
└── run_state.json                   # persistent cross-run state (per-model status)
```

Log levels: `DEBUG`, `INFO`, `WARN`, `ERROR`. Default: `INFO`.  
Each log line: timestamp · model ID · file name · event type · bytes transferred · elapsed · drive · worker ID.

`run_state.json` persists across invocations. A re-run after failure skips already-complete models and resumes in-progress ones at their byte offset — no re-checking needed.

### 7.6 Console Status Display (TTY mode)

When running in a TTY, `rich` renders a **live multi-panel layout** refreshed every 2 seconds:

```
┌─ Archive Progress ──────────────────────────────────────────────────────────┐
│  Overall  [████████████░░░░░░░░░░]  47%   3.2 TB / 6.8 TB   ETA: 14h 22m  │
└─────────────────────────────────────────────────────────────────────────────┘
┌─ Active Downloads ──────────────────────────────────────────────────────────┐
│  D1  DeepSeek-V3          shard 087/163  [████████░░░░]  312 MB/s  ↓ 67 GB │
│  D2  Llama-3.1-70B        shard 012/030  [██████░░░░░░]  198 MB/s  ↓ 28 GB │
│  D3  Qwen2.5-72B Q8_0     1/1 blob       [███░░░░░░░░░]   95 MB/s  ↓ 19 GB │
│  D4  DS-R1-Distill-70B-abl shard 004/030 [█████░░░░░░░]  201 MB/s  ↓ 22 GB │
└─────────────────────────────────────────────────────────────────────────────┘
┌─ Drive Usage ────────────────────────────────────┐ ┌─ Queue (next 5) ──────┐
│  D1  [████████████░░░░░░░░]  3.4/6.0 TB          │ │  1. DS-R1 (D1)        │
│  D2  [████████░░░░░░░░░░░░]  1.5/3.0 TB          │ │  2. Llama-405B (D1)   │
│  D3  [████░░░░░░░░░░░░░░░░]  0.7/3.0 TB          │ │  3. Qwen2.5-32B (D2)  │
│  D4  [███░░░░░░░░░░░░░░░░░]  0.6/2.0 TB          │ │  4. Gemma3-27B (D2)   │
│  D5  [░░░░░░░░░░░░░░░░░░░░]  0.05/1.0 TB         │ │  5. Codestral (D2)    │
└──────────────────────────────────────────────────┘ └───────────────────────┘
┌─ Completed ─────────────────────────────────────────────────────────────────┐
│  ✓ DeepSeek-R1       D1   850 GB   verified   2026-03-04 02:14              │
│  ✓ DeepSeek-V3-GGUF  D3   340 GB   verified   2026-03-04 04:51              │
└─────────────────────────────────────────────────────────────────────────────┘
```

When not in a TTY (nohup / systemd), the live display is suppressed; all state goes to logs and `STATUS.md` only.

### 7.7 STATUS.md — Live Status Page

`STATUS.md` is written to the **execution directory** (wherever `archiver` is invoked) and updated after every file completion event and on a 60-second heartbeat timer. It is a self-contained human-readable snapshot of the entire archive state — readable with any Markdown viewer or `cat`.

```markdown
# Archive Status
_Last updated: 2026-03-04 06:42:11 — auto-refreshed every ~60s_

## Overall Progress
- **Total:** 6.8 TB across 52 models
- **Downloaded:** 3.2 TB (47%) — 18 models complete, 4 in progress, 30 pending
- **ETA:** ~14h 22m at current throughput

## Active Downloads
| Drive | Model | Progress | Speed | ETA |
|-------|-------|----------|-------|-----|
| D1 | DeepSeek-V3 | 67 GB / 1,340 GB (5%) | 312 MB/s | 72m |
| D2 | Llama-3.1-70B | 28 GB / 140 GB (20%) | 198 MB/s | 9m |
| D3 | Qwen2.5-72B Q8_0 | 19 GB / 77 GB (25%) | 95 MB/s | 10m |
| D4 | DS-R1-Distill-70B-abl | 22 GB / 140 GB (16%) | 201 MB/s | 10m |

## Completed Models (18)
| Model | Tier | Drive | Size | Verified | Time |
|-------|------|-------|------|----------|------|
| DeepSeek-R1 | A | D1 | 850 GB | ✓ | 2026-03-04 02:14 |
| DeepSeek-V3 Q4_K_M | C | D3 | 340 GB | ✓ | 2026-03-04 04:51 |
...

## Failed / Skipped
| Model | Reason | Retries |
|-------|--------|---------|
| — | — | — |

## Drive Usage
| Drive | Used | Capacity | Free |
|-------|------|----------|------|
| D1 | 3.4 TB | 6.0 TB | 2.3 TB |
...
```

The file is written atomically (write to `.STATUS.md.tmp`, then rename) so it is never half-written.

### 7.8 GGUF-specific download

GGUF files are single large blobs (not sharded). The same algorithm applies.  
For Ollama-sourced models, `ollama pull <name>` is used and the blobs are extracted from  
`~/.ollama/models/blobs/` and copied to the archive with checksums captured at copy time.

---

## 8. Verification

### 8.1 Automatic (post-download)

Each file: SHA-256 computed → compared to `.sha256` sidecar and HF blob etag.  
Mismatch → file deleted, error logged, retry up to 3×.

### 8.2 Manual (on-demand)

```bash
archiver verify <model-id>            # verify all files for one model
archiver verify --all                 # full archive scan
archiver verify --tier raw            # only Tier A+B
archiver verify --tier quantized      # only Tier C
archiver verify --manifest <path>     # against a specific manifest.json
```

Output: per-file PASS / FAIL table + aggregate summary with total bytes verified.

### 8.3 Checksum Database (`checksums/global_index.jsonl`)

Append-only log; never deleted or rewritten. Each line:

```json
{
  "timestamp": "2026-03-04T12:00:00Z",
  "tier": "raw",
  "hf_repo": "meta-llama/Llama-3.1-405B-Instruct",
  "commit_sha": "abc123...",
  "files": [
    {"path": "model-00001-of-00191.safetensors", "sha256": "...", "size_bytes": 4815928320}
  ],
  "total_size_bytes": 812345678901
}
```

This log is portable and sufficient to verify any future re-download or off-site copy, independent of the live archive.

---

## 9. Registry Format (`registry.yaml`)

```yaml
# priority 1 = token-free, download immediately
# priority 2 = gated (requires HF_TOKEN), download after all priority-1 complete

models:
  - id: deepseek-ai/DeepSeek-V3
    hf_repo: deepseek-ai/DeepSeek-V3
    tier: A
    drive: d1
    commit_sha: null          # populated after first successful download; then frozen
    priority: 1               # token-free — starts immediately
    licence: MIT
    requires_auth: false

  - id: bartowski/Qwen2.5-Coder-32B-Instruct-GGUF
    hf_repo: bartowski/Qwen2.5-Coder-32B-Instruct-GGUF
    tier: C
    drive: d3
    commit_sha: null
    quant_levels: [Q4_K_M, Q8_0]
    priority: 1               # token-free — starts immediately
    licence: Apache-2.0
    requires_auth: false

  - id: huihui-ai/Llama-3.3-70B-Instruct-abliterated
    hf_repo: huihui-ai/Llama-3.3-70B-Instruct-abliterated
    tier: D
    drive: d4
    parent_model: meta-llama/Llama-3.3-70B-Instruct
    commit_sha: null
    priority: 1               # token-free — starts immediately
    licence: llama3.3
    requires_auth: false
    method: abliteration

  - id: meta-llama/Llama-3.1-405B-Instruct
    hf_repo: meta-llama/Llama-3.1-405B-Instruct
    tier: A
    drive: d1
    commit_sha: null
    priority: 2               # gated — deferred until HF_TOKEN confirmed present
    licence: llama3.1
    requires_auth: true
    notes: "Accept licence at huggingface.co/meta-llama/Llama-3.1-405B-Instruct"

  - id: mistralai/Codestral-22B-v0.1
    hf_repo: mistralai/Codestral-22B-v0.1
    tier: B
    drive: d2
    commit_sha: null
    priority: 2               # gated — deferred until HF_TOKEN confirmed present
    licence: Mistral-MNPL
    requires_auth: true
    notes: "Accept licence at huggingface.co/mistralai/Codestral-22B-v0.1"
```

Adding a new model version = new entry with new commit SHA. Old entries are never modified.

---

## 10. CLI Interface

```
archiver download <model-id|--tier A|B|C|D|--all>
                  [--dry-run]              # print what would be downloaded, no I/O
                  [--max-parallel-drives N]  # override default (4)
                  [--bandwidth-cap MBPS]   # hard cap total outbound bandwidth
                  [--priority-first]       # download by priority field order

archiver verify   <model-id|--all|--tier X|--drive dN> [--manifest PATH]

archiver status   [--drive X]       # console table: per-model status / size / drive / ETA

archiver list     [--tier X]        # registry dump with sizes, commit SHAs, licences, drive

archiver pin      <model-id> <commit-sha>   # manually freeze a commit SHA in registry

archiver tokens   check             # test HF_TOKEN against all gated model pages

archiver drives   status            # used/free/inodes per drive

archiver report                     # regenerate STATUS.md from run_state.json (no download)
```

---

## 11. Dependencies

### 11.1 Python packages

```
# Core — required
huggingface_hub >= 0.23       # HF API: file lists, LFS URLs, commit SHAs, etags
aria2p >= 0.12.1              # Python JSON-RPC client for aria2c daemon
httpx >= 0.27                 # async HTTP fallback (Range requests) if aria2c absent
click >= 8.1                  # CLI framework
rich >= 13.0                  # live TTY display; auto-suppressed when not in TTY
PyYAML >= 6.0                 # registry.yaml + manifest parsing
python-json-logger >= 2.0     # structured JSONL log output
psutil >= 5.9                 # disk free space; per-drive throughput sampling

# Optional — install for maximum speed on stable high-bandwidth connections
hf_transfer >= 0.1.4          # Rust-backed fast-path (no resume); enable with --fast flag
```

Python >= 3.11.

### 11.2 System dependency

`aria2c` must be installed on the host system. It is available in all major Linux package managers and is the only non-Python system dependency:

```bash
# Debian / Ubuntu
sudo apt install aria2

# Arch
sudo pacman -S aria2

# Fedora / RHEL
sudo dnf install aria2
```

The archiver checks for `aria2c` in `$PATH` at startup (part of pre-flight checks, §12.1) and exits with a clear error if not found.

### 11.3 TTY detection

`sys.stdout.isatty()` is checked at startup. When not in a TTY (nohup, systemd, screen with no attachment, cron), `rich` live display is suppressed and all output goes to log files and `STATUS.md` only.

---

## 12. Additional Features

Features beyond the core download/verify loop that improve reliability and usability for a long-running unattended archive job.

### 12.1 Pre-flight Checks (run before any download starts)

Before the first byte is fetched, the archiver validates:
1. **`aria2c` present** — check `aria2c --version` in `$PATH`; exit with install instructions if missing.
2. **HF token** — if `HF_TOKEN` is set, test it against all priority-2 (gated) models; report pass/fail per model. If `HF_TOKEN` is **not set**, log a warning listing the gated models that will be skipped, then proceed — priority-1 downloads are not blocked.
3. **Disk space** — confirm each drive has enough free space for all models assigned to it. Warn if < 10% headroom; abort if < 5%.
4. **Drive mount** — verify all 5 mount points are present and writable.
5. **Network reachability** — HEAD request to `huggingface.co`; abort if unreachable.
6. **Registry integrity** — validate YAML schema; catch typos before the run starts.

Critical failures (1, 4, 5, 6) abort the run entirely. Token absence (2) and disk headroom warnings (3) are non-fatal for priority-1 models.

### 12.2 Bandwidth Sampling and Adaptive Parallelism

A background thread samples aggregate download throughput every 10 seconds. The scheduler uses this to decide whether to open an additional parallel drive slot:

- If `current_throughput < bandwidth_headroom_pct × observed_peak` → open next drive slot.
- If a drive slot is idle (model complete, nothing queued for that drive) → close slot.
- Throughput history (last 60 samples) is written to `STATUS.md` as a sparkline.

This means on a fast connection all 4 drives download simultaneously from the start. On a slow connection they naturally serialise.

### 12.3 ETA Estimation

ETA shown in both the console display and `STATUS.md` is computed as:

```
remaining_bytes = sum of (total_size - downloaded) for all pending + in-progress models
eta_seconds     = remaining_bytes / ewma_throughput_bytes_per_sec
```

EWMA (exponentially weighted moving average) with α = 0.1 over 10-second samples — smooths out burst/stall noise without ignoring recent speed changes.

### 12.4 Completion Notification (optional)

If `ARCHIVER_NOTIFY_URL` env var is set to a webhook URL (e.g. ntfy.sh, Slack incoming webhook, Gotify), the archiver POSTs a JSON summary on:
- Each model completing successfully.
- Any model entering `FAILED` state.
- Full run completion.

No notification dependency is installed by default — the feature is a no-op if the env var is unset.

### 12.5 Download Ordering / Priority Queue

The `priority` field in the registry encodes both urgency and token dependency:

| Priority | Meaning | Models |
|----------|---------|--------|
| **1** | Token-free — start immediately | All DeepSeek, Qwen, Mistral 7B, Phi-4, Command R+, all GGUF, all uncensored (Tiers C + D), Devstral, DeepSeek-Coder |
| **2** | Gated — requires HF token | All Llama, Gemma, Mistral Large 2, Codestral |

Default download order within the queue:
1. All priority-1 models first (no token needed — begin immediately).
2. Within priority-1: larger models first on D1 (to start the longest jobs early), smaller models elsewhere.
3. Priority-2 models start only after all priority-1 models are complete **or** once `HF_TOKEN` is confirmed present via `archiver tokens check`.
4. Within same drive: pack sequentially to maximise drive throughput.

This means a fresh run with no token will download the entire ~4 TB of open-weight models unattended, and pause cleanly before the gated models. Once the token is obtained, re-running resumes from where it stopped.

`--priority-first` flag overrides size-based reordering within a priority tier and strictly follows registry order.

### 12.6 Disk Space Guard

After each shard is moved from `.tmp/` to its target drive, the archiver checks free space on that drive. If free space drops below `min_free_gb` (default: 50 GB), it:
1. Pauses downloads to that drive.
2. Logs `DISK_WARNING`.
3. Updates `STATUS.md` with a warning banner.
4. Resumes only after operator clears space (re-run is safe — idempotent).

### 12.7 `archiver report` — Offline Status Regeneration

Regenerates `STATUS.md` from `run_state.json` and the registry without starting any downloads. Useful to check status after the terminal was closed, or to share the status file after the fact:

```bash
archiver report                  # regenerate STATUS.md in current directory
archiver report --output ~/status.md
```

### 12.8 `screen` / `tmux` Recommendation

For long unattended runs, the recommended invocation pattern is:

```bash
screen -S archiver
archiver download --all
# detach with Ctrl-A D
# reattach any time:  screen -r archiver
```

The live display persists in the screen session. `STATUS.md` is always available in the execution directory regardless of whether the session is attached.

---

## 13. Out-of-Scope / Future Work

- Automatic new-release detection and download triggering.
- IPFS / BitTorrent distribution.
- Encryption at rest.
- Multi-machine sync / RAID.
- Format conversion (GGUF export from raw BF16, ONNX).
- Web UI / dashboard (STATUS.md is the lightweight substitute).

---

## 14. Open Questions

1. **Device identifiers** — confirm the `/dev/sdX` or UUID for each of the 5 drives so the registry can be fully populated.
2. **Tier C 671B GGUF** — DeepSeek-V3 and R1 at Q4_K_M are each ~340 GB on D3; include both in first run or defer one?
3. **Codestral MNPL** — non-production licence; acceptable for archival/research use?
4. **Command R+** — CC-BY-NC prohibits commercial use; include or drop?
5. **Ollama vs HF for Tier C** — prefer HF-hosted GGUFs (bartowski/unsloth/mistralai) for consistency, or also support native `ollama pull`?
6. **DeepSeek-Coder-V2-Instruct GGUF** (236B) — Q4_K_M ~120 GB; add to D3 Tier C or raw-only?
7. **Abliterated 671B models** — `huihui-ai/DeepSeek-R1-671b-abliterated` and `DeepSeek-V3-abliterated` each ~850–1,340 GB raw; defer to D1 expansion or skip?

> **Token acquisition checklist** (one-time, can be done while priority-1 downloads run):
> 1. Create HF account → [huggingface.co/join](https://huggingface.co/join)
> 2. Create read token → [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
> 3. Accept Meta Llama licence → [huggingface.co/meta-llama/Llama-3.1-405B-Instruct](https://huggingface.co/meta-llama/Llama-3.1-405B-Instruct) (covers all Llama 3.x)
> 4. Accept Google Gemma ToU → [huggingface.co/google/gemma-3-27b-it](https://huggingface.co/google/gemma-3-27b-it) (covers all Gemma 3)
> 5. Accept Mistral Research licence → [huggingface.co/mistralai/Mistral-Large-Instruct-2407](https://huggingface.co/mistralai/Mistral-Large-Instruct-2407)
> 6. Accept Mistral MNPL → [huggingface.co/mistralai/Codestral-22B-v0.1](https://huggingface.co/mistralai/Codestral-22B-v0.1)
> 7. Set token: `export HF_TOKEN=hf_...` then run `archiver tokens check`
