# gh-archival

Independent CLI: list GitHub repositories you **own**, shallow-clone the **default branch** (default filter: branch name `main`), export **`tar.gz`** per repo via `git archive` (no `.git` in artifacts), write a JSON manifest, then optionally **`rclone copy`** the run folder to Google Drive or any other [rclone](https://rclone.org/) remote.

## Requirements

- Python 3.11+
- `git`
- GitHub auth: **`GITHUB_TOKEN`** (repo scope for private repos) or **`gh auth login`**
- **`rclone`** configured (`rclone config`) when uploading

## Google Drive folder for backups

Backups for this setup go under this Drive folder (sign in to open it):

[Google Drive folder — gh-archival backups](https://drive.google.com/drive/u/0/folders/1L2FSm5KW9Ypee8IMfXUkVjHvkwmVYy69)

**Folder ID:** `1L2FSm5KW9Ypee8IMfXUkVjHvkwmVYy69`

With [rclone’s Google Drive backend](https://rclone.org/drive/), you can use that ID as the path after your remote name (replace `gdrive` with whatever you chose in `rclone config`):

```bash
export GH_ARCHIVAL_RCLONE_REMOTE="gdrive:1L2FSm5KW9Ypee8IMfXUkVjHvkwmVYy69"
gh-archival run
```

Each run uploads to `…/<run-id>/` inside that folder. If your rclone build complains about the ID form, use a path from the remote root instead, or pass through a root-folder flag, e.g. `--rclone-arg=--drive-root-folder-id=1L2FSm5KW9Ypee8IMfXUkVjHvkwmVYy69` with `GH_ARCHIVAL_RCLONE_REMOTE` set to `gdrive:` (remote root).

## Install / run

From this directory:

```bash
uv sync
uv run gh-archival --help
```

Or install the package into your environment:

```bash
uv pip install -e .
gh-archival check
```

## Commands

```bash
# Verify git + token (+ rclone if installed)
gh-archival check

# Repos that would be archived (default: owned, default branch main, no forks)
gh-archival list-repos

# All owned repos regardless of default branch name
gh-archival list-repos --any-default-branch

# Full run: tarballs under ./gh-archival-output/snapshots/<run-id>/
gh-archival run --skip-rclone

# Upload into the Drive folder above (see “Google Drive folder for backups”)
export GH_ARCHIVAL_RCLONE_REMOTE="gdrive:1L2FSm5KW9Ypee8IMfXUkVjHvkwmVYy69"
gh-archival run
```

### Useful options

| Flag | Meaning |
|------|--------|
| `--work-dir PATH` | Output base (default `./gh-archival-output`) |
| `--any-default-branch` | Include repos whose default is not `main` |
| `--include-forks` | Include forks |
| `--no-include-archived` | Skip archived repos |
| `--format dir` | Shallow clones with `.git` instead of `.tar.gz` |
| `--repo user/a --repo user/b` | Only these full names |
| `--dry-run` | Print plan only |
| `--skip-rclone` | Local snapshot only |
| `--rclone-arg=--transfers=8` | Extra `rclone copy` args (repeatable) |

## Security

Cloning uses `https://x-access-token:TOKEN@github.com/...`, which can expose the token in process listings on shared machines. Prefer a dedicated machine or short-lived fine-grained PAT with **Contents: read-only** on your repos.

## Layout

```
<work-dir>/
  snapshots/
    <run-id>/
      owner__repo.tar.gz
      ...
    manifest-<run-id>.json
```

On the remote, the same `<run-id>` directory is created under `--rclone-remote` (plus optional `--rclone-path-suffix`).
