# Ollama one-disk offload loop (supermicro → VM d5)

**See first:** [`OLLAMA-ARCHIVE-WORKFLOW.md`](OLLAMA-ARCHIVE-WORKFLOW.md) (full pipeline + **`registry/OLLAMA_MODEL_REGISTRY.json`**). This page is the short operator checklist.

**Policy:** Default is **one** canonical Ollama archive root (**`/mnt/models-d5/ollama`** on **`ubuntu@192.168.8.32`**). To use **multiple VM disks** without duplicate full mirrors, set **`ARCHIVAL_VM_SITE_CYCLE`** in `ollama-sync.sh` / env (see `OLLAMA-CACHE-POLICY.md`). Rotation does **not** yet auto-pick “most free space.”

## Loop (repeat until you change policy)

1. **Sync** supermicro `~/.ollama` → VM **d5** (run **`ollama-registry-sync`** manually when needed).
2. **Verify** the model you want to retire is represented on the archive:
   - `ollama-hosting/docs/OLLAMA-ARCHIVAL-MODEL-MAP.md`
   - `ollama-hosting/docs/data/ollama-archival-global-manifest.yaml`
   - Optional: `ssh x@ARCHIVAL_VM 'test -f …/manifests/…'` for that tag.
3. **Confirm integrity** — the sync job runs `ollama_archive_vm_maintain.py` after each success; fix any reported missing blobs before deleting on supermicro.
4. **Remove from supermicro** (only after steps 2–3):  
   `ollama rm <model:tag>`  
   Use `ollama-hosting/scripts/ollama-supermicro-prune-plan.sh` / keep rules in `OLLAMA-CACHE-POLICY.md` (e.g. keep Gemma 4 + Qwen Coder on GPU box if that is still the goal).

## What not to do

- Do not `ollama rm` before the tag’s layers exist on **d5** and integrity is clean.
- Do not start a second full mirror on another disk unless you are **migrating**; then remove the old tree after cutover.

## Changing the archive disk later

Set a fixed destination for one run, then update defaults:

```bash
export ARCHIVAL_VM_SITE_CYCLE='d3=/mnt/models-d3/ollama'
# or ARCHIVAL_VM_DEST=/mnt/models-d3/ollama for a single run
```

Update `ollama_archival_rotation.py` / inventory defaults if this becomes permanent.
