# Agent transcript summary (canonical)

**Purpose:** Capture **durable outcomes** from AI-assisted work so agents and humans can **skip** parsing raw Cursor agent transcripts (`~/.cursor/projects/.../agent-transcripts/`). Those files are verbose, lossy for tooling, and not in-repo.

**How to use**

1. Prefer this file + [`model-archival/docs/AI_CONTEXT.md`](../model-archival/docs/AI_CONTEXT.md) + [`.cursor/rules/`](../.cursor/rules/) for bootstrap.
2. Use repo **`.chat/`** only if you need a specific session paper trail; promote anything still true into **this doc** and/or proper `docs/`.
3. After a meaningful agent session, append a **dated bullet block** below (facts, file paths, operational notes). Keep it short; link to real docs for depth.

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

_Last curated: 2026-03-25. Append new sessions at the top (below the “Purpose” block)._
