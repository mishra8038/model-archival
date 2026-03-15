# Deployment Guide

Step-by-step guide to set up the model-archival environment on a fresh VM — from Proxmox HDD passthrough to running the first download.

---

## Overview

```
Proxmox host
  └── VM (Artix Linux / dinit  or  Debian / MX Linux)
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
scp local/deploy/proxmox-attach-disks.sh root@<proxmox-host>:/root/

# SSH into Proxmox host
ssh root@<proxmox-host>

# Run — detects all available HDDs, shows details, asks for confirmation
bash /root/proxmox-attach-disks.sh
```

The script:
- Lists all physical disks by serial number, model, and capacity
- Excludes OS disk, ZFS/LVM members automatically
- Asks you to confirm each mapping before attaching
- Attaches as SCSI devices to the VM

Verify in Proxmox UI (VM → Hardware) that the disks appear.

---

## Step 2 — Install OS dependencies

SSH into the **VM** and run the appropriate setup script.

<<<<<<< HEAD:local/docs/DEPLOYMENT.md
### MX Linux / Debian / Ubuntu

```bash
cd /opt/model-archival/local
bash deploy/setup-mxlinux.sh
```

Installs: `aria2`, `uv`, `python3`, `screen`, `git`, `smartmontools`, `gdisk`, `rsync`, `curl`, `wget`

=======
>>>>>>> 31a9d82 (refinements. bug fixes.):docs/DEPLOYMENT.md
### Artix Linux (dinit) / Arch Linux

```bash
cd /opt/model-archival/local
bash deploy/setup-artix.sh
```

Installs: `aria2`, `uv`, `python3`, `screen`, `git`, `smartmontools`, `gdisk`, `rsync`, `curl`, `openvpn`

### MX Linux / Debian / Ubuntu

```bash
bash deploy/setup-mxlinux.sh
```

Installs equivalent packages via `apt`.

Both scripts generate a timestamped Markdown report in `deploy/`.

---

## Step 3 — Partition, format, and mount drives

Run inside the **VM**. The `--wipe` flag is destructive — it zeroes and reformats all target HDDs.

```bash
# First run: wipe disks, create GPT, format ext4, mount
sudo bash deploy/vm-mount-disks.sh --wipe

# Subsequent reboots (mounts only, no formatting):
sudo bash deploy/vm-mount-disks.sh
```

The script:
1. Identifies passthrough disks by serial number (falls back to capacity matching)
2. Assigns each to the correct drive label (D1/D2/D3/D5)
3. `--wipe`: zeroes first/last 10 MB, creates GPT table, creates partition 1, formats ext4 with `noatime`
4. Mounts at `/mnt/models/d1`, `/mnt/models/d2`, `/mnt/models/d3`, `/mnt/models/d5`
5. Adds entries to `/etc/fstab` (UUID-based, `nofail`) for persistence across reboots
6. Creates `D1/.tmp/` scratch directory for in-progress downloads

Expected layout after mounting:

```
/mnt/models/
  d1/   6 TB  — large Tier A/B models + .tmp/ (scratch for downloads in progress)
  d2/   3 TB  — mid-size Tier A/B + Tier D uncensored
  d3/   3 TB  — Tier C/D quantized GGUF
  d5/   1 TB  — metadata, logs, state, STATUS.md
```

---

## Step 4 — Install Python environment

```bash
<<<<<<< HEAD:local/docs/DEPLOYMENT.md
cd /opt/model-archival/local   # or wherever you cloned the project
=======
cd /home/x/dev/model-archival   # or wherever you cloned the project
>>>>>>> 31a9d82 (refinements. bug fixes.):docs/DEPLOYMENT.md
uv sync
```

`uv` creates `.venv/` and installs all Python dependencies from `uv.lock`. Takes ~30 seconds.

Verify:

```bash
uv run archiver --help
```

---

## Step 5 — Set HuggingFace token

Required for gated models (Llama, Gemma, Mistral, Command-R+, Phi-4).

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

## Step 6 — Set up VPN (recommended)

ISPs commonly throttle HuggingFace downloads. Using a VPN bypasses this throttling. The setup below uses Surfshark with OpenVPN; any VPN provider with `.ovpn` configs works the same way.

### Get OpenVPN credentials from your VPN provider

For Surfshark: log in at [my.surfshark.com](https://my.surfshark.com/vpn/manual-setup/main), go to **Credentials** tab, and copy the **Service username** and **Service password** (these are different from your account login).

### Download server configs and configure auth

```bash
# Download all server configs
cd /etc/openvpn/client
sudo curl -Lo surfshark-configs.zip "https://my.surfshark.com/vpn/api/v1/server/configurations"

# Extract (unzip may not be installed — use Python)
sudo python3 -c "
import zipfile
z = zipfile.ZipFile('/etc/openvpn/client/surfshark-configs.zip')
z.extractall('/etc/openvpn/client/surfshark/')
print(f'Extracted {len(z.namelist())} configs')
"

# Create auth file with your VPN service credentials
sudo bash -c 'cat > /etc/openvpn/client/surfshark.auth << EOF
YOUR_SERVICE_USERNAME
YOUR_SERVICE_PASSWORD
EOF'
sudo chmod 600 /etc/openvpn/client/surfshark.auth
```

### Connect and verify

Pick a server close to you for lower latency and better bandwidth. Configs live in `/etc/openvpn/client/surfshark/`.

| Location        | Config file (UDP)        | Use case              |
|----------------|--------------------------|------------------------|
| **US East (NYC)** | `us-nyc.prod.surfshark.com_udp.ovpn` | NYC / US Northeast     |
| US East alt.   | `us-bos`, `us-ash`       | Boston, Ashburn DC     |
| **EU (e.g. VM)**  | `nl-ams.prod.surfshark.com_udp.ovpn` | Amsterdam; or `de-fra`, `uk-lon` |

```bash
# Example: NYC / US East (change to nl-ams for EU)
sudo openvpn --config /etc/openvpn/client/surfshark/us-nyc.prod.surfshark.com_udp.ovpn \
             --auth-user-pass /etc/openvpn/client/surfshark.auth \
             --daemon --log /var/log/surfshark-openvpn.log

# Verify tunnel is up (should show VPN provider, not your ISP)
sleep 3
curl -s https://ipinfo.io | grep -E '"ip"|"org"'
```

### Auto-start on boot

**MX Linux with sysvinit (or other SysV-style init):** install the init script, then start the VPN. If your system has no `update-rc.d` or `service`, use the script path directly.

```bash
# From repo root (e.g. /home/x/dev/model-archival/local). Optional: pass server name (default us-nyc).
sudo bash deploy/install-surfshark-sysvinit.sh
# Or for EU: sudo bash deploy/install-surfshark-sysvinit.sh nl-ams
```

Then start (use whichever works on your system):

```bash
# If you have service:
sudo service openvpn-surfshark start

# If service is not found, run the script directly:
sudo /etc/init.d/openvpn-surfshark start
```

Check: `curl -s https://ipinfo.io | grep -E '"ip"|"org"'` (should show VPN provider, not Verizon/ISP).

To start at boot when `update-rc.d` is not available: add to root crontab `sudo crontab -e`:  
`@reboot /etc/init.d/openvpn-surfshark start`

**Artix / dinit:** use the install script (default us-nyc; pass `nl-ams` for EU):

```bash
sudo bash deploy/install-surfshark-dinit.sh
# Then start:
sudo dinitctl start openvpn-surfshark
```

**MX Linux with systemd:** use a systemd unit or `sudo systemctl enable openvpn-client@surfshark-nyc` if your distro provides a generic openvpn-client@.service template.

---

## Step 7 — Verify environment

```bash
bash scripts/check-environment.sh
# or directly:
bash deploy/verify-environment.sh
```

This checks:
- Required runtime tools: `python3`, `uv`, `aria2c`, `screen`, `openvpn`
- Drive mounts: presence, writability, free space for each of D1/D2/D3/D5
- HF token: set and valid
- Network: reachable to `huggingface.co`
- Registry: YAML valid, all referenced drives exist

All checks pass → safe to run downloads.

---

## Step 8 — Dry run

```bash
bash run.sh --dry-run
```

Simulates the full pipeline without downloading anything. Shows:
- What models would be downloaded
- Which drive each lands on
- Estimated sizes
- Any pre-flight issues

---

## Step 9 — Run downloads

Always run inside `screen` — downloads take days and SSH sessions drop.

```bash
screen -S archiver bash run.sh --all
```

- Detach: `Ctrl+A D`
- Reattach: `screen -r archiver`

To download only token-free models first (while waiting for HF token approvals):

```bash
screen -S archiver bash run.sh --priority-only 1
```

**Before rebooting** — always stop the archiver gracefully to avoid filesystem corruption:

```bash
<<<<<<< HEAD:local/docs/DEPLOYMENT.md
# Copy to VM:
scp local/deploy/fix-apparmor-cursor.sh root@<vm-ip>:/root/

# Run on VM:
bash /root/fix-apparmor-cursor.sh
=======
bash stop.sh        # waits for current shard to finish, then exits
# then reboot
>>>>>>> 31a9d82 (refinements. bug fixes.):docs/DEPLOYMENT.md
```

---

## Proxmox disk discovery command (reference)

```bash
lsblk -o NAME,SIZE,MODEL,SERIAL,TYPE,MOUNTPOINTS | grep disk
smartctl -i /dev/sdX    # full SMART detail
```

---

## fstab reference

After `vm-mount-disks.sh` runs, `/etc/fstab` should have entries like:

```
UUID=<uuid-of-d1>   /mnt/models/d1   ext4   defaults,noatime,nofail   0 2
UUID=<uuid-of-d2>   /mnt/models/d2   ext4   defaults,noatime,nofail   0 2
UUID=<uuid-of-d3>   /mnt/models/d3   ext4   defaults,noatime,nofail   0 2
UUID=<uuid-of-d5>   /mnt/models/d5   ext4   defaults,noatime,nofail   0 2
```

`nofail` prevents boot failure if a drive is temporarily absent.

Verify: `mount | grep /mnt/models`

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `archiver: command not found` | Run `uv sync` first; use `uv run archiver` |
| Drive not mounted after reboot | Run `sudo bash deploy/vm-mount-disks.sh` |
| Drive shows "Structure needs cleaning" | Run `sudo fsck.ext4 -y /dev/sdXN` then remount |
| `aria2c not found` | `sudo pacman -S aria2` / `sudo apt install aria2` |
| HF token rejected | Revoke and recreate at huggingface.co/settings/tokens; run `bash deploy/sethfToken.sh hf_NEW` |
| Download stops at 0 bytes | LFS CDN URL expired — re-run, the downloader refreshes URLs automatically |
| STATUS.md not updating | Check `/mnt/models/d5/` is writable |
| Low download speed | Connect VPN (see Step 6); ISP may be throttling HuggingFace |
| VPN not connecting | Check `/var/log/surfshark-openvpn.log`; verify credentials in `/etc/openvpn/client/surfshark.auth` |
| `screen is terminating` immediately | Run `bash run.sh --all` directly first to see the error; fix it, then use screen |

For deeper issues see [`docs/OPERATIONS.md`](OPERATIONS.md).
