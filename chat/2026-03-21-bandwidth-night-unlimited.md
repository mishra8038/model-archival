# Bandwidth: daytime cap, late-night unlimited

- **Semantics** (already in `aria2_manager.BandwidthSchedule`): cap applies **inside** `--scheduled-bandwidth-window`; **outside** that interval aria2 limit is cleared (unlimited).
- **`model-archival/scripts/run.sh` defaults**: `SCHEDULED_BANDWIDTH_CAP=0.75`, `SCHEDULED_BANDWIDTH_WINDOW=07:00-23:00` → ~6 Mbps **07:00–23:00 local**, **unlimited 23:00–07:00**. `BANDWIDTH_CAP` default empty (schedule used). `--bandwidth-cap N` still forces 24/7 cap; `--no-scheduled-bandwidth-cap` clears both schedule fields.
- **`aria2_manager.py`**: docstring on `BandwidthSchedule` updated to describe day/night usage.
- **VM**: `run.sh` redeployed; archiver restarted with specialist registry; live cmd shows `--scheduled-bandwidth-cap 0.75 --scheduled-bandwidth-window 07:00-23:00` (no `--bandwidth-cap`).
