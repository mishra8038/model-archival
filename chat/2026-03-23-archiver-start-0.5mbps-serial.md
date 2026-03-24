# Archiver start — 0.5 MB/s, one download at a time

**VM:** `x@192.168.8.65` → `/home/x/dev/model-archival/model-archiver`

```bash
screen -dmS archiver bash scripts/run.sh --all \
  --registry config/registry.yaml \
  --queue-mode serial \
  --max-parallel 1 \
  --bandwidth-cap 0.5 \
  --no-scheduled-bandwidth-cap \
  --skip-drive-space-check
```

- **Serial + `--max-parallel 1`:** one model worker at a time.
- **`--bandwidth-cap 0.5`:** global aria2 cap ~0.5 MiB/s.
- **`--no-scheduled-bandwidth-cap`:** no day/night schedule (flat cap 24/7).

Attach: `screen -r archiver`

For specialist list only, swap `--registry config/registry-specialists.yaml`.
