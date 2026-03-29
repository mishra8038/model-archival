# AI_CONTEXT — compact project map (read this first)

**Purpose:** Give agents enough signal to work without walking the whole tree. For narrative detail use `PROJECT_PROMPT.md`; for pipelines use `ARCHITECTURE.md`; for day-2 ops use `OPERATIONS.md`. **Live VM facts:** `.cursor/rules/vm-operations.mdc` (IP, paths, disks, VPN).

**Agent session outcomes (skip raw transcripts):** repo root [`docs/AGENT_TRANSCRIPT_SUMMARY.md`](../../docs/AGENT_TRANSCRIPT_SUMMARY.md) — curated changelog; do not depend on `~/.cursor/.../agent-transcripts/`.

---

## What this repo is

Python CLI + bash orchestration that downloads Hugging Face model weights to **mounted data drives**, verifies SHA-256, writes manifests/provenance, and runs **unattended** (typically `screen`). Everything is **resumable**; archiver state/logs/archive live on **D3**; **D5** only stores finished models when the registry assigns `drive: d5`.

**Monorepo note:** This directory (`model-archival/`) is the **archiver**; siblings under the repo root include `fingerprints/`, `code-archival/`, `gdrive-archival/`. See repo `docs/PROJECTS.md` for the full map.

---

## Paths (inside `model-archival/`)

| Path | Role |
|------|------|
| `scripts/run.sh` | **Start here** — env check, `uv run archiver download`, verify, report |
| `scripts/stop.sh` | Graceful stop before reboot |
| `config/registry.yaml` | Master model list |
| `config/registry-legacy.yaml` | Opt-in legacy models |
| `config/registry-specialists.yaml` | Specialist queue |
| `config/drives.yaml` | Mount points, roles, tmp overrides |
| `src/archiver/` | All Python modules (package `archiver`) |
| `deploy/` | VM setup, token helper, mount scripts |

**On disk (runtime):** `d3/run_state.json`, `d3/STATUS.md`, `d3/logs/`, `d3/archive/` (replicated to d1/d2 `archive/`); scratch **`d1/.tmp/`** then **`d3/.tmp`** — never D5 for infra or partials; D5 only for completed `drive: d5` model trees — never root SSD for weights.

---

## Module → responsibility (1 line each)

| Module | Responsibility |
|--------|----------------|
| `cli.py` | Click commands; builds `Aria2Manager`, `Downloader`, `DriveScheduler`; bandwidth cap / schedule |
| `scheduler.py` | Worker pool or serial; pick next model (priority + `priority_overrides.json`); signals |
| `downloader.py` | LFS → aria2 + fresh `hf_hub_url`; XET/small → `hf_hub_download`; manifest/sidecars |
| `aria2_manager.py` | aria2c RPC daemon; global bandwidth cap; orphan partial + `.aria2` handling |
| `models.py` | `ModelEntry`, `Registry`, YAML load/save, `model_dir` |
| `state.py` | `run_state.json` atomic writes, thread-safe |
| `status.py` | Rich UI, `STATUS.md`, run report hooks |
| `verifier.py` | SHA-256, `manifest.json`, `global_index.jsonl`, descriptors |
| `preflight.py` | Drives, tools, HF token checks |

---

## Invariants (do not “optimize” away)

1. **Resumable:** Do not delete in-progress `.tmp` data or `.aria2` control files to “clean up”.
2. **Reboot:** `stop.sh` before reboot (fsck risk on data drives otherwise).
3. **LFS URLs:** Re-resolve with `hf_hub_url()` before each attempt (~1h CDN expiry).
4. **SHA mismatch:** Remove corrupt file **and** its `.aria2`, then retry.
5. **Gated models:** 401/403 → no blind retry spiral (`AuthError`).
6. **Bandwidth cap:** Approximate aggregate target; LFS via aria2 global limit; flat `--bandwidth-cap` disables scheduled day/night in `run.sh` reporting/args as implemented.

---

## Commands (cheat sheet)

```bash
# From repo root of this subproject (where pyproject.toml lives):
bash scripts/run.sh --all [--registry config/registry-specialists.yaml] [--drive d3] [--bandwidth-cap 2] [--queue-mode adaptive|serial]

bash scripts/stop.sh

uv run archiver download --all --dry-run
uv run archiver status | verify | list | drives | tokens check | report
```

HF token: `deploy/sethfToken.sh` → `~/.hf_token`.

---

## Context compaction for other tools

| Tool / pattern | Suggestion |
|----------------|------------|
| **Cursor** | `@model-archival/docs/AI_CONTEXT.md` or `@AGENTS.md` in chat; rules already under `.cursor/rules/`; global rules in `~/.cursor/rules` (see **chat-context-and-transcripts** / **meta-interactions**). |
| **Aider** | `/read model-archival/docs/AI_CONTEXT.md` (or copy path) before large tasks; add `ARCHITECTURE.md` when changing download/state. |
| **Cline** | Add `AI_CONTEXT.md` (or this paragraph) to workspace / rules / “project context” if the UI supports it. |
| **Humans** | Keep this file ≤ ~250 lines; link out instead of pasting registry lists — use `docs/ARCHIVED-MODELS.md` for inventory. Session notes: **`.chat/`** (ignored from index via repo `.cursorignore`). |

---

## Related docs (deeper, not duplicate)

- Repo root `docs/AGENT_TRANSCRIPT_SUMMARY.md` — curated agent-session facts (ignore Cursor transcript JSONL)
- `PROJECT_PROMPT.md` — mission, tiers, priorities, environment narrative  
- `ARCHITECTURE.md` — LFS vs XET, data flow, idempotency layers  
- `OPERATIONS.md` — runbooks  
- `HF-TOKEN-GUIDE.md` — gated access  
- `REQUIREMENTS.md` — large requirement / model matrix  
- Repo root `docs/ARCHIVED-MODELS.md` — consolidated inventory  

_Last curated for agent bootstrap; extend sparingly._
