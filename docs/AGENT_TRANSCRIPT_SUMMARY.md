# Agent transcript summary (canonical)

**Purpose:** Capture **durable outcomes** from AI-assisted work so agents and humans can **skip** parsing raw Cursor agent transcripts (`~/.cursor/projects/.../agent-transcripts/`). Those files are verbose, lossy for tooling, and not in-repo.

**How to use**

1. Prefer this file + [`model-archival/docs/AI_CONTEXT.md`](../model-archival/docs/AI_CONTEXT.md) + [`.cursor/rules/`](../.cursor/rules/) for bootstrap.
2. Use repo **`.chat/`** only if you need a specific session paper trail; promote anything still true into **this doc** and/or proper `docs/`.
3. After a meaningful agent session, append a **dated bullet block** below (facts, file paths, operational notes). Keep it short; link to real docs for depth.

---

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
