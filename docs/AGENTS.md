---
description: Monorepo agent entrypoint — directs agents to per-subproject bootstraps and context-compaction docs.
alwaysApply: true
---


# Monorepo agents (read this first)

## Context compaction (default)

- Prefer **`docs/AGENT_TRANSCRIPT_SUMMARY.md`** and subproject `docs/AI_CONTEXT.md` / `AGENTS.md` over raw transcripts and `.chat/`.
- Session scratch: **`.chat/`** (ignored by `.cursorignore`).

## Subprojects (each has its own `AGENTS.md` or `README.md`)

- **`model-archival/`** — model weight archiver (downloads + verify + manifests). Start at `model-archival/AGENTS.md`.
- **`gdrive-archival/`** — Google Drive uploader (upload-only). Start at `gdrive-archival/AGENTS.md`.
- **`fingerprints/`** — checksum/fingerprint harvester. Start at `fingerprints/AGENTS.md`.
- **`code-archival/`** — source/code snapshotter. Start at `code-archival/AGENTS.md`.
- **`gh-archival/`** — snapshot GitHub repos you own (`main` by default) and upload via rclone. Start at `gh-archival/README.md`.
- **`ollama-hosting/`** — Supermicro Ollama rig mirror + `ollama-sync.sh` (VM archive), inventory, prune planner. Start at `ollama-hosting/README.md`. Repo-level overview: `docs/SUPERMICRO.md`.
- **`vllm-hosting/`** — Hugging Face downloads for vLLM (deduped queue, `d5/vllm` on archive VM). Start at `vllm-hosting/README.md` / `vllm-hosting/docs/VLLM-ARCHIVE.md`.
- **`full-stack/`** — full-stack archive utility. Start at `full-stack/AGENTS.md`.
- **`integrity_tools/`** — misc integrity helpers. Start at `integrity_tools/AGENTS.md`.

**Whole-monorepo prompt + requirements:** `docs/PROJECT-PROMPT-AND-REQUIREMENTS.md`.

## Remote activity logs (remote-first)

When operating on a remote machine: write to remote `docs/remote/REMOTE_ACTIVITY_LOG.md` first, then sync into this repo under `docs/remote/REMOTE_ACTIVITY_LOG.<host>.md`.

