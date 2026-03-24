# Upload selection logic

**Primary upload path today:** use **`upload_staging`** on D3/D5 and `backup-staging` / `run-staging.sh` (see `README.md`). The sections below apply when you enable **budget-based `upload_selection`** in `config.yaml` again.

With a **3 TB** GDrive budget, uploads can be chosen in two ways.

## 1. Explicit list

Set `model_ids_gguf` and `model_ids_full` in `config.yaml` and **remove** or comment out `upload_selection`. You control exactly what is backed up. Good when you want a fixed, reviewed set.

## 2. Budget-based selection (default in repo `config.yaml`)

Set `upload_selection` in `config.yaml`. The backup script will:

- **Source of truth:** Registry (`registry.yaml`) + archiver run state (`run_state.json` on D5). Only models that are **complete** and have a known size are considered.
- **Drives:** Typically `d2`, `d3`, and **`d5`** — mid-size raw, GGUF, and any overflow/metadata-adjacent models on D5. **D1 giants stay local** unless you add `d1` explicitly (not recommended for the default 3 TB budget).
- **Per-model cap:** Skip any single model larger than `max_per_model_gb` (e.g. 200 GB) so one 400 GB model doesn’t dominate.
- **Total budget:** Add models in sort order until total size would exceed `max_total_gb` (e.g. 3000).
- **Ordering (GDrive urgency):** Models are sorted by an **urgency rank** (lower = uploaded sooner), then tier (A→G), registry `priority`, then **smaller size first** so more models fit in the cap.

### Urgency ranks

| Rank | Meaning |
|------|--------|
| **0** | `gdrive_urgency: critical` / `high` / `first` on the registry entry, **or** `notes` (plus id/repo text) matches disappearance-risk heuristics (e.g. takedown/DMCA/rehost/at risk/preservation priority). |
| **1** | **Uncensored / abliterated track:** registry **tier D**, **or** tier **F** / **G** (vision / experimental niche), **or** id/notes match common uncensored-community patterns (e.g. ablitr, uncensor, dolphin, mlabonne, tensorblock, huihui, …). |
| **2** | **Hostable:** tier **C** (GGUF), **or** registry `priority: 2` (smallest self-hostable quants in our policy), **or** on-disk size ≤ **50 GB** (single-GPU-friendly heuristic). |
| **3** | Everything else (then tier + priority + size as above). |

Optional per-model override in `registry.yaml`:

```yaml
- id: some-org/Fragile-Mirror
  gdrive_urgency: high   # or critical / first — forces rank 0
  ...
```

Result: the 3 TB budget preferentially backs up **hostable** weights, **uncensored/abliterated** and **niche SME** lines, and anything you mark or note as **high disappearance risk**, before larger generic checkpoints.

GGUF vs full is inferred from registry (tier C = GGUF; tier D with "GGUF" in id = GGUF; rest = full).

## D5 metadata tree

`extra_paths` includes **`/mnt/models/d5` → `extra/d5`** on Drive (full D5 mirror: `archive/`, `logs/`, `run_state.json`, `STATUS.md`, `code-archives/`, overflow models, etc.). **`d5/.tmp` is excluded** so scratch/partial data is not uploaded.

## Config example

```yaml
upload_selection:
  run_state_path: /mnt/models/d5/run_state.json
  drives: [d2, d3, d5]
  max_total_gb: 3000
  max_per_model_gb: 200
```

If `upload_selection` is set, `model_ids_gguf` and `model_ids_full` are ignored for the backup list (they can still be present). To see what would be uploaded without running rclone, use:

```bash
python3 backup.py list-candidates
```
