# Archiver restart — specialist registry

- **VM:** `x@192.168.8.65`, repo `/home/x/dev/model-archival/model-archiver`
- **Synced:** `model-archival/config/registry-specialists.yaml` → VM `config/registry-specialists.yaml`
- **Stopped:** prior run using `config/registry.yaml` (`scripts/stop.sh` — clean exit)
- **Started:** `screen -dmS archiver bash scripts/run.sh --all --registry config/registry-specialists.yaml --skip-drive-space-check`
- **Attach:** `screen -r archiver`
