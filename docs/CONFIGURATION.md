# Configuration

This document describes the configuration we have decided upon: registry layout, drive roles, tiers, priorities, and tooling list.

---

## Master model list — local/config/registry.yaml

The registry is the **source of truth** for the weight downloader. It defines:

- **models** — list of model entries, each with:
  - `id` — unique key (e.g. `deepseek-ai/DeepSeek-V3`).
  - `hf_repo` — Hugging Face repo (usually same as id).
  - `tier` — A (major), B (code), C (GGUF), D (uncensored/abliterated), E (reasoning), F (vision), G (math/research).
  - `drive` — `d1`, `d2`, or `d3` (where weights are stored).
  - `priority` — 1 = token-free / core; 2 = gated (HF token + licence acceptance).
  - `licence` — e.g. MIT, Apache-2.0, Qwen, llama3.1, Gemma-ToU.
  - `requires_auth` — true if gated on Hugging Face.
  - `commit_sha` — pinned after first download; `null` until then.
  - Optional: `notes`, `quant_levels`, `parent_model`, `method`.

- **tooling** — list of non-model projects to mirror as bare git repos on D5:
  - `id`, `category`, `repo`, `description`, `notes`.
  - Categories: ide_assistant, agent_platform, agent_framework, serving_backend, code_intel, eval_harness.

Tiers encode usage and placement:

- **A/B** — flagship and code models (raw BF16/FP16); large on D1, mid-size on D2.
- **C/D** — GGUF and uncensored/abliterated; D2 for raw uncensored, D3 for GGUF.
- **E/F/G** — reasoning, vision, math, research; D1 for large VLMs, D3 for smaller and research.

Priority 1 models are safe to run with `--priority-only 1` (no HF token). Priority 2 requires token and often licence acceptance on HF.

---

## Drive configuration — local/config/drives.yaml

Each logical drive has:

- **mount_point** — e.g. `/mnt/models/d1`.
- **role** — short description of what lives there.
- **tmp_dir** — (D1 only) in-progress download scratch, e.g. `/mnt/models/d1/.tmp`.
- **by_id**, **serial** — optional physical disk identifiers for remapping after VM/host changes.

Decided roles:

| Drive | Role |
|-------|------|
| d1 | Raw giants (Tier A large + Tier B large); `.tmp` scratch for in-progress downloads. |
| d2 | Raw mid-size (Tier A remainder + Tier B small + Tier D uncensored raw). |
| d3 | Quantized GGUF (Tier C + Tier D quants). |
| d5 | Metadata: archive/, logs, run_state.json, STATUS.md, tooling-archive/. |

Root SSD must never receive model data; only the Python env and logs symlink live there.

---

## Fingerprints registry — fingerprints/config/registry.yaml

Separate registry for the checksum crawler: models to fingerprint with family, tier, and importance (critical / high / medium). Can be generated from leaderboard data via `fingerprints/scripts/build_registry.py`.

---

## Code-archival registry — code-archival/registry.yaml

Projects to archive with:

- `id`, `github` (org/repo), `category`, `risk` (critical / high / medium / low), `licence`, `notes`.
- Categories include inference, training, quantization, agents, evaluation, etc.

---

## GDrive backup — gdrive-archival/config.yaml

- **archiver_root** — path to `local/`.
- **gdrive.remote** — rclone remote (e.g. `gdrive:llm-survivor`).
- **gdrive.base_path** — prefix under remote.
- **extra_paths** — list of paths to back up (registry, drives, D5 archive/logs/run_state, fingerprints dir, code-archives).
- **model_ids_gguf** / **model_ids_full** — optional subset of model IDs for selective backup.

---

## Environment

- **HF token:** `~/.hf_token` (e.g. set via `bash deploy/sethfToken.sh hf_TOKEN`). Required for gated models (Llama, Gemma, Mistral-Large, etc.).
- **Pre-flight:** `uv run archiver tokens check` validates access to gated models before a full run.
