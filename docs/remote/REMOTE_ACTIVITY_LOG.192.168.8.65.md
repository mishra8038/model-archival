
## 2026-03-26 (UTC) — local deployment
- Deployed updated gdrive uploader files from local workspace.
- Stopped gdrive-upload screen before replacing files.
- Validated upload_registry.py syntax on VM.
- Refreshed remote metadata cache (upload_registry.py --refresh-remote-tree-cache).
- Restarted gdrive-upload session with updated files.

## 2026-03-28 (UTC) — upload + download status refresh

- gdrive-archival: python3 backup.py upload-registry-status; python3 backup.py uploaded-registry-list
- model-archiver: uv run archiver report (wrote /mnt/models/d3/STATUS.md)

## 2026-03-29 (UTC) — storage: failspy uncensored d5 → d3

- Removed incomplete `d3/uncensored/failspy/Meta-Llama-3-70B-Instruct-abliterated-v3.5` (~10G), then cross-fs `mv` full tree from `d5/uncensored/failspy/` → `d3/uncensored/failspy/` (~132G).
- After: `d5/uncensored/failspy/` empty; `d5` ~132G free (was 100%); `d3` ~200G free.

## 2026-03-29 (UTC) — .tmp compare: failspy / tensorblock GGUF (d3 vs d5)

- Compared `d3/.tmp` vs `d5/.tmp` for three ids: **failspy** stubs only on both (weights complete under `d3/uncensored/`). **DeepSeek-R1-Distill-Llama-70B abliterated GGUF**: ~34G Q3_K_M partial **only on d3**; d5 dir empty → removed empty d5 tmp dir. **Llama-3.3-70B abliterated GGUF**: ~34G Q3_K_M partial **only on d5**; d3 dir empty → removed empty d3 tmp dir. No cross-drive shard merge needed (no split file between disks).
- VM cleanup: `rm -rf` both `failspy_*` `.tmp` trees (metadata-only); `rmdir` empty duplicate tensorblock tmp dirs as above.
- Registry (sync from repo): `failspy/...` and `tensorblock/DeepSeek-R1-Distill-Llama-70B-abliterated-GGUF` → **drive: d3**; `tensorblock/Llama-3.3-70B-Instruct-abliterated-GGUF` remains **drive: d5**.

