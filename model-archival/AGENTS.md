# Agents / AI assistants

**Bootstrap file:** Read [`docs/AI_CONTEXT.md`](docs/AI_CONTEXT.md) first — compact map of modules, paths, invariants, and commands. It points to deeper docs only when needed.

**Session history (ignore `~/.cursor/.../agent-transcripts/`):** [`docs/AGENT_TRANSCRIPT_SUMMARY.md`](../../docs/AGENT_TRANSCRIPT_SUMMARY.md) at repo root.

**Cursor rules:** Repository `.cursor/rules/` (`archiver-codebase.mdc`, `vm-operations.mdc`, `model-archival-project.mdc`).

**Orchestrator:** `scripts/run.sh` · **Stop before reboot:** `scripts/stop.sh`

**LTFS / tape vault (plans, PAR2 policy, inventory snapshot):** [`tape-archive/`](tape-archive/) — regenerate plan with `python3 tape-archive/scripts/build_tape_allocation.py --write` (reads `config/registry.yaml` for tiers).
