# Context snapshot (`.dump/`)

This folder holds **user-maintained** context snapshots so a new chat can reload *intent and state* without relying on Cursor transcript history.

## Files

| File | Role |
|------|------|
| **`CONTEXT_SNAPSHOT.md`** | Living handoff: edit before ending a session or when milestones change. |
| **`YYYY-MM-DD-context.md`** | Optional dated freeze; copy from the template or from `CONTEXT_SNAPSHOT.md` when you want a named checkpoint. |

## How to use

1. Fill in **`CONTEXT_SNAPSHOT.md`** (keep it short: goal, decisions, paths, next step).
2. In the next session: **`@.dump/CONTEXT_SNAPSHOT.md`** (or a dated file) and say you want to continue from that snapshot.
3. Do **not** put secrets here (tokens, keys). Use path references and “see `~/.hf_token`” style hints.

Cursor rules: **`.cursor/rules/context-snapshot.mdc`** (workspace) and global **`chat-context-and-transcripts.mdc`** (context snapshot section).
