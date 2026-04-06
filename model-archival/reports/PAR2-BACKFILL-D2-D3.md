# PAR2 backfill on D2 and D3

Per-revision **`par2 create`** under each model tree’s **`.parity/`** directory (same layout as `integrity_tools/parity_cli.py`: main file named `{revision}.par2`).

## Requirements

- **`par2`** from [par2cmdline](https://github.com/Parchive/par2cmdline) on the machine that holds the disks (e.g. `sudo pacman -S par2cmdline` on Artix). The batch script also looks for **`~/.local/bin/par2`** if the user built from source without sudo.
- **CLI note:** par2cmdline expects **`par2 c`** (create) with **`-B<revision_dir>`** and source paths **relative** to that directory. The backfill script and `integrity_tools/parity_cli.py` follow this.
- Enough free space on **D2** and **D3** for recovery files (default **5%** redundancy × **1.2** fudge + **64 MiB** per tree, plus **`--reserve-gib`** headroom left on each drive).

## Run (archive VM)

From a checkout that includes `model-archival/model-archival/scripts/`:

```bash
# Plan only (no par2 required if you only inspect; script still checks par2 unless --dry-run)
python3 model-archival/scripts/par2_backfill_d2_d3.py --dry-run

# Execute (default mounts)
python3 model-archival/scripts/par2_backfill_d2_d3.py

# Tune redundancy / ordering
python3 model-archival/scripts/par2_backfill_d2_d3.py --redundancy-pct 5 --sort smallest-first --reserve-gib 2
```

Paths default to **`/mnt/models/d2`** and **`/mnt/models/d3`**. Override with **`--d2`** / **`--d3`** if needed.

## Behaviour

- Discovers revision dirs under **`raw/`**, **`quantized/`**, **`uncensored/`**, and **`specialist/`** (revision = **`main`** or **40-hex** directory name; skips symlink-only children).
- Only files **≥ `--min-size-mb`** (default 32) are protected (same idea as `parity_cli`).
- Skips trees that already have **`.parity/{revision}.par2`**.
- **Per model:** if estimated parity + reserve does not fit current free space, that revision is **`skipped_insufficient_space`**; smaller revisions may still be processed later (**`smallest-first`** default).
- **Abandon drive:** after a **`par2` failure** (partial **`.parity/`** removed) or if free space drops **below reserve** after a successful create, no further work is queued on that drive (remaining rows **`skipped_drive_abandoned`**).

## Reports

Each run writes under **`model-archival/reports/`**:

- **`PAR2-D2-D3-RUN-<UTC>.md`** — human table + summary counts  
- **`PAR2-D2-D3-RUN-<UTC>.json`** — machine-readable  
- **`PAR2-D2-D3-LATEST.md`** — pointer to the last run’s files  

PAR2 does **not** replace **`manifest.json`** / **`.sha256`** sidecars; it adds **local repair** capability for minor corruption.

## See also

- [PAR2-STORAGE-ESTIMATE-D1-D2-D3.md](PAR2-STORAGE-ESTIMATE-D1-D2-D3.md) — fleet headroom math  
- `integrity_tools/parity_cli.py` — single-tree create/verify/repair  
