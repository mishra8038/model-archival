# Ollama on the archival VM (direct pulls on big disk)

Use this when you want **new downloads** to land on **`/mnt/models-d2`** or **`/mnt/models-d3`** instead of filling Supermicro `~/.ollama`.

**Host:** `ubuntu@192.168.8.32` (Ubuntu; hostname **k80-ollama**). Default **`OLLAMA_HOME`** / Ollama sync destination: **`/mnt/models-d5/ollama`** (see `ollama-hosting/config/env-archive-vm.sh` and `ollama-sync.sh`).

**Legacy:** `x@192.168.8.65` (Artix) used **`/mnt/models/d5/supermicro`** and **`/mnt/models/d2/ollama`** — older notes below still describe that layout if you ever attach those disks read-only.

## Layout on the VM (current)

| Path | Role |
|------|------|
| **`/mnt/models-d5/ollama`** | **`OLLAMA_HOME`** default — live Ollama data + additive Supermicro rsync target |
| **`/mnt/models-d2/ollama`**, **`/mnt/models-d3/ollama`** | Optional overflow **`OLLAMA_HOME`** targets (create dirs; ensure service user owns them) |
| **`~/z/env/ai/ollama/`** | Optional synced copy of **ollama-hosting** (if you keep that tree on the VM) |

## One-time: environment

```bash
# On the archive VM, from repo or synced tree:
source /path/to/ollama-hosting/config/env-archive-vm.sh
ollama serve   # foreground, or systemd / screen
```

`env-archive-vm.sh` sets:

- `PATH` → includes `~/.local/bin` (where the `ollama` binary may live)
- `OLLAMA_HOME` → **`/mnt/models-d5/ollama`** by default
- `OLLAMA_HOST` → `127.0.0.1:11434`

## Pulls (registry, throttled)

```bash
source /path/to/ollama-hosting/config/env-archive-vm.sh
cd /path/to/ollama-hosting   # or your synced ~/z/.../ollama layout
command -v trickle >/dev/null || echo "Install trickle for ~4 MiB/s cap (optional)"
./scripts/ollama-pull-queue
```

Default queue behavior: **one model per run**; **`--all`** drains pending. **`USE_TRICKLE=0`** disables the cap.

**Note:** Registry JSON may still mark tags “complete” if `merge-manifest` thinks weights live under an older **`supermicro`** path. For a **fresh** VM-only queue state you can edit `registry/OLLAMA_MODEL_REGISTRY.json` or run pulls with `RE_PULL_ARCHIVED=1` / `IGNORE_PULL_HISTORY=1` as documented in `ollama-pull-queue` header — align policy with your real **`OLLAMA_HOME`**.

## Refresh kit from workstation

```bash
rsync -az --delete --exclude '.venv/' --exclude 'uv.lock' \
  /path/to/ollama-hosting/ \
  ubuntu@192.168.8.32:~/z/env/ai/ollama/
scp /path/to/ollama-hosting/config/env-archive-vm.sh \
  ubuntu@192.168.8.32:~/z/env/ai/ollama/env-archive-vm.sh
```

(Adjust remote paths if your checkout on the VM is not under **`~/z/env/ai/ollama`**.)

## Binary install (no root)

The `ollama` client binary can be copied from Supermicro (`/usr/local/bin/ollama`) to `~/.local/bin/ollama` on the VM. To upgrade: repeat from a host that has a newer `ollama`, or extract `ollama-linux-amd64.tar.zst` from [GitHub releases](https://github.com/ollama/ollama/releases).
