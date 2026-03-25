# Remote Activity Log

Compact operational log of actions performed by Cursor agent(s) on remote machines (SSH/VM/cloud hosts).

## 2026-03-25

### VM `x@192.168.8.65` (SSH)
- Checked active download processes and sessions (`aria2c`, `screen`, `run.sh`, `uv run archiver`).
- Pulled live status from `/mnt/models/d5/STATUS.md` and sampled `/mnt/models/d5/run_state.json`.
- Confirmed active specialist-queue download, reported current speed/ETA/completed/failed snapshot.

### Notes
- This file tracks remote-machine actions only; durable project decisions belong in `docs/AGENT_TRANSCRIPT_SUMMARY.md` and subsystem docs.
