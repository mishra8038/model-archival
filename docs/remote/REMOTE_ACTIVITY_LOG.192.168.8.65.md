
## 2026-04-03 (UTC) — Specialist run: Gemma 4 first + disk-space failed retries

- **Registry (workspace → VM `config/`):** `registry-specialists.yaml` — `deepseek-ai/deepseek-vl2` **d1→d3**; added **`nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16`** (matches `run_state` id); **`Undi95/dbrx-base`**, **`tiiuae/falcon-180B-chat`** on **d2** for retries; **`registry.yaml`** — same Nemotron row; **`Undi95/dbrx-base`**; **`falcon-180B-chat` d1→d2**.
- **Screen:** `archiver-specialists` — `uv run archiver --registry config/registry-specialists.yaml download --all --queue-mode adaptive --max-parallel-drives 4 --max-per-drive 2 --bandwidth-cap 4 --min-speed-mbps 3 --skip-drive-space-check` (log append **`/mnt/models/d3/logs/archiver-specialists.log`**). **Note:** `--registry` is a **global** archiver option (before `download`), not after it.
- **Priority:** existing **`/mnt/models/d3/priority_overrides.json`** keeps Gemma 4 small line at **-620** / 26B at **-580** — scheduler picks Gemma before override-**120** disk-failed rows.

## 2026-04-03 (UTC) — Gemini 3 HF previews → legacy; specialist registry trim

- **Workspace → VM `config/`:** `registry-specialists.yaml` (removed `google/gemini-3-flash-preview`, `google/gemini-3.1-flash-lite-preview`); `registry-legacy.yaml` (same ids added with `legacy: true`, notes: no HF token / Gemma 4 sufficient).
- **`uv run archiver failed-registry --include-skipped`** on VM; outputs synced back to local repo (`config/failed-models-registry.yaml`, `docs/FAILED_MODEL_REGISTRY.md`).

## 2026-04-03 (UTC) — D3 `priority_overrides.json` (specialist queue)

- Replaced **`/mnt/models/d3/priority_overrides.json`** (atomic `*.new` → rename) from merged VM PO + gated **`run_state.json`** + **`registry-specialists.yaml`** rules.
- **Gemma-4 small dense** (`E2B`, `E2B-it`, `E4B`, `E4B-it`): **-620**; **Gemma-4 26B MoE** pair: **-580**; **31B** pair: overrides **removed** (registry priority only).
- **Failed specialists** (except four below): **120**; **`unsloth/DeepSeek-R1-GGUF`** (failed, not in specialist registry): **120** (cleared legacy **-979**).
- **Last four** (absolute tail): **`unsloth/DeepSeek-V3-GGUF`**, **`deepseek-ai/deepseek-vl2`**, **`Qwen/Qwen3.5-122B-A10B`**, **`Qwen/Qwen3.5-397B-A17B`** → **250**.
- **Pending/in_progress** with prior override **0**: key **removed** (registry priority applies). **Complete** specialist keys **removed** from file.

## 2026-04-02 (UTC) — registry: drive alignment to remaining `.tmp` / d5 dolphin tree

- **`config/registry.yaml`** (synced to VM **`model-archiver/config/`**): `tiiuae/falcon-180B` **d1→d5** (scratch `d5/.tmp/tiiuae_falcon-180B`); `unsloth/DeepSeek-V3-GGUF` **d5→d1** (scratch `d1/.tmp/unsloth_DeepSeek-V3-GGUF`). `cognitivecomputations/dolphin-2.9.2-qwen2-72b` stays **d5** (no `.tmp` left; tree under `d5/uncensored/` — notes only).
- **`registry-specialists.yaml`**: dolphin notes; DeepSeek-V3-GGUF already **d1** — note text aligned.

## 2026-04-02 (UTC) — scratch: remove selected `.tmp` trees

- **`rm -rf`**: `d1/.tmp/tiiuae_falcon-180B`; `d3/.tmp/unsloth_DeepSeek-V3-GGUF`; `d3/.tmp/cognitivecomputations_dolphin-2.9.2-qwen2-72b`; `d5/.tmp/cognitivecomputations_dolphin-2.9.2-qwen2-72b`.
- **Left in place** (not requested): `d1/.tmp/unsloth_DeepSeek-V3-GGUF`; `d5/.tmp/tiiuae_falcon-180B`.

## 2026-04-02 (UTC) — dedupe: remove duplicate model trees (d1/d2)

- **`rm -rf`** duplicate installs (canonical copies remain on registry drives: Llama **d1**, RomboUltima + deepseek-coder-6.7b **d3**):
  - `d2/raw/meta-llama/Llama-3.3-70B-Instruct/6f6073b423013f6a7d4d9f39144961bfbfbc386b` (~197 GiB)
  - `d1/uncensored/FINGU-AI/RomboUltima-32B/98a732a32e2366a2ab8f08fdc3d668892e7c1f7f` (~10 GiB)
  - `d1/raw/deepseek-ai/deepseek-coder-6.7b-instruct/e5d64addd26a6a1db0f9b863abf6ee3141936807` (~16 GiB)
- Empty parent dirs removed where applicable; **`df`**: d2 ~335 G free, d1 ~64 G free after op.

## 2026-04-02 (UTC) — gh-archival: owned repos → D5 → Google Drive

- Rsynced **`gh-archival/`** from workspace → **`/home/x/dev/model-archival/gh-archival`** on VM; **`uv sync`**.
- Started **`uv run gh-archival run`** with **`--work-dir /mnt/models/d5/gh-archival-output`**, **`RCLONE_CONFIG=/home/x/dev/model-archival/gdrive-archival/rclone.conf`**, **`GH_ARCHIVAL_RCLONE_REMOTE=gdrive:1L2FSm5KW9Ypee8IMfXUkVjHvkwmVYy69`**, **`--rclone-arg=--bwlimit=2M`** (background **`nohup`**, log path **`/mnt/models/d5/gh-archival-output/nohup.log`** — Rich UI may leave it sparse). **`GITHUB_TOKEN`** supplied from developer machine via one-shot SSH heredoc (not written to disk on VM).
- Outcome: run **`2026-04-02T195908Z`**, **23** repos archived **`ok`**, **0** failed (**`manifest-2026-04-02T195908Z.json`**); **~570M** on D5 under **`snapshots/2026-04-02T195908Z/`**; **`rclone lsf`** shows **23** files under Drive **`…/2026-04-02T195908Z/`** in folder **`1L2FSm5KW9Ypee8IMfXUkVjHvkwmVYy69`**.

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

## 2026-03-30 (UTC) — specialist queue: priority overrides + full adaptive run

- Merged **`/mnt/models/d3/priority_overrides.json`** using `scripts/compute-priority-overrides.py` (from workspace): **finish soon** for `Intel/neural-chat-7b-v3-1`, `HuggingFaceH4/zephyr-7b-beta` (~−1000); **defer (99)** for `MiniMaxAI/MiniMax-M2.5`, `meta-llama/Llama-3.2-90B-Vision-Instruct`, `google/medgemma-27b-it` (large / low on-disk progress).
- Stopped previous **`archiver-m25`** MiniMax-only session (SIGKILL after SIGTERM did not exit within 5 min — investigate stuck shard if recurring).
- Started **`screen -S archiver-specialists`**: `uv run archiver --registry config/registry-specialists.yaml download --all --queue-mode adaptive --max-parallel-drives 4 --max-per-drive 2 --bandwidth-cap 4 --min-speed-mbps 3 --skip-drive-space-check` → log `/mnt/models/d3/logs/archiver-specialists.log`. Gated rows skipped without token: `MiniMaxAI/MiniMax-M2.7`, `google/gemini-3-flash-preview`, `google/gemini-3.1-flash-lite-preview`.
- **`scripts/stop.sh`**: `pgrep` pattern broadened to `archiver.*[[:space:]]download` so single-model invocations are found.

## 2026-03-29 (UTC) — .tmp compare: failspy / tensorblock GGUF (d3 vs d5)

- Compared `d3/.tmp` vs `d5/.tmp` for three ids: **failspy** stubs only on both (weights complete under `d3/uncensored/`). **DeepSeek-R1-Distill-Llama-70B abliterated GGUF**: ~34G Q3_K_M partial **only on d3**; d5 dir empty → removed empty d5 tmp dir. **Llama-3.3-70B abliterated GGUF**: ~34G Q3_K_M partial **only on d5**; d3 dir empty → removed empty d3 tmp dir. No cross-drive shard merge needed (no split file between disks).
- VM cleanup: `rm -rf` both `failspy_*` `.tmp` trees (metadata-only); `rmdir` empty duplicate tensorblock tmp dirs as above.
- Registry (sync from repo): `failspy/...` and `tensorblock/DeepSeek-R1-Distill-Llama-70B-abliterated-GGUF` → **drive: d3**; `tensorblock/Llama-3.3-70B-Instruct-abliterated-GGUF` remains **drive: d5**.

