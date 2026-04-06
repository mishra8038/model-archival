# Why `ollama-sync.sh` mirrors — it does not “offload” Supermicro by itself

## What the default pipeline does

`ollama-sync.sh` / `ollama-registry-sync` use **rsync without `--delete`**. That means:

- **Additive copy:** blobs and manifests from Supermicro `~/.ollama` are **added or updated** on the archival VM path (default `/mnt/models/d5/supermicro`).
- **No automatic removal** on Supermicro after sync. The GPU host keeps a full local copy until **you** run `ollama rm <tag>` (or delete blobs) after you trust the archive.

So operationally this is a **backup / mirror to big disk**, not an automatic **move** that frees the small Supermicro disk.

## What “offload” requires (manual step)

1. Sync completes and (optional) VM integrity passes.
2. Confirm models on the VM (`OLLAMA-ARCHIVAL-MODEL-MAP.md` / manifest YAML).
3. **Then** remove from Supermicro: `ollama rm …` per your retention policy (`OLLAMA-CACHE-POLICY.md`).

Automation could be added later (e.g. scripted `ollama rm` after checks); it is **not** the current default to avoid deleting weights before archive verification.

## Alternative: pull directly on the archive VM

If the GPU box should stay thin and the VM has space and (optional) CPU inference, install Ollama on the VM, set **`OLLAMA_HOME`** to a large mount (e.g. `/mnt/models/d2/ollama`), and run **`ollama-pull-queue`** there. See **`OLLAMA-ARCHIVE-VM-HOST.md`**.
