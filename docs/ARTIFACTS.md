# Artifacts We Archive

This document describes the artifact inventory across all subprojects:
weight trees, checksum metadata, code snapshots, tooling mirrors, and
control-plane metadata.

---

## 1. Model weights (local archiver)

Downloaded from Hugging Face, verified with SHA-256, and stored per-drive. Formats: raw BF16/FP16 safetensors, GGUF (selected quant levels).

**Full per-model list** (master registry, legacy, specialist queue, uncensored vs tier-D Nemotron, tier E/F/G breakdown), plus **expected disk paths** and optional **download / GDrive** columns: [ARCHIVED-MODELS.md](ARCHIVED-MODELS.md). Regenerate after registry or state changes: `uv run --directory model-archival python3 ../scripts/generate-archived-models-doc.py` (on the archive host, or set `ARCHIVER_RUN_STATE` / `ARCHIVER_MODELS_MOUNT` to your paths).

### Tier A — Major models (raw)

- **General / reasoning:** DeepSeek-V3, DeepSeek-R1, R1 distills (Llama-70B, Qwen-32B/14B/8B), Qwen2.5/Qwen3 (72B, 32B, 14B, 7B, MoE), Llama 3.1/3.3 (405B, 70B, 8B), Gemma 3 (27B, 12B), Mistral-Large, Mistral-Small-24B, Phi-4, Command R+, Nemotron-70B, Tulu-3-70B.
- **Sizes:** From ~15 GB (7B) to ~1,340 GB (DeepSeek-V3); 405B ~756 GB.

### Tier B — Code models (raw)

- Qwen2.5-Coder-32B, Qwen3-Coder-30B-A3B, DeepSeek-Coder-V2 (Instruct + Lite), Devstral-Small-2507, Codestral-22B, OlympicCoder-32B, StarCoder2-15B.
- **Sizes:** ~30 GB to ~440 GB (DeepSeek-Coder-V2).

### Tier C — Quantized GGUF

- Same families as A/B in GGUF form (Q4_K_M or Q8_0): DeepSeek-R1/V3, distills, Qwen2.5/Qwen3, Llama 3.x, Mistral-Small, Phi-4, Gemma 3, Codestral, Devstral.
- **Sizes:** Order of hundreds of GB for 671B quants; tens of GB for smaller models.

### Tier D — Uncensored / abliterated

Exact Hugging Face `id` lists (including Nemotron rows on tier D for placement) live in [ARCHIVED-MODELS.md](ARCHIVED-MODELS.md) under **Uncensored, abliterated, and alignment-relaxed weights** and **Tier D — large checkpoints**.

- **Raw:** huihui-ai abliterated line, Dolphin family, mlabonne lorablated / NeuralDaredevil, failspy, CombinHorizon merges, FINGU Rombo/Chocolatine, rombodawg merge.
- **GGUF:** tensorblock and mlabonne abliterated GGUF variants aligned with the above.
- **Sizes:** Similar to base models; GGUF smaller.

### Tier E — Reasoning

- QwQ-32B, OlympicCoder-32B, Sky-T1-32B-Preview.
- Stored on D3 (research/reasoning).

### Tier F — Vision / VLMs

- Qwen2.5-VL-72B/7B, Gemma-3-4b-it, Llama-3.2-11B/90B-Vision-Instruct.
- Large on D1, smaller on D3.

### Tier G — Math / research

- Qwen2.5-Math-72B/7B, DeepSeek-R1-Distill-Qwen-7B.
- On D3.

### Per-model artifacts on disk

- Weight files (`.safetensors`, `.gguf`, etc.) in a directory named by repo (e.g. `org__ModelName/`).
- `manifest.json` — file list and SHA-256.
- `.sha256` sidecars per file.
- `DESCRIPTOR.json` / `DESCRIPTOR.md` — provenance.
- `global_index.jsonl` — append-only index of completed models.

---

## 2. Checksums (fingerprints)

- **No weight files.** Only LFS pointer files and metadata are fetched.
- **Output:** Per-repo directories under `model-checksums/` with:
  - `fingerprint.json` — full structured data (repo, commits, file list + SHA-256 + size).
  - `fingerprint.md` — human-readable summary.
  - `commits/<commit_sha>.json` — per-commit file list and hashes.
- **index.jsonl** — global append-only index.
- **leaderboard-snapshots/** — Open LLM Leaderboard snapshots (dated).
- **Purpose:** Verify any copy of a model (e.g. from a mirror) against author-published checksums; minimal storage (KB per model).

---

## 3. Source code (code-archival)

- **Shallow git clone** — latest commit on default branch.
- **Latest release tarball** from GitHub.
- **metadata.json** — licence, description, stars, last commit, archived date.
- **Categories:** inference, inference-ui, server, training, quantization, model-editing, evaluation, alignment, agents, coding-agents, rag, tooling, etc.
- **Risk levels:** critical, high, medium, low (drives selection and prioritisation).
- **Output:** One directory per project under the code-archival output root (e.g. `/mnt/models/d1/code-archival/`).

---

## 4. Tooling mirrors (bare git)

- From `tooling:` in `model-archival/config/registry.yaml`.
- **Artifacts:** Bare git repos at `/mnt/models/d5/tooling-archive/<id>.git`.
- **Projects:** Continue, Aider, Tabby, OpenHands, OpenDevin, LangChain, LangGraph, LlamaIndex, Semantic Kernel, AutoGen, vLLM, llama.cpp, Ollama, Sourcegraph, SWE-bench, HumanEval, etc.
- **Purpose:** Preserve code for IDE assistants, agent platforms, and serving backends without storing weights.

---

## 5. Metadata and state (D5)

- **run_state.json** — per-model status: pending, in_progress, complete, failed, skipped.
- **STATUS.md** — live dashboard (progress, active downloads, ETA, drive usage).
- **archive/** — replicated metadata (manifests, descriptors) synced to all drives after each model completes.
- **logs/** — run logs.
- **Run reports** — timestamped Markdown reports per run (startup, pre-flight, per-model events, final summary).

---

## 6. Cloud backup (gdrive-archival)

- **Registry uploads:** `gdrive-archival/logs/registry-upload-state.json` — which model relpaths finished verify + rclone (skip those on later runs; `--resync-all` to force). `gdrive-archival/logs/GDRIVE-REGISTRY-UPLOAD-STATUS.md` — human summary from discovery + log + tracker; refresh via `python3 backup.py upload-registry-status` or after `backup-registry`.
- **Default:** **Staging folders** on D3/D5 (`upload_staging`); only immediate subdirectories are uploaded to the configured Drive folder (`backup-staging` / `run-staging.sh`). See `gdrive-archival/README.md`.
- **Legacy (optional in config):** `extra_paths` (registry, full D5 mirror, etc.), budget `upload_selection`, or explicit `model_ids_*`.

---

## Artifact integrity model

- **Weights:** verified locally against `manifest.json` / `.sha256` sidecars.
- **Fingerprints:** capture upstream SHA-256 values from HF LFS pointers.
- **Code snapshots:** preserve repo state + release tarballs + metadata.
- **Cloud uploads:** rely on verify-first local checks and `rclone --checksum`
  for resumable transfer decisions.
