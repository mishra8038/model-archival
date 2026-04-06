# Model tree deduplication (archive VM, 2026-04-05)

Operations applied on **192.168.8.65** under `/mnt/models`. Canonical location for each repo follows **`config/registry.yaml`** `drive` and `content_subdir` (`raw` / `quantized` / `uncensored`).

## Cross-drive / stub consolidation

| hf_repo | Canonical (kept) | Removed / moved |
|--------|-------------------|-----------------|
| `MiniMaxAI/MiniMax-M2.5` | **d1** `raw/.../f710177d...` (~64 GiB, 144 files) | **d3** partial same SHA (~24 GiB, 94 files) — deleted |
| `microsoft/Phi-4-mini-instruct` | **d5** `raw/.../cfbefac...` + `latest` → SHA (rsync from d3) | **d3** BF16 tree removed; **d2** stub removed |
| `meta-llama/Llama-3.2-3B-Instruct` | **d2** `raw/.../0cb88a4f...` + `latest` → SHA (rsync from d3) | **d3** tree removed; **d2** old stub overwritten by rsync |
| `deepseek-ai/deepseek-coder-6.7b-instruct` | **d3** `raw/.../e5d64add...` + `latest` | **d2** stub removed; **d3** `specialist/science/raw/...` stub (~1.4 MiB) removed |
| `failspy/Meta-Llama-3-70B-Instruct-abliterated-v3.5` | **d3** `uncensored/.../fc951b03...` + `latest` | **d3** `specialist/science/uncensored/...` stub (~8.9 MiB) removed |

## Verified non-issues

- **`Qwen/Qwen2.5-Math-72B-Instruct`**: On VM, only **d5** `raw/.../8fcf92b1...` with `latest` → SHA (single tree). No second full copy on d5; d3 path absent.
- **`failspy/...` “three revisions”**: Inventory showed one full SHA + `latest` symlink; the extra rows were the **specialist** stub (removed), not a third full tree.

## Ongoing checks (164 “latest + SHA” rows)

Many manifests list both `latest` and a commit directory; **if `latest` is a symlink to that SHA, disk usage is not doubled**. To find risky layouts:

- `bash model-archival/scripts/scan-suspicious-revision-layout.sh` — flags non-symlink `latest` or **multiple** 40-hex dirs under one repo.
- `bash model-archival/scripts/scan-cross-drive-raw-duplicates.sh` — lists `org/name` present under `raw/` on more than one of d1/d2/d3/d5.

Review script output before deleting anything; multi-SHA can be intentional (A/B revisions).

## Not touched

- **`unsloth/Phi-4-mini-instruct-GGUF`** on d3 (and specialist mirror) — different `hf_repo` from BF16 `microsoft/Phi-4-mini-instruct`.
- **Checksum / inventory sidecars** under e.g. `d1/model-checksums/` — separate from weight trees; reconcile in a dedicated pass if desired.
