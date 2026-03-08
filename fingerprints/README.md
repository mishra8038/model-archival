# model-fingerprints

Lightweight SHA-256 fingerprint harvester for open-source LLM releases on HuggingFace.

**No weights are downloaded.** Only the tiny LFS pointer files (~150 bytes each) are
fetched. These contain the authoritative SHA-256 hash that the model author published
for every weight shard in every version of the model.

The harvested fingerprints let you later verify any copy of a model — from any source —
against the original HuggingFace checksums, even if the model has since been removed.

---

## Why this exists

- Models get deleted, modified, or restricted without notice.
- Checksums published by authors at release time are the ground truth.
- Recording them costs almost nothing (a few KB per model, a few seconds to crawl).
- If a model disappears and re-appears from a third-party mirror, you can verify
  the mirror's copy is bit-for-bit identical to what the author published.

---

## What gets stored

For every model in the registry, for every commit in its history:

```
model-checksums/
├── index.jsonl                             # global append-only index
├── deepseek-ai__DeepSeek-V3/
│   ├── fingerprint.json                    # full structured data
│   ├── fingerprint.md                      # human-readable summary
│   └── commits/
│       ├── <commit_sha>.json               # per-commit file list + hashes
│       └── ...
├── meta-llama__Llama-3.3-70B-Instruct/
│   └── ...
└── ...
```

Each `fingerprint.json` contains:
- Model identity (HF repo, URL, family, tier, licence)
- Snapshot metadata (crawl date, number of commits captured)
- For every commit: SHA-256 + size of every weight file (`.safetensors`, `.gguf`, `.bin`)

---

## Registry

`config/registry.yaml` contains ~90 models across all major families:

| Family | Notable models |
|--------|---------------|
| DeepSeek | V3, R1, R1-Zero, all distills, Coder V2 |
| Meta Llama | Llama 3.3/3.1/3.0/2 (8B → 405B) |
| Qwen | Qwen2.5 (1.5B → 72B), Coder, QwQ-32B |
| Mistral | Mistral 7B (all versions), Mixtral 8x7B/8x22B, Mistral-Large, Codestral, Devstral |
| Google Gemma | Gemma 3/2/1 (1B → 27B) |
| Microsoft Phi | phi-4, phi-4-mini, Phi-3.5, phi-2 |
| Cohere | Command R+ (all releases), Aya |
| Falcon | Falcon 180B, Falcon 3, Falcon 40B |
| BLOOM | bloom-176B, bloomz |
| OLMo | OLMo-2 13B/7B (fully open training data) |
| Uncensored | Dolphin, WizardLM, huihui-ai abliterations, mlabonne variants |
| GGUF | bartowski, unsloth quantizations of all the above |

Tiers:
- **A** — Major flagship models (raw BF16/FP16 weights)
- **B** — Code-specialist models
- **C** — Quantized GGUF variants
- **D** — Uncensored / abliterated variants

Importance levels drive retry behaviour and filtering:
- **critical** — Must not be skipped; retry aggressively
- **high** — Important; retry on failure
- **medium** — Nice to have; skip on persistent failure

---

## Setup

```bash
cd /home/x/dev/model-archival/fingerprints
uv sync
source .venv/bin/activate
```

Set your HuggingFace token (needed for gated models: Llama, Gemma, Mistral-Large, etc.):

```bash
# Either:
export HF_TOKEN=hf_...
# Or store it in ~/.hf_token (chmod 600 ~/.hf_token)
```

---

## Usage

```bash
# Crawl everything (resumable — safe to interrupt and re-run)
bash run.sh

# Crawl to a specific drive
bash run.sh --output /mnt/models/d1

# Only critical flagship models
bash run.sh --importance critical --tier A

# Only one family
bash run.sh --family deepseek

# Dry-run: show what would be crawled
bash run.sh --dry-run

# Re-crawl repos already marked complete (e.g. after adding new commits upstream)
bash run.sh --force

# Check progress
fingerprints status

# Inspect a specific model's fingerprint
fingerprints show deepseek-ai/DeepSeek-V3

# Verify a local file against stored fingerprints
fingerprints verify deepseek-ai/DeepSeek-V3 /mnt/models/d1/deepseek-ai__DeepSeek-V3/model-00001-of-00163.safetensors
```

---

## Output storage

By default, output goes to `/mnt/models/d5/model-checksums/` (the metadata drive).
Because the output is tiny (a few KB per model, ~10 MB for the full registry), it
fits comfortably on D5 alongside `run_state.json`, logs, and `STATUS.md`.

You can mirror the output directory to any drive or cloud storage — it's just JSON and
Markdown files, entirely self-contained and human-readable.

---

## Relation to model-archival

`model-archival` downloads full weight files and verifies them at download time.
`model-fingerprints` is a complementary lightweight tool:

| | model-archival | model-fingerprints |
|---|---|---|
| Downloads weights | Yes | No |
| Captures checksums | Yes (for downloaded models) | Yes (for all registry models, all versions) |
| Storage per model | 10 GB – 750 GB | ~50 KB |
| Run time per model | Hours – days | Seconds |
| Covers older versions | No (latest only) | Yes (full commit history) |
| Requires disk space | Multi-TB | Negligible |

---

## How to verify a file manually

```bash
# Get the expected hash from the fingerprint:
jq -r '.latest_commit.files[] | select(.filename | endswith("model-00001-of-00163.safetensors")) | .sha256' \
  /mnt/models/d5/model-checksums/deepseek-ai__DeepSeek-V3/fingerprint.json

# Verify:
sha256sum /path/to/model-00001-of-00163.safetensors
```

Or use the built-in verify command:

```bash
fingerprints verify deepseek-ai/DeepSeek-V3 /path/to/model-00001-of-00163.safetensors
```
