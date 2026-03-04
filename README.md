# model-archival

Unattended offline archival of open-source LLM/LRM weights from Hugging Face.

## Quick start

```bash
# 1. Install system dependency
sudo apt install aria2

# 2. Install the project
uv sync

# 3. Edit config/drives.yaml — set the mount_point for each drive
# 4. (Optional) Set HF token for gated models
export HF_TOKEN=hf_...

# 5. Dry-run to preview what will be downloaded
uv run archiver download --all --dry-run

# 6. Start the archive (recommended: inside screen or tmux)
screen -S archiver
uv run archiver download --all
# Detach: Ctrl-A D  |  Reattach: screen -r archiver
```

`STATUS.md` is written to the current directory and updated every ~60 s.

## Commands

```
archiver download  <model-id|--tier A|B|C|D|--all>  [--dry-run] [--max-parallel-drives N]
archiver verify    <model-id|--all|--tier X|--drive dN>
archiver status    [--drive X]
archiver list      [--tier X] [--json]
archiver pin       <model-id> <commit-sha>
archiver tokens    check
archiver drives    status
archiver report    [--output STATUS.md]
```

## Project layout

```
config/
  registry.yaml       model registry — edit to add/pin models
  drives.yaml         drive mount points — edit to match your fstab

src/archiver/
  cli.py              click entry points
  models.py           ModelEntry dataclass + registry loader
  aria2_manager.py    aria2c daemon lifecycle + aria2p wrapper
  downloader.py       per-model download orchestration
  scheduler.py        priority queue + per-drive worker threads
  verifier.py         SHA-256 checksums + manifest writer
  state.py            run_state.json + archive replication
  preflight.py        pre-flight checks
  status.py           rich console display + STATUS.md writer
```

## Requirements

- Python ≥ 3.11
- `aria2c` in PATH (`sudo apt install aria2`)
- Drives mounted at the paths in `config/drives.yaml`

See `docs/REQUIREMENTS.md` for the full specification.
