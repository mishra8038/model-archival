# Ollama archival sync — systemd timer **removed**

Periodic **`ollama-registry-sync`** via a user **timer** is **no longer** shipped in this repo. Run sync **manually** when you want to copy Supermicro `~/.ollama` to the archive VM and refresh the registry:

```bash
cd /path/to/ollama-hosting
./scripts/ollama-registry-sync
```

## If you previously installed the timer

Disable and remove the units so nothing runs on a schedule:

```bash
systemctl --user disable --now ollama-archival-sync.timer 2>/dev/null || true
rm -f ~/.config/systemd/user/ollama-archival-sync.timer \
      ~/.config/systemd/user/ollama-archival-sync.service
systemctl --user daemon-reload
```

Optional: reset failed state if any:

```bash
systemctl --user reset-failed ollama-archival-sync.service 2>/dev/null || true
```

One-off sync (same as old service would have run):

```bash
cd "$HOME/z/dev/model-archival/model-archival/ollama-hosting"
OLLAMA_SYNC_BWLIMIT_KB=0 ARCHIVAL_VM_DEST=/mnt/models/d5/supermicro ./scripts/ollama-registry-sync
```

Adjust paths to match your clone.
