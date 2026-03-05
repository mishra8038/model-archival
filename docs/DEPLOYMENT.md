# Deployment Guide

Step-by-step guide to set up the model-archival environment on a fresh VM — from Proxmox HDD passthrough to running the first download.

---

## Overview

```
Proxmox host
  └── VM 106 (Debian / MX Linux  or  Artix Linux)
        ├── /dev/sda  — root SSD (256 GB, OS only, no model data)
        ├── /dev/sd*  — D1 6TB   (passthrough HDD)
        ├── /dev/sd*  — D2 3TB   (passthrough HDD)
        ├── /dev/sd*  — D3 3TB   (passthrough HDD)
        └── /dev/sd*  — D5 1TB   (passthrough HDD)
```

The root SSD is only for the OS, project code, and logs. No model weights ever touch it.

---

## Step 1 — Attach HDDs to the VM (Proxmox host)

Run on the **Proxmox host**, not inside the VM.

```bash
# Copy the script to Proxmox
scp deploy/proxmox-attach-disks.sh root@<proxmox-host>:/root/

# SSH into Proxmox host
ssh root@<proxmox-host>

# Run — it detects all available HDDs, shows details, asks for confirmation
bash /root/proxmox-attach-disks.sh
```

The script:
- Lists all physical disks by serial number, model, and capacity
- Excludes OS disk, ZFS/LVM members automatically
- Asks you to confirm each mapping before attaching
- Attaches as SCSI devices to VM 106

Verify in Proxmox UI (VM 106 → Hardware) that the disks appear.

---

## Step 2 — Install OS dependencies

SSH into the **VM** and run the appropriate setup script.

### MX Linux / Debian / Ubuntu

```bash
bash deploy/setup-mxlinux.sh
```

Installs: `aria2`, `uv`, `python3`, `screen`, `git`, `smartmontools`, `gdisk`, `rsync`, `curl`, `wget`

### Artix Linux (dinit) / Arch Linux

```bash
bash deploy/setup-artix.sh
```

Installs equivalent packages via `pacman`.

Both scripts generate a timestamped Markdown report in `deploy/`.

---

## Step 3 — Partition, format, and mount drives

Run inside the **VM**. This is destructive — it wipes all target HDDs.

```bash
# First run: wipe disks, create GPT, format ext4, mount
bash deploy/vm-mount-disks.sh --wipe

# Subsequent reboots (mounts only, no formatting):
bash deploy/vm-mount-disks.sh
```

The script:
1. Identifies passthrough disks by serial number (falling back to capacity matching)
2. Assigns each to the correct drive label (D1/D2/D3/D5)
3. `--wipe`: zeroes first 100 MB, creates GPT table, creates partition, formats ext4
4. Mounts at `/mnt/models/d1`, `/mnt/models/d2`, `/mnt/models/d3`, `/mnt/models/d5`
5. Adds entries to `/etc/fstab` for persistence across reboots
6. Creates `.tmp/` scratch directory on D1

Expected layout after mounting:

```
/mnt/models/
  d1/          6 TB  — large Tier A/B models + .tmp/
  d2/          3 TB  — mid-size Tier A/B + Tier D
  d3/          3 TB  — Tier C/D quantized GGUF
  d5/          1 TB  — metadata, logs, state, STATUS.md
```

---

## Step 4 — Install Python environment

```bash
cd /opt/model-archival   # or wherever you cloned the project
uv sync
```

`uv` creates `.venv/` and installs all Python dependencies from `uv.lock`. This takes ~30 seconds.

Verify:

```bash
uv run archiver --help
```

---

## Step 5 — Set HuggingFace token

Required for gated models (Llama, Gemma, Mistral, Phi).

```bash
bash deploy/sethfToken.sh hf_YOURTOKEN
source ~/.bashrc
```

The token is stored in `~/.hf_token` (chmod 600) and auto-exported on login.  
It is never stored in the project repository.

To get a token: see [`docs/HF-TOKEN-GUIDE.md`](HF-TOKEN-GUIDE.md)

To verify access:

```bash
uv run archiver tokens check
```

---

## Step 6 — Verify environment

```bash
bash scripts/check-environment.sh
# or directly:
bash deploy/verify-environment.sh
```

This checks:
- Required runtime tools: `python3`, `uv`, `aria2c`, `screen`
- Disk management tools (warn if missing): `smartctl`, `gdisk`, `sgdisk`, `lsblk`
- Drive mounts: presence, writability, free space for each of D1/D2/D3/D5
- HF token: set and valid
- Network: reachable to `huggingface.co`
- Registry: YAML valid, all referenced drives exist

All checks pass → safe to run downloads.

---

## Step 7 — Dry run

```bash
bash run.sh --dry-run
```

Simulates the full pipeline without downloading anything. Shows:
- What models would be downloaded
- Which drive each lands on
- Estimated sizes
- Any pre-flight issues

---

## Step 8 — Run downloads

Always run inside `screen` — downloads take days and SSH sessions drop.

```bash
screen -S archiver
bash run.sh
```

- Detach: `Ctrl+A D`
- Reattach: `screen -r archiver`

To download only token-free models first (while waiting for HF token approvals):

```bash
bash run.sh --priority-only 1
```

---

## Cursor Remote SSH fix (optional)

If Cursor IDE Remote SSH shows "Terminal sandbox could not start":

```bash
# Copy to VM:
scp deploy/fix-apparmor-cursor.sh root@<vm-ip>:/root/

# Run on VM:
bash /root/fix-apparmor-cursor.sh
```

Applies AppArmor / userns kernel parameter fixes. Safe, fully reversible.

---

## Proxmox disk discovery command (reference)

To query disk details from the Proxmox console before running the attach script:

```bash
lsblk -o NAME,SIZE,MODEL,SERIAL,TYPE,MOUNTPOINTS | grep disk
```

Or for full SMART detail on a specific disk:

```bash
smartctl -i /dev/sdX
```

---

## fstab reference

After `vm-mount-disks.sh` runs, `/etc/fstab` should have entries like:

```
UUID=<uuid-of-d1>   /mnt/models/d1   ext4   defaults,nofail   0 2
UUID=<uuid-of-d2>   /mnt/models/d2   ext4   defaults,nofail   0 2
UUID=<uuid-of-d3>   /mnt/models/d3   ext4   defaults,nofail   0 2
UUID=<uuid-of-d5>   /mnt/models/d5   ext4   defaults,nofail   0 2
```

`nofail` prevents boot failure if a drive is not present.

Verify: `mount | grep /mnt/models`

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `archiver: command not found` | Run `uv sync` first; use `uv run archiver` |
| Drive not mounted after reboot | Check fstab UUID, run `sudo mount -a` |
| `aria2c not found` | `sudo apt install aria2` |
| HF token rejected | Revoke and recreate at huggingface.co/settings/tokens; run `bash deploy/sethfToken.sh hf_NEW` |
| Download stops at 0 bytes | LFS CDN URL expired — re-run, the downloader refreshes URLs automatically |
| STATUS.md not updating | Check `/mnt/models/d5/` is writable |
| Cursor terminal sandbox error | Run `bash deploy/fix-apparmor-cursor.sh` on the VM |

For deeper issues see [`docs/OPERATIONS.md`](OPERATIONS.md).
