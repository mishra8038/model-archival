# Storage layout and capacity

**Purpose:** Where artifacts are stored, how much space each drive has, and how to check you have enough room for the full registry.

---

## 1. What gets stored (artifacts)

For each model the archiver stores:

- **Weights:** any of `.safetensors`, `.bin`, `.pt`, `.pth`, `.gguf`, `.ggml` (filtered by tier and `quant_levels`).
- **Config / tokenizer:** `config.json`, `tokenizer.json`, `tokenizer_config.json`, `special_tokens_map.json`, `generation_config.json`, `vocab.json`, `merges.txt`, `tokenizer.model`, plus other `.json` / `.txt` / `.model` / `.tiktoken` / `.py` at repo root (so custom code like DeepSeek’s is included).

So you get “master” weights plus everything needed to load and run the model (config, tokenizer, custom `.py`). No separate “artifacts” path — it’s one directory per model under the drive.

**Per model:** one directory per repo+revision:

- **Path:** `<drive_mount>/<content_subdir>/<org>/<repo>/<rev>/`
- **content_subdir:** `raw` (tiers A, B, E, F, G), `quantized` (tier C), `uncensored` (tier D).
- **rev:** `commit_sha` from registry or `main`.

Plus a `manifest.json` and descriptor in that directory, and a `.sha256` sidecar next to each weight file. A `latest` symlink points at the current rev.

---

## 2. Where things live (drives)

| Drive | Mount           | Capacity (typical) | Role |
|-------|-----------------|--------------------|------|
| **D1** | `/mnt/models/d1` | 5.5 TB | Raw giants (Tier A/B large) + **in‑progress downloads** |
| **D2** | `/mnt/models/d2` | 2.7 TB | Raw mid‑size (Tier A/B remainder, Tier D raw). **No new models should be added here** — treat D2 as effectively full. |
| **D3** | `/mnt/models/d3` | 2.7 TB | Quantized GGUF (Tier C) + Tier D GGUF |
| **D5** | `/mnt/models/d5` | 916 GB | **Metadata + rare overflow:** `archive/`, logs, `run_state.json`, `STATUS.md`. In exceptional cases, a small number of overflow models when D1/D3 are full. |

- **In‑progress downloads:** All partial LFS downloads and `.aria2` control files go to **D1’s `.tmp`** (`/mnt/models/d1/.tmp/<model_id>/`). When a file is done it is moved to the **target** drive (d1, d2, or d3). So during a run, D1 must have enough free space for both existing models and the largest single file currently downloading in `.tmp`. XET downloads use the library’s own cache; completion is still written to the target drive.

- **Root SSD:** Never holds model data; only the project tree and logs symlink.

---

## 3. Which models go to which drive

Assignment is per model in `config/registry.yaml` via the `drive:` field.

- **D1:** Largest raw models (e.g. DeepSeek‑V3, DeepSeek‑R1, Qwen3‑235B, Llama‑3.1‑405B, Mistral‑Large, Command R+, DeepSeek‑Coder‑V2‑Instruct, Qwen2.5‑VL‑72B, deepseek‑vl2, Llama‑3.2‑90B‑Vision, Grok‑1). Also all `.tmp` scratch.
- **D2:** Mid‑size raw (e.g. 7B–72B instruct, code, Mixtral, Yi, GLM, InternLM, uncensored raw).
- **D3:** GGUF quantized (tier C) and tier D GGUF, plus small raw (e.g. embeddings, Phi‑3‑mini, TinyLlama) that were explicitly assigned d3.

Current registry has roughly: **~18 models on d1**, **~54 on d2**, **~48 on d3**. Exact counts can change with registry edits; run a dry‑run or list by drive to confirm.

---

## 4. Do we have enough disk space?

- **D5:** Primarily metadata; 916 GB is more than enough for archive index, logs, and state, with headroom for a **small number of overflow models** when D1/D3 are full.
- **D1:** Must fit all d1 models **plus** headroom for `.tmp` (at least the size of the largest single file you might download, often 100–200 GB for sharded giants). 5.5 TB is intended to cover current d1 giants and scratch; if you add more very large models, check free space first.
- **D2:** `drives.yaml` has historically noted “FULL; no new writes” when the disk was near capacity. **Before adding or running new d2 models, check free space** (e.g. `df -h /mnt/models/d2`). If D2 is full, either free space, or assign new mid‑size raw models to **d1** in the registry (and ensure D1 has room).
- **D3:** Same idea: ensure free space on `/mnt/models/d3` for all d3 models (GGUF + any small raw on d3).

**Recommended:**

1. Before a full run: `df -h /mnt/models/d1 /mnt/models/d2 /mnt/models/d3`
2. Optionally run a **dry‑run** so the archiver prints per‑model sizes (it fetches file list from HF and sums size). That gives you a per‑drive total for the current registry.
3. If D2 is full: stop adding `drive: d2` for new models; put new raw mid‑size on **d1** (and possibly plan a future disk upgrade or rebalance).

---

## 5. Quick reference

| Question | Answer |
|----------|--------|
| Where are model weights stored? | On the drive in `registry.yaml` for that model: `<mount>/raw\|quantized\|uncensored/<org>/<repo>/<rev>/` |
| Where do in‑progress downloads go? | D1 only: `/mnt/models/d1/.tmp/<model_id>/` |
| Does D5 hold any model weights? | Normally no. D5 is metadata-only infrastructure **except** for a small number of overflow models when D1/D3 are saturated. |
| What exactly is archived per model? | Weight files (safetensors/bin/pt/pth/gguf/ggml) + config/tokenizer/custom .py + manifest + .sha256 sidecars |
| How do I see if I have enough space? | `df -h /mnt/models/d1 /mnt/models/d2 /mnt/models/d3` and optionally `archiver download --dry-run --all` for size estimates |
