# Tape workflows moved

All LTFS scripts, cartridge registry, PAR2 policy, reports, and tape planning tools now live in a **separate repository** so tape scope stays deliberate and decoupled from the day-to-day archiver tree:

**`/home/x/z/ai/ai-model-backup-tape/`**

- Scripts and LTFS helpers: `tape-archive/scripts/`
- Physical media log: `tape-archive/config/tape_media_registry.yaml`
- Workstation disk inventories: `inventories/` and `docs/WORKSTATION-DISK-LAYOUT-*.md`
- Numbered tape plan: `plans/TAPES-MASTER-PLAN.md`

Run writers and planners **on `dp75k-mxl`** (local `/mnt/d1`–`/mnt/d3`, `/dev/sg1`), not on the SSH archival VM.
