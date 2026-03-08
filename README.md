# model-archival

Archival of open-source LLM/LRM weights from HuggingFace. Two strategies:

| Folder | Strategy | Status |
|--------|----------|--------|
| [`local/`](local/) | Python archiver — downloads to physical HDDs via aria2c on a local VM | Active |
| [`colab/`](colab/) | Google Colab notebooks — streams weights to Google Drive | In development |

## local/

Self-contained Python project (`uv`). All code, config, docs, scripts, and deployment tools live under `local/`.

```bash
cd local
uv sync
bash run.sh --dry-run
bash run.sh --all
```

See [`local/README.md`](local/README.md) for full documentation.

## colab/

Google Colab notebook for archiving to Google Drive. See [`colab/README.md`](colab/README.md).
