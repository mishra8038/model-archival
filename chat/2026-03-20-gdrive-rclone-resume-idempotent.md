# GDrive backup: rclone-merge resume

- Removed **`remote_path_has_files`** and all “skip if state says backed_up” short-circuits for models, `backup-dirs`, and **`backup_extra_paths`**. Partial uploads no longer strand half-finished trees.
- Every sync runs **`rclone copy --checksum`**; rclone only transfers missing/changed files. Re-run after interruption to resume.
- **`uploaded.log`**: still appended on **first** successful completion for a model/dir (`was_marked_complete`), not on every no-op re-sync.
- **`backup_extra_paths_refresh`**: updates `state.json` paths on success like non-refresh.
- **`README.md`**: documents idempotent/resumable behavior.
