# systemd user timer — Ollama archival sync every 4 hours

Runs on the **workstation** that can reach **supermicro** and the **archival VM** (same host where you manually run the sshfs bridge sync).

**ExecStart** calls **`$HOME/z/dev/model-archival/model-archival/ollama-hosting/scripts/ollama-registry-sync`**, which runs **`ollama-hosting/scripts/ollama-sync.sh`** and then merges **`docs/data/ollama-archival-global-manifest.yaml`** + **`registry/TARGET_PULL_HISTORY.csv`** into **`ollama-hosting/registry/OLLAMA_MODEL_REGISTRY.json`**. Edit the unit file if your clone path differs.

## Install

```bash
mkdir -p ~/.config/systemd/user
OH="$HOME/z/dev/model-archival/model-archival/ollama-hosting"
cp "$OH/systemd/ollama-archival-sync.service" ~/.config/systemd/user/
cp "$OH/systemd/ollama-archival-sync.timer" ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now ollama-archival-sync.timer
```

## Check

```bash
systemctl --user list-timers ollama-archival-sync.timer
journalctl --user -u ollama-archival-sync.service -n 80 --no-pager
```

## Requirements

- **SSH** to Supermicro and archival VM without interactive password (keys loaded).
- **`uv`** on `PATH` in login shells (inventory step) if `ollama-sync.sh` invokes it.
- **Runs while logged out:** `loginctl enable-linger "$USER"`

## One-shot test

```bash
systemctl --user start ollama-archival-sync.service
```
