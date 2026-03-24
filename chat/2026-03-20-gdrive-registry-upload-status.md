# GDrive registry upload status file

- **`logs/GDRIVE-REGISTRY-UPLOAD-STATUS.md`**: Markdown dashboard — discovered model revision dirs vs `logs/uploaded.log` (`registry-model`), pending list, orphans; optional newest `registry-d5` timestamp; line count for pre-upload verify JSONL.
- **Refresh:** end of every `backup-registry` / `upload_registry.py` run; manual `python3 backup.py upload-registry-status`.
- **d5:** successful full-tree copy appends `registry-d5` to `uploaded.log` (one line per successful run).
