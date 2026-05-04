# Ollama cache: supermicro retention, VM inventory, registry overlap

**Canonical tree:** Ollama hosting, sync scripts, rotation state, and refreshed inventory for this workflow are maintained under **[`ollama-hosting/`](../../ollama-hosting/README.md)**. Prefer **`ollama-hosting/scripts/ollama-sync.sh`** and **`ollama-hosting/docs/`** for new work; the copies below remain for backward compatibility until you retire them.

## Goals

1. **Free space on supermicro** by deleting Ollama blobs *only after* the same model is **fully synced** to the archival VM (`scripts/ollama-sync.sh` → **`ubuntu@192.168.8.32`** by default). Default destination is **`/mnt/models-d5/ollama`**; set **`ARCHIVAL_VM_SITE_CYCLE`** for multiple roots or **`ARCHIVAL_VM_DEST`** for a fixed path.
2. **Keep on supermicro** (hot subset for the GPU box):
   - **Gemma 4** — entire product line on disk (`gemma4/…` manifests: MoE, dense, E2B/E4B, any quant you still pull).
   - **Qwen Coder** only — `qwen2.5-coder/…`, and future `qwen3*coder*` paths — **not** base Qwen chat, **not** DeepSeek-R1 distills, **not** Llama/Dolphin/DeepSeek Coder unless you widen `keep_tag` again.
3. **Do not keep** on supermicro after verified VM sync: **Llama**, **Dolphin**, **DeepSeek Coder**, **DeepSeek-R1**, **non-coder Qwen**, **q8-only** edge cases you choose to drop, etc. — use `ollama-supermicro-prune-plan.sh` after comparing manifest lists.

Adjust the keep rules in `scripts/ollama-supermicro-prune-plan.sh` (`keep_tag`) if your definition differs.

### Archival VM disks (`d1`–`d5`)

Ollama expects a **single** coherent `models/` tree (`blobs/` + `manifests/`). **One rsync destination = one archive root**; you cannot stripe one live cache across disks without **mergerfs** (or similar) or maintaining **separate full copies** on different disks.

| Mount | Typical use |
|-------|-------------|
| **`/mnt/models-d5/ollama`** | Default additive Ollama archive (current archival VM). |
| **`/mnt/models-d2/ollama`**, **`/mnt/models-d3/ollama`**, … | Optional extra cycle members — set **`ARCHIVAL_VM_SITE_CYCLE`** (e.g. `d2=/mnt/models-d2/ollama,d5=/mnt/models-d5/ollama`). |
| **Legacy Artix** **`/mnt/models/d5/supermicro`** | Retired host **`x@192.168.8.65`** only; do not use on **`192.168.8.32`**. |

Refresh free space before large syncs: `ssh ubuntu@192.168.8.32 'df -h /mnt/models-d{1,2,3,5}'`.

### Per-sync destination rotation

- Leave **`ARCHIVAL_VM_DEST` unset** (empty): each successful `ollama-sync.sh` run picks the **next** path in the cycle and **advances** the counter in `docs/data/ollama-sync-rotation.state` (JSON: `next_index`, `sync_history`).
- Set **`ARCHIVAL_VM_DEST=/mnt/models-d5/ollama`** (or another absolute path) explicitly: that path is used; rotation **does not** advance (use for one-off or recovery).
- Override the cycle with **`ARCHIVAL_VM_SITE_CYCLE`** (comma-separated `LABEL=PATH` or bare paths). Default cycle is **d5** only (`/mnt/models-d5/ollama`).
- Implementation: `scripts/ollama_archival_rotation.py` (called from `ollama-sync.sh`).

### Completed models only (sync) + archive hygiene (VM)

1. **Supermicro before sync:** finish or cancel in-flight `ollama pull` jobs, then remove Ollama incomplete shards locally so they are not mistaken for complete weights (see `supermicro/scripts/ollama-cleanup-partials.sh` on the GPU host, or delete `~/.ollama/models/blobs/*partial*` while no pull is running).
2. **`ollama-sync.sh`:** by default **does not copy** `models/blobs/*partial*` or top-level `.rsync-partial/` from the source (set `OLLAMA_SYNC_INCLUDE_PARTIALS=1` only if you intentionally want incomplete shards — not recommended).
3. **After each successful VM sync:** by default the script runs **`ollama_archive_vm_maintain.py`** on the archival VM for **every** root in the rotation cycle (default **d5** only): deletes stray `*partial*` blobs, removes `.rsync-partial` trees, then prints an **integrity** summary (manifests whose layer blobs are missing). Set `OLLAMA_SYNC_VM_MAINTAIN=0` to skip.
4. **Manual maintain only:** `./scripts/ollama-archive-vm-maintain.sh` (same SSH + roots as sync).

### Where each model lives (canonical map)

After every sync (when inventory refresh is enabled), the repo regenerates:

| File | Purpose |
|------|---------|
| **`docs/OLLAMA-ARCHIVAL-MODEL-MAP.md`** | Human table: **`model:tag` → disk label → archive root → size → `supermicro_cleared`**. Use this before **`ollama rm`** on the Supermicro for anything that is **not** Gemma 4 / Qwen Coder. |
| `docs/data/ollama-vm-models-inventory.yaml` | Machine-readable source; **all** configured roots are scanned so a model copied to **d2** on one run and older blobs still on **d5** both appear. |

To refresh the map without re-syncing:

```bash
cd model-archival && uv run python scripts/update_ollama_vm_inventory.py --ssh ubuntu@192.168.8.32 \
  --infer-supermicro-cleared --supermicro-ssh x@192.168.8.106
uv run python scripts/generate_ollama_archival_map.py
```

(`ollama-sync.sh` passes the configured cycle roots for inventory — default **d5** only.)

## Maintained inventory

| File | Purpose |
|------|---------|
| `docs/data/ollama-cache-inventory.yaml` | Canonical lists: supermicro tags (fill in), VM **d5**/**d2**/**d3**/**d1** Ollama manifest paths (optional legacy), prune policy pointer. |
| `docs/data/ollama-vm-models-inventory.yaml` | **Ollama descriptors** (`model:tag`), **disk** (`d5`/`d2`/`d3`/`d1`), **paths**, **approximate sizes** (manifest + blob files), **`supermicro_cleared`** (`unknown` / `yes` / `no`). Regenerated by `scripts/update_ollama_vm_inventory.py`. |
| `docs/data/ollama-sync-rotation.state` | Rotation cursor + append-only **sync_history** (which disk each sync targeted). |
| `scripts/ollama_archive_vm_maintain.py` | Archival VM: delete `*partial*` blobs + `.rsync-partial/`; **integrity** check (manifest vs blobs). |
| `scripts/ollama-archive-vm-maintain.sh` | Wrapper: SSH + `print-archive-roots` + maintain script (no rsync). |
| `docs/SPECIALIST-HF-PENDING-OLLAMA.md` | **Single unified table:** union of specialist registry + failed-registry ids; columns for main-registry overlap, HF failure, **Ollama** tags/sizes/pull (from specialist `notes`), notes. Regenerate: `uv run python scripts/generate_specialist_ollama_pending_report.py`. Cache: `docs/data/ollama-registry-size-cache.json`. |

After each **`ollama-sync.sh`** run, the script attempts (unless `OLLAMA_SYNC_UPDATE_INVENTORY=0`) to refresh **`ollama-vm-models-inventory.yaml`** via SSH to the archival VM. To also infer **`supermicro_cleared`** from a live supermicro cache scan:

```bash
OLLAMA_VM_INVENTORY_EXTRA='--infer-supermicro-cleared --supermicro-ssh x@192.168.8.106' ./scripts/ollama-sync.sh
# or manually:
cd model-archival && uv run python scripts/update_ollama_vm_inventory.py --ssh ubuntu@192.168.8.32 \
  --infer-supermicro-cleared --supermicro-ssh x@192.168.8.106
```

Without `--infer-supermicro-cleared`, existing **`supermicro_cleared`** values in the YAML are preserved; set them by hand after you prune supermicro.

Refresh the legacy YAML **transferred** section (optional; mirrors manifest paths) after each sync:

```bash
ssh ubuntu@192.168.8.32 'find /mnt/models-d5/ollama/models/manifests/registry.ollama.ai/library -type f | sed "s|.*/library/||" | sort'
# paste into ollama-cache-inventory.yaml under transferred_ollama_cache.d5_supermicro.manifest_paths
```

## Prune plan (dry run)

1. On **supermicro**, export manifest list → `/tmp/super.txt` (see script header).
2. On **VM**, export list → `/tmp/vm.txt` (or use inventory YAML).
3. From repo:

```bash
SUPER=/tmp/super.txt VM=/tmp/vm.txt DRY_RUN=1 bash model-archival/scripts/ollama-supermicro-prune-plan.sh
```

4. When satisfied, run **`ollama rm model:tag`** on supermicro only for **PRUNE** lines (or `DRY_RUN=0` on supermicro — still verify VM trees complete first).

## Registry duplicates (HF archiver vs specialist queue)

- **103** models in `config/registry-specialists.yaml`.
- **58** of those **`id`s also appear in `config/registry.yaml`** — the same HF repo may be downloaded twice if you run both registries without scoping.
- Cross-check Ollama tags in specialist `notes` (`[ollama:…]`) against HF `id` to avoid pulling the **same weights** via Ollama and HF (GGUF vs safetensors is not always duplicate on disk, but operationally redundant).

## Specialist HF failures → Ollama format

Regenerate:

```bash
cd model-archival
uv run archiver failed-registry   # on host with /mnt/models/d3/run_state.json
uv run python scripts/generate_specialist_ollama_pending_report.py   # queries registry.ollama.ai for sizes; use --offline to use cache only
```

Open **`docs/SPECIALIST-HF-PENDING-OLLAMA.md`**: failed specialist rows (hostable &lt; ~200B heuristic), optional `ollama pull` when tags exist in notes.

**Pending** models (not `failed` in YAML) are not in that file — use `run_state.json` / `STATUS.md` on the VM.
