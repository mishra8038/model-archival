# Ollama archival sync — job specification

**Job name:** Ollama cache sync (Supermicro → archival VM)  
**Primary script:** `../scripts/ollama-sync.sh`  
**Policy:** **Additive archive** — rsync **never** uses `--delete*`; destination files absent from the source are retained.

**Inverse:** there is **no** operational rsync of pull kits, registry, or Ollama trees **from the archival VM to Supermicro** — VM is sink-only for this job; refresh Supermicro from git (`deploy-ollama-pull-kit-to-supermicro.sh`). See **`OLLAMA-ARCHIVE-WORKFLOW.md`**.

## Actors and paths

| Role | Default SSH | Default path |
|------|-------------|--------------|
| Ollama source (Supermicro) | `x@192.168.8.106` | `~/.ollama` (`OLLAMA_REMOTE_DIR`) |
| Archival VM | `ubuntu@192.168.8.32` | Default archive: `/mnt/models-d5/ollama` (single copy; override with `ARCHIVAL_VM_SITE_CYCLE`) |

Override with **`SUPER_OLLAMA_REMOTE`**, **`ARCHIVAL_VM`**, **`ARCHIVAL_VM_DEST`** (fixed dest skips rotation advance), **`ARCHIVAL_VM_SITE_CYCLE`**.

## Execution modes

- **`OLLAMA_SYNC_DEST=vm`** (default): copy to archival VM.
- **`OLLAMA_SYNC_DEST=local`**: copy to a local directory (e.g. disk mounted on workstation); **`OLLAMA_D5_DEST`** sets the target.

## Transfer strategies (VM mode)

Tried in order:

1. **VM pull** — SSH to the VM and run `rsync` from there to Supermicro (best when the VM can reach Supermicro on SSH).
2. **Bridge** — If (1) fails, the workstation runs **`sshfs`** to mount Supermicro’s Ollama tree, then `rsync` from the workstation to the VM (for topologies where the VM cannot open SSH to the GPU host).

Set **`OLLAMA_SKIP_VM_PULL=1`** to skip (1) and use the bridge immediately.

## Completed weights only (default)

By default the job **excludes** incomplete Ollama shards:

- `models/blobs/*partial*`
- `.rsync-partial/` at the Ollama cache root

Set **`OLLAMA_SYNC_INCLUDE_PARTIALS=1`** to mirror the **full** Supermicro cache (including in-flight downloads) so **`OLLAMA_HOME`** on the archive VM can **resume** pulls. Post-sync maintain then keeps `*partial*` files (**`--keep-ollama-partials`**). See **`OLLAMA-RESUME-ON-ARCHIVE-VM.md`**.

## Post-sync maintenance (VM)

When **`OLLAMA_SYNC_VM_MAINTAIN`** is non-zero (default), after a successful VM sync the job streams **`ollama_archive_vm_maintain.py`** to the archival VM and runs it on **every** root in the rotation cycle: remove stray `*partial*` blobs (unless **`OLLAMA_SYNC_INCLUDE_PARTIALS=1`** or **`OLLAMA_MAINTAIN_KEEP_PARTIALS=1`**), prune `.rsync-partial` trees, then print manifest↔blob integrity. Set **`OLLAMA_SYNC_VM_MAINTAIN=0`** to skip.

## Destination rotation

If **`ARCHIVAL_VM_DEST`** is **unset**, `ollama_archival_rotation.py` picks the next path from the cycle, records the run in **`docs/data/ollama-sync-rotation.state`**, and advances **`next_index`** after success. A **fixed** `ARCHIVAL_VM_DEST` does **not** advance the cursor.

Default cycle: **d5** only (`/mnt/models-d5/ollama`). Set **`ARCHIVAL_VM_SITE_CYCLE`** to add or move targets.

## Inventory and human map

When **`OLLAMA_SYNC_UPDATE_INVENTORY`** is non-zero (default) and **`uv`** is available:

1. **`update_ollama_vm_inventory.py`** refreshes **`docs/data/ollama-vm-models-inventory.yaml`** (SSH to VM or local root).
2. **`generate_ollama_archival_map.py`** rebuilds **`docs/OLLAMA-ARCHIVAL-MODEL-MAP.md`**.

Extra CLI flags for inventory (e.g. infer **`supermicro_cleared`**): **`OLLAMA_VM_INVENTORY_EXTRA`**.

## Bandwidth and SSH

| Variable | Meaning |
|----------|---------|
| **`OLLAMA_SYNC_BWLIMIT_KB`** | rsync `--bwlimit` in KiB/s (default **`0`** = unlimited on LAN; set e.g. `4096` to cap WAN or shared links) |
| **`SSHPASS` / `VM_SSHPASS`** | Optional; use with **`sshpass`** for password-based SSH |
| **`RSYNC_EXTRA`** | Extra rsync args; **delete/remove flags are stripped** |

## Passwords and safety

- Do not commit secrets; use env or your shell profile.
- Before Supermicro **prune** (`ollama rm`), confirm the same **`model:tag`** exists on the VM archive — use **`docs/OLLAMA-ARCHIVAL-MODEL-MAP.md`** and **`scripts/ollama-supermicro-prune-plan.sh`**.

## Back-compat wrapper

`sync-supermicro-ollama-to-d5.sh` is a thin **`exec`** of **`ollama-sync.sh`**.
