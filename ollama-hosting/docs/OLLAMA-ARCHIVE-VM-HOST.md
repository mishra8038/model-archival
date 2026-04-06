# Ollama on the archival VM (direct pulls on big disk)

Use this when you want **new downloads** to land on **`/mnt/models/d2`** or **`d3`** instead of filling Supermicro `~/.ollama`.

**Host:** `x@192.168.8.65` (Artix). **Existing rsync mirror** of Supermicro cache stays under **`/mnt/models/d5/supermicro`** unless you change that layout.

## Layout on the VM

| Path | Role |
|------|------|
| `~/z/env/ai/ollama/` | Synced copy of **ollama-hosting** (registry, `scripts/ollama-pull-queue`, docs) |
| `/mnt/models/d2/ollama` | **`OLLAMA_HOME`** — live Ollama data (models, id files) for VM-local pulls |
| `/mnt/models/d5/supermicro` | Prior **mirror** from Supermicro (additive rsync; separate from `OLLAMA_HOME` above) |

To use **d3** instead: set `OLLAMA_HOME=/mnt/models/d3/ollama` (create the directory first; ensure `x` owns it).

## One-time: environment

```bash
# On the archive VM, after copying env-archive-vm.sh:
source ~/z/env/ai/ollama/env-archive-vm.sh
ollama serve   # foreground, or nohup / OpenRC / screen
```

`env-archive-vm.sh` sets:

- `PATH` → includes `~/.local/bin` (where the `ollama` binary lives)
- `OLLAMA_HOME` → big disk (default **d2**)
- `OLLAMA_HOST` → `127.0.0.1:11434`

## Pulls (registry, throttled)

```bash
source ~/z/env/ai/ollama/env-archive-vm.sh
cd ~/z/env/ai/ollama
command -v trickle >/dev/null || echo "Install trickle for ~4 MiB/s cap (optional)"
./scripts/ollama-pull-queue
```

Default queue behavior: **one model per run**; **`--all`** drains pending. **`USE_TRICKLE=0`** disables the cap.

**Note:** Registry JSON may still mark tags “complete” if `merge-manifest` thinks weights live under **d5** `supermicro`. For a **fresh** VM-only queue state you can edit `registry/OLLAMA_MODEL_REGISTRY.json` or run pulls with `RE_PULL_ARCHIVED=1` / `IGNORE_PULL_HISTORY=1` as documented in `ollama-pull-queue` header — align policy with how you treat d5 vs d2.

## Refresh kit from workstation

From a machine with the canonical tree:

```bash
rsync -az --delete --exclude '.venv/' --exclude 'uv.lock' \
  /path/to/ollama-hosting/ \
  x@192.168.8.65:~/z/env/ai/ollama/
scp /path/to/ollama-hosting/config/env-archive-vm.sh \
  x@192.168.8.65:~/z/env/ai/ollama/env-archive-vm.sh
```

## Binary install (no root)

The `ollama` client binary was copied from Supermicro (`/usr/local/bin/ollama`) to `~/.local/bin/ollama` on the VM. To upgrade: repeat from a host that has a newer `ollama`, or extract `ollama-linux-amd64.tar.zst` from [GitHub releases](https://github.com/ollama/ollama/releases).
