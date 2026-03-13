## Integrity tools

This folder contains small, standalone helpers for detecting and repairing
bit-level corruption in archived model files. They are intentionally
independent of the main `archiver` CLI so they can be used ad‑hoc on any
directory tree.

### 1. Chunked SHA-256 hashes

`chunk_hashes.py` generates per-chunk SHA-256 manifests for large files and
verifies them later. This lets you detect *where* a file is damaged, not just
that its top-level hash changed.

- **Generate manifests** (default: 8 MiB chunks, files ≥32 MiB):

```bash
uv run python -m integrity_tools.chunk_hashes hash /mnt/models/d1/org/ModelName
```

- **Verify against manifests**:

```bash
uv run python -m integrity_tools.chunk_hashes verify /mnt/models/d1/org/ModelName
```

Each large file gets a sidecar next to it, e.g.:

- `model.safetensors.sha256chunks.json`

The manifest records:

- full-file SHA-256
- fixed chunk size
- per-chunk SHA-256 list

### 2. PAR2 parity for local repair

`parity_cli.py` wraps `par2` (par2cmdline) to generate parity data for a model
directory, and to verify/repair later when corruption is detected.

You will need `par2` installed on the VM, e.g.:

```bash
sudo pacman -S par2cmdline
```

- **Create parity** for a model directory (default: 10% redundancy, files ≥32 MiB):

```bash
uv run python -m integrity_tools.parity_cli create /mnt/models/d1/org/ModelName
```

This writes a `.parity/` subdirectory under the model directory containing the
PAR2 set (around 10–15% overhead depending on settings).

To store parity trees on a different drive, pass a `--parity-root`:

```bash
uv run python -m integrity_tools.parity_cli create \
  /mnt/models/d1/org/ModelName \
  --parity-root /mnt/models/d5/parity \
  --redundancy-pct 12
```

The tool mirrors the model directory layout under `parity-root` so you can keep
parity data on D5 or another disk.

- **Verify an existing parity set**:

```bash
uv run python -m integrity_tools.parity_cli verify /mnt/models/d1/org/ModelName
```

- **Attempt repair using parity**:

```bash
uv run python -m integrity_tools.parity_cli repair /mnt/models/d1/org/ModelName
```

### Notes and future integration

- These tools do not currently talk to `run_state.json` or `STATUS.md` — they
  are low-level primitives for scrubbing and healing individual model trees.
- A future step would be an `archiver scrub` subcommand that:
  - walks all models from `registry.yaml`
  - uses the existing `manifest.json` + `.sha256` sidecars for detection
  - optionally leverages chunk manifests + PAR2 to localise and repair minor
    damage before falling back to full redownload.

