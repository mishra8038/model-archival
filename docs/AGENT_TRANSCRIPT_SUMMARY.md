# Agent transcript summary (canonical)

**Purpose:** Capture **durable outcomes** from AI-assisted work so agents and humans can **skip** parsing raw Cursor agent transcripts (`~/.cursor/projects/.../agent-transcripts/`). Those files are verbose, lossy for tooling, and not in-repo.

**How to use**

1. Prefer this file + [`model-archival/docs/AI_CONTEXT.md`](../model-archival/docs/AI_CONTEXT.md) + [`.cursor/rules/`](../.cursor/rules/) for bootstrap.
2. Use repo **`.chat/`** only if you need a specific session paper trail; promote anything still true into **this doc** and/or proper `docs/`.
3. After a meaningful agent session, append a **dated bullet block** below (facts, file paths, operational notes). Keep it short; link to real docs for depth.

---

## 2026-04-08 — vLLM + D5 `specialist` → D1 (repo + VM)

- **`model-archival/config/drives.yaml`:** **`d5_vllm.mount_point`** → **`/mnt/models/d1/vllm`** (label **`d5_vllm`** unchanged; **`/mnt/models/d5/vllm`** may symlink after move).
- **`registry-specialists.yaml`:** **`drive: d1`** for former D5 rows (Mistral-Small-24B, DeepSeek-R1-Distill-Qwen-32B, QwQ-32B, Qwen3.5-35B-A3B{,-Base}, tensorblock Llama-3.3-70B GGUF) + note tweaks.
- **vLLM paths:** **`vllm-hosting/config/*.yaml`**, **`env-archive-vm-vllm.sh`**, **`vllm_archive_pull_one.py`**, **`_generate_vllm_*.py`**, **`registry-vllm.yaml` header**, **`VLLM-ARCHIVE.md`**, **`run-vllm-d5-archiver.sh`**, **`.cursor/rules/archiver-codebase.mdc`**, **`docs/AGENTS.md`**, **`ollama-hosting/docs/TARGET_MODEL_LIST.md`** — default root **`/mnt/models/d1/vllm`**.
- **Disk manifest TSV:** **`model-archival/reports/MODEL-DISK-MANIFEST-2026-04-05.tsv`** — **d5** specialist/science rows → **d1** + absolute paths under **`/mnt/models/d1/specialist/...`**.
- **VM (`192.168.8.65`):** Long **`rsync`** **d5/vllm → d1/vllm** then **`mv`**, **`ln -s`**, remove backup (prior agent shell). **`/tmp/wait-vllm-then-specialist.sh`** (nohup): waits until **`/mnt/models/d5/vllm`** is a **symlink**, then **`rsync` specialist → d1**, same **`mv`/`ln -s`** pattern for **`d5/specialist`**. Log: **`/tmp/d1-specialist-after-vllm.log`**.

## 2026-04-06 — VM: Graphcore on D1 (move + D5 `graphcore-*` into tree)

- **`x@192.168.8.65`:** moved **`/mnt/models/d5/graphcore`** → **`/mnt/models/d1/graphcore`** (~**47 GiB**, cross-fs `mv`). User then merged **`d5/graphcore-archive`**, **`d5/graphcore-downloads`**, **`d5/graphcore-projects`** into **`/mnt/models/d1/graphcore/`** as **`graphcore-archive/`**, **`graphcore-downloads/`**, **`graphcore-projects/`**.
- **Docs:** **`docs/remote/REMOTE_ACTIVITY_LOG.192.168.8.65.md`**; manifest scope **`model-archival/reports/MODEL-DISK-MANIFEST-2026-04-05.md`** (`d1/graphcore` excluded from model TSV). **GDrive audit logs:** `gdrive-archival/logs/GDRIVE-REGISTRY-UPLOAD-STATUS.md`, `gdrive-archival/logs/registry-uploaded-models.md`, `gdrive-archival/logs/registry-uploaded-models.json` — **`d5/graphcore*`** path prefixes rewritten to **`d1/graphcore/...`** plus layout notes where applicable.

## 2026-04-05 — vLLM immediate queue (>21B, <120 GiB, focused)

- **`vllm-hosting/config/vllm-immediate-targets.yaml`** — **16** causal HF repos: **>21B** total params, **<120 GiB** each, roles **`general` / `specialist` / `uncensored`**. Generator: **`vllm-hosting/scripts/_generate_vllm_immediate_targets.py`** (~**948 GiB** summed). **`vllm_archive_pull_one.py`** defaults to this manifest; wide catalog: **`--manifest .../vllm-archive-manifest.yaml`**.
- **`model-archival/config/registry-vllm-immediate.yaml`** — same repos for **`archiver download --registry`** (manifest+SHA parity). **`vllm-hosting/docs/VLLM-ARCHIVE.md`** + **`README`**: archiver vs **`huggingface-cli`** guidance.

## 2026-04-05 — Specialists: science + management / finance

- **`registry-specialists.yaml` + vLLM generator:** **Science** — **`allenai/OLMo-2-1124-7B-Instruct`**, **`allenai/scibert_scivocab_uncased`**, **`m3rg-iitd/matscibert`**, **`nvidia/OpenMath-Nemotron-{1.5B,7B}`** (CC-BY-4.0 in notes), **`TIGER-Lab/MAmmoTH2-8B`**, **`Snowflake/snowflake-arctic-embed-l-v2.0`**, **`HuggingFaceTB/fineweb-edu-classifier`**. **Management / finance** — **`ibm-granite/granite-3.3-8b-instruct`**, **`AdaptLLM/finance-chat`** (`licence: llama2`), **`ProsusAI/finbert`**. Regenerated **`vllm-hosting/config/vllm-archive-manifest.yaml`**.

## 2026-04-05 — Specialists: chemistry / math / law (registry + vLLM manifest)

- **`model-archival/config/registry-specialists.yaml`:** Added **legal** encoders **`nlpaueb/legal-bert-{base,small}-uncased`**, **`pile-of-law/legalbert-large-1.7M-2`** (PoL NC-SA terms in notes). **Math:** **`Qwen/Qwen2.5-Math-1.5B-Instruct`**, **`Qwen/Qwen2-Math-7B-Instruct`**, **`AI-MO/NuminaMath-7B-{TIR,CoT}`**, **`qingy2019/Qwen2.5-Math-14B-Instruct`**, **`meta-math/MetaMath-Mistral-7B`**, **`WizardLMTeam/WizardMath-7B-V1.1`** (`licence: other` — verify card). **Chemistry:** **`language-plus-molecules/molt5-base-smiles2caption-LPM24`**, **`DeepChem/ChemBERTa-77M-MLM`**, **`Derify/ModChemBERT-MLM-DAPT-TAFT`**.
- **`vllm-hosting/scripts/_generate_vllm_manifest.py`** + regenerated **`vllm-hosting/config/vllm-archive-manifest.yaml`** (encoder/MolT5 rows noted as non-causal where relevant).

## 2026-04-05 — vLLM-oriented HF archive (`d5/vllm`, replaces Ollama pull intent)

- **New tree:** **`vllm-hosting/`** — **`config/vllm-archive-manifest.yaml`** (**57** deduped HF repos, **`~2827 GiB`** summed estimate, disclaimer in YAML), **`config/env-archive-vm-vllm.sh`** (`HF_HOME` under **`/mnt/models/d5/vllm`**, prepends **`$VLLM_ARCHIVE_ROOT/venv/bin`** when **`huggingface-cli`** exists), **`scripts/vllm-archive-setup-dirs.sh`**, **`scripts/vllm-archive-pull-one.sh`**, **`scripts/vllm_archive_pull_one.py`** (queue + lock + **`state/completed_repos.txt`**), **`scripts/_generate_vllm_manifest.py`** (regenerate manifest). **Docs:** **`vllm-hosting/docs/VLLM-ARCHIVE.md`**, **`vllm-hosting/README.md`**. **Ollama doc pointer:** **`ollama-hosting/docs/TARGET_MODEL_LIST.md`** header.
- **Archive VM (`192.168.8.65`):** **`/mnt/models/d5/vllm`** layout; **`vllm-hosting/`** is **in the monorepo** — after **`git pull`** at **`/home/x/dev/model-archival`**, use **`./vllm-hosting/...`** (not a separate rsync-only tree). **`trickle`** may be missing; use **`USE_TRICKLE=0`** until capped pulls. **`MODEL_ARCHIVAL_UV_ROOT=/home/x/dev/model-archival/model-archiver`** for **`uv run` + PyYAML**. **D5** may be too small for the full manifest — use subset or **`VLLM_ARCHIVE_ROOT`** on **D2**.
- **When to pull:** operator runs **`source …/env-archive-vm-vllm.sh`** then **`./vllm-hosting/scripts/vllm-archive-pull-one.sh`** (default **2 MiB/s** via **`THROTTLE_KBPS=2048`** + **`trickle`**).
- **2026-04-05 (later):** Manifest **schema v2** — **`max_approx_disk_gib_per_model: 120`**; **`policy.excluded_over_limit`** lists former **>120 GiB** repos (70B class, Gemma‑4‑31B, 72B VL, Qwen3.5‑122B, dolphin‑72B, etc.). Added **`target_category`**: **`specialist`** (e.g. R1‑0528‑Qwen3‑8B, OlympicCoder 7B/32B, gte‑Qwen2 / e5‑mistral / bge‑en‑icl, deepseek‑math / Qwen2.5‑Math‑7B, TechxGenus starcoder2‑15b‑instruct, Llama‑3.2‑11B‑Vision) and **`uncensored`** (huihui R1‑Qwen‑32B abliterated, Mistral‑Small‑24B abliterated, Qwen2.5‑14B abliterated v2, RomboUltima‑32B). Regenerate: **`uv run --directory model-archival python ../vllm-hosting/scripts/_generate_vllm_manifest.py`**.
- **vLLM manifest vs archiver:** **`model-archival/scripts/vllm_manifest_vs_archiver.py`** — merged registry + **`run_state.json`** + on-disk **`_check_manifest_complete`** (or unregistered drive scan). On archive VM (**61** manifest repos, snapshot): **34** verified paths. **`--out-md`** → **`vllm-hosting/reports/VLLM-VS-ARCHIVER.md`** (ensure **`vllm-hosting/reports/`** exists before **`scp`** from VM). **`--out-md`** now writes only the Markdown file (summary line on stderr). Spot-check rows with **`run_state: complete`** but **no** verified path (**QwQ-32B**, **Mathstral**, **deepseek-math-7b-instruct**, etc.): layout, **`.sha256`** sidecars, or **`latest`**-only dirs.

## 2026-04-05 — D1 prune: &lt;60% progress (VM applied)

- **`src/archiver/d1_disk_eval.py`:** Shared **`gather_d1_incomplete_rows`**, **`remove_models_from_yaml_registry`** (``.bak`` before round-trip), **`strip_models_from_run_state`**.
- **`scripts/d1_prune_low_progress.py`:** Default **dry-run**; **`--apply`** deletes **`repo_base`** + **`.tmp/<slug>`**, drops ids from **`registry.yaml`** + **`registry-d1-manifest-incomplete.yaml`**, strips **`run_state.json`**; **`--apply-disk-only`** / **`--no-treat-hf-errors-as-prune`** / **`--threshold-pct`**. **VM (`192.168.8.65`):** **`--apply`** removed **15** low-progress ids (only **6** trees still existed on disk); **3** incomplete **≥60%** rows left in narrow file (**InternLM**, **Llama-3.3-70B-Instruct**, **DeepSeek-V3-0324**). PyYAML rewrite **drops comments** — **`config/registry.yaml.bak`** on VM preserves pre-prune file.
- **`scripts/evaluate_d1_incomplete.py`:** Refactored to use **`d1_disk_eval`**; detail table adds **Progress %**.

## 2026-04-05 — D1 incomplete evaluation script (narrow registry + download estimate)

- **`model-archival/scripts/evaluate_d1_incomplete.py`:** On the archive host (D1 mounted), scans **`registry.yaml`** rows with **`drive: d1`**, marks **manifest-complete** if any revision dir passes **`_check_manifest_complete`**, compares to **`registry-d1-manifest-incomplete.yaml`**, and calls HF (same file filters as **`resolve_model_archive_files`**) to estimate **remaining GiB** (HF sizes minus bytes under resolved commit dir, sibling revs, and **`d1/.tmp/<slug>/`**; sidecar-done files excluded). **`downloader.py`:** factored **`resolve_model_archive_files(model, api)`** and **`estimate_remaining_download_bytes(...)`** for reuse.
- **Run:** `cd model-archival && export HF_TOKEN=… && uv run python scripts/evaluate_d1_incomplete.py` (optional `--out-md reports/D1-INCOMPLETE-EVAL.md`).

## 2026-04-05 — MiniMax M2.7: dropped from active registries (gated)

- **Removed** **`MiniMaxAI/MiniMax-M2.7`** from **`model-archival/config/registry.yaml`** and **`registry-d1-manifest-incomplete.yaml`** (operator: repeatedly **skipped** — gated HF token / licence).
- **Recorded** under **`categories.auth`** in **`model-archival/config/failed-models-registry.yaml`** (`primary_source: operator`); bumped **`summary`** counts (**`auth: 3`**, **`total_rows: 47`**, **`total_failed: 31`**). **VM:** update **`run_state.json`** or run **`uv run archiver failed-registry`** when syncing state so default runs do not keep a stale **`skipped`** row.

## 2026-04-05 — PAR2: per-revision backfill driver for D2/D3

- **`model-archival/scripts/par2_backfill_d2_d3.py`:** Walks **`raw/`**, **`quantized/`**, **`uncensored/`**, **`specialist/`** on **`/mnt/models/d2`** and **`d3`**; invokes **`par2 c`** with **`-B<rev_dir>`** and relative file paths into each revision’s **`.parity/`** (par2cmdline-compatible). Space checks: **`--reserve-gib`**, estimate fudge. Skips existing **`.par2`**; per-drive **abandon** on **`par2`** failure or free &lt; reserve after a create; oversized single trees **skip** without abandoning the whole disk. Reports **`reports/PAR2-D2-D3-RUN-*.md`** / **`.json`** + **`PAR2-D2-D3-LATEST.md`**. **`find_par2()`** also uses **`~/.local/bin/par2`** when PATH lacks system install.
- **`integrity_tools/parity_cli.py`:** Same **`par2 c` / `-B` / relative paths** for create; **`verify`/`repair`** use resolved **`par2`** and **`cwd=model`**. **Archive VM:** built par2cmdline from source into **`~/.local/bin`** (no sudo); full backfill started via **`nohup`** + **`PATH`** (see **`/mnt/models/d3/logs/par2-d2-d3-*.log`**).
- **Docs:** **`model-archival/reports/PAR2-BACKFILL-D2-D3.md`**, **`reports/README.md`**, **`integrity_tools/README.md`** § fleet backfill; **`PAR2-STORAGE-ESTIMATE-D1-D2-D3.md`** links the script.

## 2026-04-05 — VM: dedupe redundant HF trees (registry-aligned)

- **`192.168.8.65`:** Consolidated same-`hf_repo` copies to **one** tree per **`registry.yaml`**: removed **d3** partial **MiniMaxAI/MiniMax-M2.5** (kept **d1**); **rsync** **Phi-4-mini-instruct** **d3→d5** (registry **d5**), removed **d2/d3** BF16 stubs; **rsync** **Llama-3.2-3B-Instruct** **d3→d2**, set **`latest`** on **d2**, removed **d3**; removed **d2** stub + **d3 specialist/science** stub for **deepseek-coder-6.7b-instruct**; removed **d3 specialist/science** stub for **failspy/Meta-Llama-3-70B-Instruct-abliterated-v3.5**. **Qwen2.5-Math-72B-Instruct**: only **d5** + symlink layout (no action).
- **Reports / tools:** **`model-archival/reports/MODEL-DEDUPE-2026-04-05.md`**; **`model-archival/scripts/scan-cross-drive-raw-duplicates.sh`**, **`scan-suspicious-revision-layout.sh`** (read-only; use before bulk deletes).

## 2026-04-05 — Ollama queue: embedding models (beyond `bge-m3`)

- **`TARGET_QUEUE_ORDERED.txt`** / **`OLLAMA_MODEL_REGISTRY.json`:** After **`bge-m3`**, added **`granite-embedding`**, **`nomic-embed-text`**, **`embeddinggemma`**, **`snowflake-arctic-embed`**, **`mxbai-embed-large`**, **`bge-large`**, **`qwen3-embedding`** (manifest sizes verified on **`registry.ollama.ai`**). **`ollama_registry_tool.py`** `default_group_for_tag` maps these to **`embedding`**.

## 2026-04-05 — Ollama targets: MedGemma community pulls + DeepSeek R1 tag fix

- **`ollama-hosting/registry/TARGET_QUEUE_ORDERED.txt`** + **`OLLAMA_MODEL_REGISTRY.json`:** **`alibayram/medgemma:4b`** (~2.49 GB manifest) after **`gemma3:4b-it-q4_K_M`**. **`alibayram/medgemma:27b`** **removed** from queue — **27B MedGemma** via **HF** (`google/medgemma-27b-it`, etc.). **`starcoder2:15b-instruct-q4_K_M`** **not** queued (**404** on registry — keep HF bartowski GGUF).
- **Docs / YAML:** **`TARGET_MODEL_LIST.md`**, **`SPECIALIST-HF-PENDING-OLLAMA.md`** (ollama-hosting + model-archival copies), **`registry-specialists.yaml`** (MedGemma + DeepSeek R1 note), **`final_downloads.yaml`**, **`ollama-registry-size-cache.json`** (both `docs/data/` trees): replaced invalid **`deepseek-r1:32b-class`** with **`deepseek-r1:32b-qwen-distill-q4_K_M`**.

## 2026-04-05 — VM: `d5/specialist` → `d2/specialist` blocked (d2 full)

- **`192.168.8.65`:** Partial **`rsync`** of **`/mnt/models/d5/specialist`** (~**154G**) to **`/mnt/models/d2/specialist`** failed with **ENOSPC** (~**121G** copied). Removed incomplete **`/mnt/models/d2/specialist`** to recover d2 (**~114G** free afterward). **Source on d5 unchanged.**
- **Root cause:** d2 **~2.7T** filesystem is too full to hold the **154G** specialist tree in addition to existing **`d2/raw`** / **`d2/uncensored`** / **`d2/quantized`** — need **~40–60G+** more free space (or offload other data) before retry. **`rsync -av --remove-source-files`** … `/mnt/models/d5/specialist/` → `/mnt/models/d2/specialist/` when ready.
- **Registries / gdrive roots:** **Not** updated to **`d2/specialist`** (would desync until the move completes). Scratch: **`.chat/2026-04-05-d5-specialist-d2-move-blocked.md`**.

## 2026-04-03 — VM `priority_overrides.json` (Gemma-4 first, failed tail)

- **`192.168.8.65` `/mnt/models/d3/priority_overrides.json`:** Gemma-4 small dense **-620**, 26B MoE **-580**, 31B overrides removed; specialist **failed** → **120**; **`unsloth/DeepSeek-R1-GGUF`** (failed) **120**; last four (**`DeepSeek-V3-GGUF`**, **`deepseek-vl2`**, **`Qwen3.5-122B-A10B`**, **`Qwen3.5-397B-A17B`**) → **250**; pending/in_progress override **0** removed. Log: **`docs/remote/REMOTE_ACTIVITY_LOG.192.168.8.65.md`**.
- **Gemini 3 HF previews:** Removed **`google/gemini-3-flash-preview`** and **`google/gemini-3.1-flash-lite-preview`** from **`registry-specialists.yaml`**; added to **`registry-legacy.yaml`** (`legacy: true`, no token / Gemma 4 sufficient). **`failed-registry`** regenerated on VM; repo **`config/failed-models-registry.yaml`** + **`docs/FAILED_MODEL_REGISTRY.md`** updated.

## 2026-04-02 — Archiver: `failed-registry` (run_state + historical `run-report-*.md`)

- **`model-archival/src/archiver/failed_registry.py`:** Classifies `error` / `last_error` → `disk_space` | `unavailable` | `auth` | `failed_shards` | `verify` | `other` (+ `skipped_gated` with `--include-skipped`); parses **`run-report-*.md`** for past download/verify/skip events; merges **`registry*.yaml`**; dedupes incidents; **`historical_only`** rows when not currently `failed` in `run_state`.
- **`uv run archiver failed-registry`:** **`--no-historical`**, **`--reports-dir`** (repeatable). Writes **`config/failed-models-registry.yaml`** + **`docs/FAILED_MODEL_REGISTRY.md`**. Docs: **`model-archival/docs/OPERATIONS.md`**, **`docs/AI_CONTEXT.md`**.

## 2026-04-02 — `gh-archival`: owned GitHub repos → tarballs + rclone

- **`gh-archival/`:** Standalone Python package (`uv sync`); console script **`gh-archival`**. Commands: **`check`**, **`list-repos`** (API `affiliation=owner`, default branch **`main`** unless `--any-default-branch`), **`run`** (`git archive` **`.tar.gz`** per repo or `--format dir`, manifest JSON, optional **`rclone copy`** via **`GH_ARCHIVAL_RCLONE_REMOTE`**). See **`gh-archival/README.md`**.
- **Ollama library metadata:** **`fingerprints/scripts/snapshot_ollama_library.py`** archives **`https://ollama.com/api/tags`**, **`/v1/models`**, **`/library`** (model families), per-family **`/library/<name>/tags`**, and (by default) **`https://registry.ollama.ai/v2/library/<model>/manifests/<tag>`** OCI manifests — full **`manifest_sha256`**, per-layer digests, and **`model_layer_digests`** (`application/vnd.ollama.image.model`, for GGUF blob verification vs **`sha256sum`**). **`--no-manifests`** skips registry. Output **`fingerprints/ollama-library/YYYY-MM-DD/snapshot.json`** (+ README).

## 2026-03-30 — Specialist queue: completion-based `priority_overrides` + VM run

- **`model-archival/scripts/compute-priority-overrides.py`:** Multi-drive scan vs `run_state.json`; **`--defer-id`** for huge partials when `total_bytes` is missing. **`model-archival/scripts/stop.sh`:** `pgrep -f 'archiver.*[[:space:]]download'`. **`model-archival/docs/OPERATIONS.md`:** overrides + older-VM `uv run archiver --registry … download` example.
- **VM `192.168.8.65`:** Merged `/mnt/models/d3/priority_overrides.json`; started **`screen -S archiver-specialists`** adaptive specialist run — **`docs/remote/REMOTE_ACTIVITY_LOG.192.168.8.65.md`**.

## 2026-03-29 — Deploy: tmux + powerline + fonts + tmux-powerline

- **`deploy/setup-mxlinux.sh`:** `tmux`, `python3-powerline`, `fonts-powerline` in `PACKAGES`; step **1b** clones [erikw/tmux-powerline](https://github.com/erikw/tmux-powerline) → `~/.tmux-powerline`.
- **`deploy/setup-artix.sh`:** `tmux`, `python-powerline`, `powerline-fonts`; same **1b** clone.
- **`deploy/_common.sh`:** `install_tmux_powerline_repo` (override with `TMUX_POWERLINE_URL`). **`deploy/verify-environment.sh`:** optional `tmux` check. Docs: **`model-archival/docs/DEPLOYMENT.md`**, **`PROJECT_PROMPT.md`**; **`.cursor/rules/vm-operations.mdc`**.

## 2026-03-29 — Deploy: fish + Oh My Fish

- **`deploy/setup-mxlinux.sh` / `setup-artix.sh`:** `fish` in `PACKAGES`; step **1c** runs **`install_oh_my_fish`** in **`deploy/_common.sh`** (curl official installer → `fish … --noninteractive --yes`). Skip: **`OMF_SKIP=1`**. Override installer URL: **`OMF_INSTALL_URL`**. **`deploy/verify-environment.sh`:** optional **`fish`** check.

## 2026-03-29 — GitHub-facing archive inventory (`docs/archive-inventory/`)

- **`scripts/generate-archive-inventory.py`:** Writes JSON + Markdown under **`docs/archive-inventory/`**: merged master+legacy+specialist models with per-drive paths, optional `run_state.json` status, manifest summary + **`manifest_sha256`** when `manifest.json` is readable, full disk scan for orphan manifest trees, tail of **`global_index.jsonl`**, **`code-archival/registry.yaml`** as JSON/MD, **`gdrive-registry.yaml`** roots, monorepo scope summary. **`--include-file-checksums`** embeds per-file SHA-256 from manifests (large).
- **Docs:** **`docs/archive-inventory/README.md`**; pointers in **`docs/ARCHIVED-MODELS.md`**, **`model-archival/docs/AI_CONTEXT.md`**.

## 2026-03-29 — Archiver: `.tmp` scratch audit (JSON + MD on D3)

- **`model-archival/src/archiver/tmp_audit.py`:** Scans ``<mount>/.tmp/*`` for every drive in ``drives.yaml``; merges the four registry YAMLs for **id → drive**; reads ``run_state.json`` (read-only JSON); classifies each folder vs verified installs (**``manifest.json`` + ``.sha256`` sidecars**, same rule as ``downloader._check_manifest_complete``). Writes ``logs/TMP-SCRATCH-AUDIT.json`` and ``logs/TMP-SCRATCH-AUDIT.md`` under D3 infra.
- **`uv run archiver audit-tmp`:** CLI (optional ``--infra`` for hosts without mounts; ``--delete-reclaimable --apply`` removes only ``reclaimable_tmp`` rows). **`scripts/audit_tmp_status.sh`** wrapper.
- **`model-archival/docs/OPERATIONS.md`:** “Scratch audit” subsection under disk maintenance.

## 2026-03-28 — GDrive: pre-upload verify repair script + non-model `manifest.json`

- **`gdrive-archival/repair_preupload_failures.py`:** Reads `logs/gdrive-preupload-verify-failures.jsonl`; re-fetches only files that still fail SHA vs `manifest.json` via `hf_hub_download` (pinned `commit_sha`); optional `rclone copy` + `uploaded.log` / tracker update; independent logs `logs/preupload-verify-repair.log`, `logs/preupload-verify-repair-state.json`; reconcile runs `python3 backup.py upload-registry-status` and appends `logs/PREUPLOAD-REPAIR-RECONCILE.md` (skipped on `--dry-run`).
- **`gdrive-archival/upload_registry.py`:** `_is_archiver_model_manifest` — if `manifest.json` exists but lacks archiver shape (`hf_repo` + `files` list), **skip archiver SHA verify** and allow upload (fixes `d5/code-archives` code-archival index vs model-manifest confusion).
- **`gdrive-archival/AGENTS.md`:** Entry point for the repair script.

## 2026-03-25 — GDrive: granular `registry-tree` tracking for d5/

- **`gdrive-archival/upload_registry.py`:** For `path: d5` with `tree_upload_min_depth` (default **3** in yaml), discover non-overlapping subtree units (depth‑3 dirs + shallow top-level branches), skip units overlapping `d5_exclude` / `tree_upload_exclude` / `quantized/**` / `uncensored/**` / model revision paths; each successful `rclone copy` appends **`registry-tree`** to `logs/uploaded.log` and the relpath to `registry-upload-state.json` `completed_models`. **`tree_upload_min_depth: 0`** on the d5 root restores legacy single `registry-d5` full-tree copy.
- **`gdrive-archival/gdrive-registry.yaml`:** d5 root documents `tree_upload_min_depth: 3`.
- **Remote metadata cache:** `upload_registry.py` can now refresh Drive tree metadata snapshot via `--refresh-remote-tree-cache` (writes `logs/gdrive-remote-tree-cache.json` + `logs/GDRIVE-REMOTE-TREE-CACHE.md` with per-root dir/file counts + listing digests). Normal runs auto-spawn this in background on a cooldown (`config.yaml` → `remote_tree_cache.enabled`, `refresh_interval_hours`).

---

## 2026-03-25 — Archiver infra on D3; D5 models-only

- **`model-archival/src/archiver/cli.py`:** `run_state.json`, `logs/`, `archive/` (primary), `STATUS.md`, activity log, `gdrive_metadata_pending`, `priority_overrides.json` → **D3** (`_infra_root`). Scratch: D1 then non-D5 `tmp_dir`, then `d3/.tmp` — **never D5**. `sync_archive()` replicas → **D1 + D2 only** (`_archive_replica_mounts`). One-time copy from legacy D5 paths via `_maybe_migrate_infra_from_d5` when D3 files are missing.
- **`config/drives.yaml`:** D5 `tmp_dir` removed; roles updated. **`gdrive-archival/config.yaml`:** `metadata_pending_path` → `/mnt/models/d3/gdrive_metadata_pending`. **`gdrive-archival/backup.py`** defaults: `run_state` → d3.
- **Rules/docs touched:** `.cursor/rules/archiver-codebase.mdc`, `vm-operations.mdc`, `model-archival/docs/AI_CONTEXT.md`; helper scripts `gen-manifest.py`, `generate-archived-models-doc.py`, `run.sh`, `verify-archive.py` example.

---

## 2026-04-05 — `archive/` replicas include D5

- **`model-archival/src/archiver/cli.py`:** `_archive_replica_mounts` now lists **d1, d2, d5** (D3 remains canonical `archive/`). **`sync_archive()`** overwrites each replica from D3 after each successful model complete.
- **Docs/rules:** `docs/AI_CONTEXT.md`, `docs/OPERATIONS.md`, `docs/REQUIREMENTS.md` (design bullets), `.cursor/rules/archiver-codebase.mdc`.
- **VM:** one-shot `sync_archive` run so **`/mnt/models/d5/archive`** matches D3 (~600K each on d1/d2/d5 after sync).

---

## 2026-03-25 — `multidisk-downloader` requirements scaffold

- Added new project-doc folder **`multidisk-downloader/`** with:
  - `README.md` (scope + document map),
  - `REQUIREMENTS.md` (usage-pattern-derived downloader/uploader requirements),
  - `ARCHITECTURE-BOUNDARIES.md` (strict selector vs transfer-engine contracts).
- Formalized a hard separation rule: model selection/planning is selector-only; downloader/uploader execute versioned plans and must not read selection registries for decision logic.
- Captured transfer safety invariants as requirements: resumability, atomic state/report writes, integrity verification, non-destructive upload semantics, clean shutdown/restart behavior, and explicit auth/config handling.

---

## 2026-03-25 — Context + bandwidth + transcript policy

- **`model-archival/docs/AI_CONTEXT.md`:** Compact module/path/invariant map for agents; tool hints (Cursor `@`, Aider `/read`).
- **`model-archival/AGENTS.md`:** Pointer to `AI_CONTEXT.md` and Cursor rules.
- **Cross-links:** `PROJECT_PROMPT.md`, `docs/PROJECTS.md`, `docs/README.md`, `.cursor/rules/archiver-codebase.mdc` (also corrected **`scripts/run.sh`** / **`scripts/stop.sh`** paths in that rule).
- **`cli.py`:** If `--bandwidth-cap` > 0, set `HF_HUB_ENABLE_HF_TRANSFER=0` — coarse guard so hub/XET does not ignore the cap; **approximate** neighbor-friendly throughput is acceptable.
- **`scripts/run.sh`:** When `BANDWIDTH_CAP` is set, scheduled-cap **report** fields are cleared so the run report matches CLI (download already omitted scheduled args).
- **This file:** Established as the in-repo substitute for transcript mining.
- **Remote ops log:** Added `docs/remote/REMOTE_ACTIVITY_LOG.<host>.md` to record commands/actions/outcomes on remote machines (VM/SSH).
- **`.chat/` + `.cursorignore`:** Session notes folder renamed from `chat/` → **`.chat/`**; repo **`.cursorignore`** lists **`.chat/`** and **`.vscode/`**. User-wide Cursor rules under **`~/.cursor/rules`** (symlinks to `~/z/env/ai/cursor/rules/`) define default **context compaction** for all projects.
- **GDrive registry upload fixes:** Removed `gdrive-upload` roots from `gdrive-registry.yaml`; patched registry uploader so rclone subprocesses always use `--config $RCLONE_CONFIG` (prevents fallback to `~/.config/rclone/rclone.conf`). Confirmed upload-only (rclone copy/check; no deletions).

---

## 2026-03-24 — Archived models doc + registry hygiene

- **`docs/ARCHIVED-MODELS.md`:** Full inventory narrative (master + legacy + specialists, tiers, specialty breakdown); generator **`scripts/generate-archived-models-doc.py`**; env `ARCHIVER_RUN_STATE`, `ARCHIVER_MODELS_MOUNT` for optional columns.
- **`registry.yaml`:** Removed duplicate **`open-r1/OlympicCoder-32B`** row (merged into single entry).
- **Docs coherence:** Root `README.md`, `docs/README.md`, `docs/PROJECTS.md`, `docs/CONFIGURATION.md`, `docs/ARTIFACTS.md` aligned on four-part pipeline (**model-archival**, fingerprints, code-archival, gdrive-archival), D5 control-plane refs, fingerprints path **`D1/model-checksums/`**, GDrive staging vs registry mode.

---

## 2026-03-23 — Registry priorities + archiver cadence notes

- **DBRX removed** from `registry.yaml` and `registry-specialists.yaml` (unreliable on HF). Clean **`run_state.json` / `priority_overrides.json`** on VM if stale keys remain.
- **Large-model priority band:** Many ≥70B / flagship / MoE-class ids set to **`priority: 4`** in both registries; **`Salesforce/CoDA-*`**, **`apple/DiffuCoder-*`** kept at lower priorities (naming false positive fix).
- **Ops chat:** Example low-rate specialist run: `screen` + `run.sh` with **`registry-specialists.yaml`**, serial or adaptive + **`--bandwidth-cap`** as required.

---

## 2026-03-22 — Specialist registry on VM (example)

- **Example VM:** `x@192.168.8.65`; sync **`registry-specialists.yaml`** then start e.g.  
  `screen -dmS archiver bash scripts/run.sh --all --registry config/registry-specialists.yaml …`  
  (exact flags evolve — see **`vm-operations.mdc`** and live **`STATUS.md`**).

---

## 2026-03-21 — VPN / Surfshark (VM ops, not in git)

- **VM:** Prefer **one** OpenVPN path — dinit service **`openvpn-surfshark`**; avoid duplicate Surfshark services that create two `tun` devices and risky routing. Details were applied on the host under `/etc/dinit.d/` (see **`.chat/2026-03-21-surfshark-single-openvpn-vm.md`** if needed).

---

## Older / rolling

- Many single-topic notes live under **`.chat/*.md`** (GDrive upload, Graphcore tarballs, registry expansions). **Do not** require agents to read them by default; merge anything still operationally true into this file or into **`docs/OPERATIONS.md`**, **`docs/GDRIVE-UPLOAD-RUNBOOK.md`**, etc.

---

_Last curated: 2026-03-28. Append new sessions at the top (below the “Purpose” block)._
