# setup-artix — Execution Report

| Field | Value |
|-------|-------|
| Script | `setup-artix` |
| Host | a4kg3-artix-xfce |
| User | root |
| Started | 2026-03-04 17:41:54 EST |

---
| Distro | Artix Linux (Arch/pacman, dinit) |
| Repo dir | `/home/x/dev/model-archival` |


## Pre-flight Checks

  - ✔ pyproject.toml found at /home/x/dev/model-archival
  - ✔ sudo available
  - ✔ pacman available
| pyproject.toml | found |
| sudo | available |
| pacman |  |

## 1 — System Packages (pacman)

  ✓ Syncing pacman database…
  - `sudo pacman -Sy --noconfirm`
  ```
  :: Synchronizing package databases...
   system downloading...
   world downloading...
   galaxy downloading...
  ```
  - ✔ Package database synced
  ✓ Installing: python aria2 git screen rsync curl wget ca-certificates htop nvme-cli gptfdisk
**Packages:** `python aria2 git screen rsync curl wget ca-certificates htop nvme-cli gptfdisk`

  - ✔ python  (already installed — 3.14.3-1)
  - python — already installed (3.14.3-1)
  - ✔ aria2  (already installed — 1.37.0-2)
  - aria2 — already installed (1.37.0-2)
  - ✔ git  (already installed — 2.53.0-1)
  - git — already installed (2.53.0-1)
  - ✔ screen  (already installed — 5.0.1-3)
  - screen — already installed (5.0.1-3)
  - ✔ rsync  (already installed — 3.4.1-2)
  - rsync — already installed (3.4.1-2)
  - ✔ curl  (already installed — 8.18.0-3)
  - curl — already installed (8.18.0-3)
  - ✔ wget  (already installed — 1.25.0-3)
  - wget — already installed (1.25.0-3)
  - ✔ ca-certificates  (already installed — 20240618-1)
  - ca-certificates — already installed (20240618-1)
  - ✔ htop  (already installed — 3.4.1-1)
  - htop — already installed (3.4.1-1)
  - ✔ nvme-cli  (already installed — 2.16-2)
  - nvme-cli — already installed (2.16-2)
  - ✔ gptfdisk  (already installed — 1.0.10-2)
  - gptfdisk — already installed (1.0.10-2)
  ✓ Packages: 0 newly installed, 11 already present

Summary: 0 newly installed, 11 already present
  ✓ Verifying key binaries…
  - ✔ aria2c — aria2 version 1.37.0
  - `aria2c` ✔  aria2 version 1.37.0
  - ✔ python3 — Python 3.14.3
  - `python3` ✔  Python 3.14.3
  - ✔ python — Python 3.14.3
  - `python` ✔  Python 3.14.3
  - ✔ git — git version 2.53.0
  - `git` ✔  git version 2.53.0
  - ✔ screen — Screen version 5.0.1 (build on 2025-06-05 08:06:06) 
  - `screen` ✔  Screen version 5.0.1 (build on 2025-06-05 08:06:06) 
  - ✔ rsync — rsync  version 3.4.1  protocol version 32
  - `rsync` ✔  rsync  version 3.4.1  protocol version 32
  - ✔ sgdisk — GPT fdisk (sgdisk) version 1.0.10
  - `sgdisk` ✔  GPT fdisk (sgdisk) version 1.0.10

## 2 — Install uv (Python toolchain manager)

  ✓ uv already installed: uv 0.10.7 (08ab1a344 2026-02-27)
  - ✔ uv uv 0.10.7 (08ab1a344 2026-02-27)
uv already installed: `uv 0.10.7 (08ab1a344 2026-02-27)`

**PATH persistence:**

## 3 — Python 3.11 Virtual Environment (uv)

  ✓ Changing to repo directory: /home/x/dev/model-archival
  ✓ Pinning Python 3.11…
  - `uv python pin 3.11`
  ```
  Downloading cpython-3.11.14-linux-x86_64-gnu (download) (29.8MiB)
   Downloaded cpython-3.11.14-linux-x86_64-gnu (download)
  Pinned `.python-version` to `3.11`
  ```
  ✓ Syncing virtual environment (uv sync)…
  - `uv sync`
  - ✔ Virtual environment ready — Python 3.11.14

- Venv path: `/home/x/dev/model-archival/.venv`
- Python: `Python 3.11.14`

## 4 — CLI Smoke Tests

  ✓ Testing archiver --help…
  - ✔ archiver --help returned output
**archiver --help (first 8 lines):**
```
Usage: archiver [OPTIONS] COMMAND [ARGS]...

  Model archival tool — download, verify, and manage LLM weight archives.

Options:
  -r, --registry PATH  Path to registry.yaml  [default: config/registry.yaml]
  --drives PATH        Path to drives.yaml  [default: config/drives.yaml]
  -v, --verbose        Enable debug logging
```
  ✓ Testing registry list (drives not mounted yet — non-fatal)…

**archiver list --tier A (first 6 lines):**
```
                                             Model Registry                                             
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━┳━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ ID                                        ┃ Tier ┃ Dri… ┃ P  ┃ Auth  ┃ Licence          ┃ Commit SHA ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━╇━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ deepseek-ai/DeepSeek-V3                   │ A    │ D1   │ 1  │ no    │ MIT              │ —          │
│ deepseek-ai/DeepSeek-R1                   │ A    │ D1   │ 1  │ no    │ MIT              │ —          │
```
  - ✔ Registry list executed

## 5 — Mount Point Directories

  ✓ Creating /mnt/models/dN directories…
| Directory | Created | Owner |
|-----------|---------|-------|
  - ✔ /mnt/models/d1 — already exists
| `/mnt/models/d1` | already exists | root:root |
  - ✔ /mnt/models/d2 — already exists
| `/mnt/models/d2` | already exists | root:root |
  - ✔ /mnt/models/d3 — already exists
| `/mnt/models/d3` | already exists | root:root |
  - ✔ /mnt/models/d5 — already exists
| `/mnt/models/d5` | already exists | root:root |

## 6 — Shell Alias (archiver-screen)

Alias: `alias archiver-screen='cd /home/x/dev/model-archival && screen -S archiver uv run archiver'`


## Setup Complete

| Component | Version |
|-----------|---------|
| uv | uv 0.10.7 (08ab1a344 2026-02-27) |
| Python | Python 3.11.14 |
| aria2c | aria2 version 1.37.0 |
| Repo | `/home/x/dev/model-archival` |

---

## Result: SUCCESS

Completed: 2026-03-04 17:41:58 EST
