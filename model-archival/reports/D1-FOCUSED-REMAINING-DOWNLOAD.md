# D1 focused registry — remaining download requirement

**Focused registry:** [`../config/registry-d1-manifest-incomplete.yaml`](../config/registry-d1-manifest-incomplete.yaml)  
**(narrow / resume list for `drive: d1` incomplete work)**

After prune candidates were removed from the main registry and disk, this file lists **only** the D1 models still targeted for a **narrow** archiver run (`-r registry-d1-manifest-incomplete.yaml`).

## Current ids (3)

| `id` | `requires_auth` | Notes (from narrow file) |
|------|-----------------|---------------------------|
| `IntervitensInc/internlm2_5-20b-llamafied` | no | — |
| `meta-llama/Llama-3.3-70B-Instruct` | yes | Gated (llama3.3); resume partial tree |
| `deepseek-ai/DeepSeek-V3-0324` | no | Older V3 checkpoint; legacy policy in notes |

## Expected disk to **finish** incomplete downloads (HF estimate)

Source: last on-host evaluation table in [`D1-INCOMPLETE-EVAL.md`](D1-INCOMPLETE-EVAL.md) (same methodology as `evaluate_d1_incomplete.py`: HF file-set sizes minus bytes under resolved revision dir, sibling revs, and `d1/.tmp/<slug>/`).

| Model | Remaining (GiB) | HF total (GiB) | Comment |
|-------|----------------:|---------------:|---------|
| `IntervitensInc/internlm2_5-20b-llamafied` | **0.00** | 37.00 | Treat as **complete** for download planning; archiver may still reconcile manifests. |
| `meta-llama/Llama-3.3-70B-Instruct` | **16.43** | 262.87 | Needs HF access + licence. |
| `deepseek-ai/DeepSeek-V3-0324` | **106.10** | 641.31 | Largest remaining slice in this list. |

**Sum (meaningful remaining):** **16.43 + 106.10 ≈ 122.5 GiB** (binary GiB, 1024³).

**If you insist on summing the table literally (including InternLM):** **0.00 + 16.43 + 106.10 ≈ 122.5 GiB** — unchanged.

## Planning headroom (not in the 122.5 GiB figure)

- **`d1/.tmp` scratch:** concurrent shards and aria2 need **extra free space** beyond “bytes left to fetch” (often **tens of GiB** minimum on a busy run; more if multiple models or large shards).
- **XET / hub cache:** eval footnote — partials outside counted paths can shift real usage slightly.
- **Default `run.sh` cap:** `--max-model-download-gib` (e.g. 80) would **defer** `deepseek-ai/DeepSeek-V3-0324` (HF total **641 GiB**). The focused wrapper below uses **`--no-max-model-download`**.

## Start archiver (only these three on D1, 4 MB/s cap)

From the **`model-archival/`** repo root on the archive VM (where `config/` and `scripts/` live):

```bash
bash scripts/run-d1-focused-incomplete.sh
```

Preview without downloading:

```bash
bash scripts/run-d1-focused-incomplete.sh --dry-run
```

What the wrapper passes through **`scripts/run.sh`**:

| Flag | Purpose |
|------|---------|
| `--registry config/registry-d1-manifest-incomplete.yaml` | Only the three ids above |
| `--drive d1` | Only rows with `drive: d1` (all three) |
| `--bandwidth-cap 4` | Flat **4 MB/s** total cap in aria2 (24/7; clears day/night schedule) |
| `--no-max-model-download` | Allow **DeepSeek-V3-0324** despite default 80 GiB checkpoint gate |
| `--queue-mode serial` / `--max-parallel 1` / `--max-per-drive 1` | One active model on D1 at a time |

**HF token + Llama licence** are required for **`meta-llama/Llama-3.3-70B-Instruct`**.

**After** all three are finished and post-run verify is clean, run PAR2 if desired (see [`PAR2-BACKFILL-D2-D3.md`](PAR2-BACKFILL-D2-D3.md) / `scripts/par2-verify-then-backfill-all-drives.sh`) — do **not** start fleet-wide PAR2 until this download pass is done if you want parity only after completion.

## Refresh

On the archive VM with D1 mounted:

```bash
cd /path/to/model-archival/model-archival
uv run python scripts/evaluate_d1_incomplete.py
```

That regenerates [`D1-INCOMPLETE-EVAL.md`](D1-INCOMPLETE-EVAL.md) and replaces the numbers above if disk/HF state changed.

## Contrast: old narrow list before prunes

The same eval doc previously reported **~7349 GiB** remaining for **narrow ∩ incomplete** across **many** ids. Removing pruned candidates from the registry and narrowing this file to **three** ids collapses outstanding **estimated** payload to **~122.5 GiB** for the focused list.
