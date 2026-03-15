# Model sources beyond Hugging Face

## Summary

**Abliterated and specialist models:** There are **no** Kaggle-hosted abliterated or uncensored LLM weights that are missing from Hugging Face. Kaggle does not host a separate catalogue of abliterated/specialist models.

**Kaggle’s role:** Kaggle hosts (1) **official publisher models** (Google Gemma 1/2/3, Meta Llama 2 / 3.2, QwenLM Qwen2.5-Coder on the Models hub) and (2) **links to Hugging Face** (`refs/hf-model/...`) — i.e. discovery/redirect, not separate copies. Community datasets (e.g. fine-tuned Llama 3 8B, GPT-2 weights) are occasional mirrors or fine-tunes, not abliterated variants.

**Where to get abliterated / specialist models:** Hugging Face is the primary and effectively only reliable source for:

- Abliterated variants (huihui-ai, failspy, tensorblock, mlabonne, etc.)
- Specialist (coder, math, uncensored-merge) models

---

## Kaggle (checked 2025-03)

| Content type        | On Kaggle? | Notes |
|---------------------|------------|--------|
| Abliterated models  | No         | Search for "abliterated" / "uncensored llm" returns no dedicated datasets. |
| Specialist (Coder)  | Partial    | QwenLM Qwen2.5-Coder on Models hub; some datasets (e.g. Qwen2.5-Coder-1.5B-Base) mirror HF. |
| Official bases      | Yes        | Meta Llama 2/3.2, Google Gemma 1/2/3 — same as or aligned with HF. |
| HF-linked refs      | Yes        | e.g. Qwen/Qwen3.5-4B, Qwen3.5-9B — link to HF, not Kaggle-hosted weights. |

So: **no** abliterated or specialist models found on Kaggle that we couldn’t find on Hugging Face.

---

## Other reliable sources (recap)

- **Model Scope (modelscope.cn)** — Primary alternative for **Qwen** (official Alibaba); good backup if HF is down or rate-limited.
- **Hugging Face** — Primary for almost all open LLMs, including abliterated and specialist.
- **Kaggle** — Useful for official Gemma/Llama and HF discovery; not an extra source for abliterated/specialist weights.

---

## Registry coverage (abliterated / Tier D)

Our registry already pulls abliterated and specialist models from HF, e.g.:

- huihui-ai: Llama-3.3-70B-Instruct-abliterated, Qwen2.5-72B-Instruct-abliterated, Mistral-Small-24B-Instruct-2501-abliterated, DeepSeek-R1-Distill-* abliterated
- failspy: Meta-Llama-3-70B-Instruct-abliterated-v3.5
- tensorblock: GGUF abliterated quants (Llama 3.3 70B, DeepSeek-R1-Distill, Mistral-Small-24B)
- mlabonne: NeuralDaredevil-8B-abliterated, Llama-3.1-70B-Instruct-lorablated
- cognitivecomputations: Dolphin (uncensored)
- CombinHorizon: zetasepic-abliteratedV2-Qwen2.5-32B merge
- rombodawg, FINGU-AI: uncensored merges

If a model exists only on Kaggle (e.g. a future community upload), it would need a custom download path; the current archiver is HF-centric.
