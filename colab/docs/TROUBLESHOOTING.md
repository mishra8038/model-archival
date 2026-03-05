# Troubleshooting

Common issues and fixes for the Colab archiver and Docker local runtime.

---

## Docker on MX Linux 23

### Daemon fails to start

**Symptom:**
```
sudo /etc/init.d/docker start
# → no output, or exits immediately
```

**Step 1 — Start containerd first**

Docker CE depends on containerd. On MX Linux, it doesn't always auto-start:
```bash
sudo /etc/init.d/containerd start
sudo /etc/init.d/docker start
```

**Step 2 — Get the actual error**

```bash
sudo dockerd 2>&1 | head -40
```

**Step 3 — Fix iptables/nftables conflict (most common on MX Linux 23)**

MX Linux 23 uses nftables by default. Docker CE expects iptables-legacy:
```bash
sudo apt-get install -y iptables
sudo update-alternatives --set iptables /usr/sbin/iptables-legacy
sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy
sudo /etc/init.d/docker start
```

**Step 4 — Load overlay kernel module**

```bash
sudo modprobe overlay
sudo modprobe br_netfilter
# Make persistent across reboots:
echo "overlay" | sudo tee -a /etc/modules
echo "br_netfilter" | sudo tee -a /etc/modules
sudo /etc/init.d/docker start
```

**Step 5 — Check syslog for clues**

```bash
sudo tail -50 /var/log/syslog | grep -i docker
sudo tail -50 /var/log/daemon.log | grep -i docker
```

---

### Container starts but URL not printed

```bash
# Wait longer and check logs manually
docker logs colab-runtime 2>&1 | grep token
# or
bash ~/colab-url.sh
```

---

### Port 9000 already in use

```bash
sudo lsof -i :9000
# Kill the conflicting process, or start on a different port:
docker stop colab-runtime
docker run -d --name colab-runtime --restart=unless-stopped \
  -p 127.0.0.1:9001:8080 \
  us-docker.pkg.dev/colab-images/public/runtime
# Update ~/colab-url.sh port accordingly
```

---

### docker: permission denied (not in docker group yet)

```bash
# Use sudo for now:
sudo docker ps
sudo bash ~/colab-url.sh

# Permanent fix (requires re-login):
sudo usermod -aG docker $USER
# Then log out and back in, or:
newgrp docker
```

---

## Colab notebook

### "Cannot find downloader.py"

Run `setup.ipynb` first — it copies `colab/lib/` to Drive so it persists across sessions.

Alternatively, clone the repo manually in a notebook cell:
```python
import subprocess
subprocess.check_call(['git', 'clone', '--depth=1',
    'https://github.com/mishra8038/model-archival.git',
    '/content/model-archival'])
```

### "Cannot find registry.yaml"

Same fix — run `setup.ipynb` or clone the repo.

### Drive mount fails / hangs

Cell 3 includes retry logic. If it keeps failing:
```python
from google.colab import drive
drive.mount('/content/drive', force_remount=True)
```

Or in a fresh cell:
```python
import subprocess
subprocess.check_call(['umount', '/content/drive'])
from google.colab import drive
drive.mount('/content/drive')
```

### HF 401 on a gated model

1. Check token is set: in Cell 2 output it should say "HF_TOKEN loaded"
2. Visit the model page on huggingface.co and accept the licence terms
3. If token expired: add a new one via Colab Secrets (🔑 icon)

### Session disconnects before download finishes

This is expected on free Colab (12h limit) and Pro (24h limit).
The notebook is fully resumable — just run it again.

For Pro+: enable **Runtime → Background execution** before closing the browser.

### Progress bar not showing

`ipywidgets` should be pre-installed in Colab. If missing:
```bash
!pip install -q ipywidgets
```

---

## Local Docker runtime — connecting to Colab

### "Connect to local runtime" not available in Colab menu

This option requires the runtime to be reachable from your browser.

If the Docker container is on a **remote machine**, you need an SSH tunnel:
```bash
# Run on your local machine (not the remote):
ssh -L 9000:127.0.0.1:9000 user@<remote-ip> -N &
```
Then paste `http://127.0.0.1:9000/?token=...` into Colab.

### Connection refused after paste

- Check container is running: `docker ps`
- Check port binding: `docker port colab-runtime`
- Verify SSH tunnel is active: `lsof -i :9000`

### URL token changes after container restart

The Jupyter token is regenerated on every container start. After any restart:
```bash
bash ~/colab-url.sh   # on the machine running Docker
```
Then re-paste into Colab.

---

## Integrity / checksums

### Sidecar mismatch in verify cell

A file was corrupted during transfer. Fix:
1. Delete the bad file and its `.sha256` sidecar from Drive
2. Delete the model's `.file_state.json` entry for that file
3. Re-run the notebook — it will re-download only the missing file

### manifest.json missing

Indicates the session was cut before the model completed.
The notebook will re-download missing files and regenerate the manifest.
