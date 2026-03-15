# Upload selection logic

With a **3 TB** GDrive budget, uploads can be chosen in two ways.

## 1. Explicit list (default)

Set `model_ids_gguf` and `model_ids_full` in `config.yaml`. You control exactly what is backed up. Good when you want a fixed, reviewed set.

## 2. Budget-based selection (recommended for 3 TB)

Set `upload_selection` in `config.yaml`. The backup script will:

- **Source of truth:** Registry (`registry.yaml`) + archiver run state (`run_state.json` on D5). Only models that are **complete** and have a known size are considered.
- **Drives:** Restrict to `d2` and `d3` (mid-size and GGUF; D1 giants stay local).
- **Per-model cap:** Skip any single model larger than `max_per_model_gb` (e.g. 200 GB) so one 400 GB model doesn’t dominate.
- **Total budget:** Add models in priority order until total size would exceed `max_total_gb` (e.g. 3000).
- **Ordering:** Prefer higher priority (tier A before B before C…, priority 1 before 2), then smaller models first so more models fit within the cap.

Result: as many D2/D3 models as fit in 3 TB, with no single model over the per-model limit. GGUF vs full is inferred from registry (tier C = GGUF; tier D with "GGUF" in id = GGUF; rest = full).

## Config example

```yaml
# Optional: replace fixed model_ids_gguf / model_ids_full with budget-based selection
upload_selection:
  run_state_path: /mnt/models/d5/run_state.json   # archiver run state (has total_bytes per model)
  drives: [d2, d3]
  max_total_gb: 3000
  max_per_model_gb: 200
```

If `upload_selection` is set, `model_ids_gguf` and `model_ids_full` are ignored for the backup list (they can still be present). To see what would be uploaded without running rclone, use:

```bash
python3 backup.py list-candidates
```
