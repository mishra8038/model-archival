# Agents / AI assistants

**Bootstrap file:** Read [`docs/AI_CONTEXT.md`](docs/AI_CONTEXT.md) first — compact map of modules, paths, invariants, and commands. It points to deeper docs only when needed.

**Session history (ignore `~/.cursor/.../agent-transcripts/`):** [`docs/AGENT_TRANSCRIPT_SUMMARY.md`](../../docs/AGENT_TRANSCRIPT_SUMMARY.md) at repo root.

**Cursor rules:** Repository `.cursor/rules/` (`archiver-codebase.mdc`, `vm-operations.mdc`, `model-archival-project.mdc`).

**Orchestrator:** `scripts/run.sh` · **Stop before reboot:** `scripts/stop.sh`

**LTFS / tape vault:** moved to **`/home/x/z/ai/ai-model-backup-tape/`** (see `tape-archive/README.md` here for the pointer). **Run on `dp75k-mxl`** with local **`/mnt/d1`–`/mnt/d3`** and **`/dev/sg1`**. This repo still owns **`config/registry.yaml`** (tiers, HF list); the tape project symlinks it for planners. Numbered tape plan and workstation model inventories live under the tape repo’s `plans/` and `inventories/`.
