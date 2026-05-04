# Mirror Supermicro `~/.ollama` to d5 (including partials) and resume pulls on the archive VM

## Is it possible?

**Yes**, with two conditions:

1. **Same tree layout** — Ollama expects `models/manifests/…` and `models/blobs/…` under a single data root (`OLLAMA_HOME` / `~/.ollama`). If you rsync Supermicro’s `~/.ollama/` into **`/mnt/models-d5/ollama/`** on the VM, point Ollama at that directory:

   ```bash
   export OLLAMA_HOME=/mnt/models-d5/ollama
   export PATH="$HOME/.local/bin:$PATH"
   ollama serve
   ```

   Then run **`ollama pull <same model:tag>`** for any incomplete download. Ollama should continue writing the existing `sha256-*-partial*` shard files instead of starting from zero.

2. **Compatible Ollama build** — Prefer the **same or newer** `ollama` version on the VM as on Supermicro. Older clients might mishandle newer manifest formats.

## Sync **including** partial downloads

Default **`ollama-sync.sh`** skips `models/blobs/*partial*` so the archive only gets completed weights. To mirror **everything** Supermicro has (so the VM can resume):

```bash
cd ollama-hosting
OLLAMA_SYNC_INCLUDE_PARTIALS=1 ./scripts/ollama-sync.sh
# or full pipeline:
OLLAMA_SYNC_INCLUDE_PARTIALS=1 ./scripts/ollama-registry-sync
```

Effects:

- **rsync** copies partial blob files and `.rsync-partial/` (interrupted rsync debris).
- **Post-sync maintain** automatically passes **`--keep-ollama-partials`** so the VM does **not** delete `*partial*` files right after sync. It still prunes `.rsync-partial/` trees (those are rsync’s, not Ollama’s resume state).

To preserve partials but keep the default rsync excludes, run sync as usual and only skip deletion:

```bash
OLLAMA_MAINTAIN_KEEP_PARTIALS=1 ./scripts/ollama-sync.sh
```

(Meaningful only if partial files were copied earlier or created on the VM.)

Manual maintain on the VM with partials kept:

```bash
cat scripts/ollama_archive_vm_maintain.py | ssh ubuntu@192.168.8.32 python3 - --keep-ollama-partials /mnt/models-d5/ollama
```

## Record: which blob belongs to which model

Ollama’s mapping is **manifest JSON → digest list → files under `models/blobs/`**. Generate a CSV/JSON table from any Ollama home (Supermicro, d5 mirror, etc.):

```bash
cd ollama-hosting
./scripts/ollama_blob_model_map.py /mnt/models-d5/ollama --format csv --out docs/data/ollama-blob-model-map.csv
# or on Supermicro:
./scripts/ollama_blob_model_map.py ~/.ollama --format tsv
```

Columns include **`model_tag`** (`model:tag`), **`role`** (`config` / `layer`), **`digest`**, **`blob_file`**, **`size_bytes`**, **`is_partial_file`**. Layers shared by several tags appear **once per tag** (duplicate digests across rows are normal).

The existing inventory pipeline (**`update_ollama_vm_inventory.py`**) still produces **`docs/data/ollama-vm-models-inventory.yaml`** (per-tag totals and paths); use **`ollama_blob_model_map.py`** when you need **per-layer / per-blob** detail.

## Caveats

- **Additive archive:** rsync still does not `--delete` on the VM. Deleted models on Supermicro do not remove blobs on d5.
- **Integrity:** While a pull is incomplete, manifests may reference blobs that are not fully present yet; **`ollama_archive_vm_maintain.py`** may report warnings until the pull finishes.
- **Two active writers:** Avoid running **`ollama pull` on Supermicro and on the VM at the same time** against the same tag; sync between sessions instead.
