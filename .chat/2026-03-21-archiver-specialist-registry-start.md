# Archiver — specialist registry

- `model-archival/scripts/run.sh`: added `--registry PATH` (passed through to `uv run archiver --registry …` for plan, download, status; Python snippets use the same file for D5 logs path).
- VM `x@192.168.8.65`: repo path **`/home/x/dev/model-archival/model-archiver`** (not `…/local`). Synced `config/registry-specialists.yaml` and `scripts/run.sh`, then started:
  - `screen -dmS archiver bash -c 'cd …/model-archiver && bash scripts/run.sh --registry config/registry-specialists.yaml --skip-drive-space-check'`
- Active child observed: `archiver --registry config/registry-specialists.yaml download --all …` (pid ~10841).
