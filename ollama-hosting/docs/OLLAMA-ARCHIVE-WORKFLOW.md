# Ollama download → archive → supermicro offload (single picture)

## Objective

1. **Download** Ollama tags we care about (registry may drop models later).
2. **Archive** completed blobs on the **archival VM** where there is disk.
3. **Free the Supermicro** `~/.ollama` cache so the next large model can download.

This file is the **conceptual source of truth** for that loop. **Machine-readable state** for “what we want, what pulled, what landed on archive, what we cleared locally” lives in **`OLLAMA_MODEL_REGISTRY.json`**, updated with **`ollama_registry_tool.py`** (see below). Heavy automation (rsync, integrity, inventory YAML) stays in **`model-archival/ollama-hosting`**.

### Policy: one-way from archival VM to Supermicro (weights and kits)

**Do not** rsync, scp, or otherwise **deploy from the archival VM back to Supermicro** — no pushing the pull kit, registry edits, or Ollama trees from the archival VM (e.g. `ubuntu@192.168.8.32`) → `192.168.8.106`. The archive VM is a **sink** for blobs and HF data; Supermicro is refreshed from **git + workstation** (or CI) via **`deploy-ollama-pull-kit-to-supermicro.sh`**, and weight flow is **Supermicro → archival VM** only (`ollama-sync.sh` / `ollama-registry-sync`).

### Operator sequence (expected)

1. **Finalize queue** in **`registry/`** (this repo).
2. **Deploy** to Supermicro **`~/z/dev/ollama/`**: **`scripts/deploy-ollama-pull-kit-to-supermicro.sh`** (rsync `registry/` + pull scripts).
3. **Pull** on Supermicro: **`~/z/dev/ollama/scripts/ollama-pull-queue`** (or **`trigger-ollama-pull-on-supermicro.sh`** from your workstation).
4. **Poll / copy cache to archive VM disks** — from a bridge host with SSH to Supermicro + VM: **`scripts/ollama-registry-sync`** (runs **`ollama-sync.sh`** rsync, then manifest + registry merges). Re-run **manually** (or your own scheduler) after known completes; partial blobs stay on Supermicro until pulls finish.

---

## What `ollama-sync.sh` does today (and what it does not)

Implemented in `~/z/dev/model-archival/model-archival/ollama-hosting/scripts/ollama-sync.sh`:

| Behavior | Detail |
|----------|--------|
| **Completed weights only** | By default **excludes** `models/blobs/*partial*` (in-flight shards). Only finished blob sets that Ollama has written normally get copied. |
| **Additive archive** | **No `--delete`** on the VM side: old blobs stay if you `ollama rm` on Supermicro after a sync. Safe for “backup before registry loss.” |
| **Destination** | Default cycle is **`/mnt/models/d5/supermicro`** (see `OLLAMA-CACHE-POLICY.md`). Override with **`ARCHIVAL_VM_DEST`** or **`ARCHIVAL_VM_SITE_CYCLE`**. |
| **After sync** | Optional VM **maintain** + **manifest↔blob integrity**; optional **inventory** refresh → **`OLLAMA-ARCHIVAL-MODEL-MAP.md`** + **`ollama-archival-global-manifest.yaml`**. |

It does **not** (today):

- **Pick the disk by free space** — rotation is **round-robin over the configured cycle**, not “largest `df` wins.” To spread load by capacity, extend **`ollama_archival_rotation.py`** in ollama-hosting (future) or set **`ARCHIVAL_VM_DEST`** per run after checking `df`.
- **Automatically `ollama rm` on Supermicro** — that stays **operator-driven** after you confirm the tag is on the archive and integrity is clean (see §4).

---

## End-to-end loop (recommended)

```text
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────────────┐
│ Supermicro      │     │ ollama-sync.sh       │     │ Archival VM             │
│ ollama pull …   │────►│ rsync ~/.ollama       │────►│ /mnt/models/dX/…        │
│ (queue below)   │     │ (no partial blobs)   │     │ additive backup         │
└────────┬────────┘     └──────────────────────┘     └───────────┬─────────────┘
         │                                                          │
         │         ┌────────────────────────────────────────────────┘
         │         │  Inventory refresh → global manifest + model map
         ▼         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Confirm tag + blobs on VM (OLLAMA-ARCHIVAL-MODEL-MAP.md or manifest YAML)   │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ ollama rm tag   │  ← only after verification; frees Supermicro disk
└─────────────────┘
```

---

## One global list (`ollama-hosting/`)

**Queue priorities** (what to add / how high to sort pulls) are documented in **`docs/TARGET_MODEL_LIST.md`** (“Acquisition priorities” + review cadence). The mechanical pull order is always the **`registry.queue`** / **`registry/TARGET_QUEUE_ORDERED.txt`** sequence — update that when strategy changes.

---

| Artifact | Role |
|----------|------|
| **`registry/OLLAMA_MODEL_REGISTRY.json`** | **Canonical:** ordered **queue**, per-tag **pull** state (from CSV / tool), **archive** fields (merged from `ollama-archival-global-manifest.yaml` when you run merge). |
| **`registry/TARGET_QUEUE_ORDERED.txt`** | **Pull script input** — one tag per line. **Preferred:** edit this file, then merge into JSON (see `ollama_registry_tool.py init` — or sync queue in JSON without wiping archive fields). |
| **`registry/TARGET_PULL_HISTORY.csv`** | **Append-only** log of `ollama pull` attempts. Fold into registry: `python3 ollama_registry_tool.py merge-pull-history`. |
| **`docs/TARGET_MODEL_LIST.md`** | Human notes (sizes, HF mapping, throttle policy, **`group`** taxonomy). |

**Primary scripts (`ollama-hosting/scripts/`):**

| Script | Role |
|--------|------|
| **`ollama-registry-sync`** | Runs **`scripts/ollama-sync.sh`**, then merges manifest + **`registry/TARGET_PULL_HISTORY.csv`** into **`registry/OLLAMA_MODEL_REGISTRY.json`**. |
| **`ollama-pull-queue`** | On the **Ollama host**, pulls tags that still need a download. **Skips** tags already **`pull.complete`** or with **`archive.on_canonical_disk`** set (weights on archival VM — run **`merge-manifest`** / **`ollama-registry-sync`** so the registry knows). **`RE_PULL_ARCHIVED=1`** forces re-pull to Supermicro. **`sync-pull-from-archive`** (registry tool) marks archived tags complete and appends CSV rows. |
| **`ollama-clean-partials`** | On the **Ollama host**, **inspect** `models/blobs/*partial*` by default (Ollama can **resume** pulls — partials stay). **`--delete`** removes them; **`--delete --older-than N`** only stale shards. |

```bash
# Workstation / bridge host (from ollama-hosting/):
./scripts/ollama-registry-sync

# Supermicro (GPU host); copy or mount this repo, then:
export OLLAMA_HOST=127.0.0.1:11434
./scripts/ollama-pull-queue                # one model per run by default (~4 MiB/s via trickle)
```

**Registry maintenance (from `ollama-hosting/registry/`):**

```bash
cd registry   # inside ollama-hosting
python3 ollama_registry_tool.py init

python3 ollama_registry_tool.py merge-manifest \
  ~/z/dev/model-archival/model-archival/ollama-hosting/docs/data/ollama-archival-global-manifest.yaml

python3 ollama_registry_tool.py merge-pull-history
python3 ollama_registry_tool.py sync-pull-from-archive --history TARGET_PULL_HISTORY.csv
python3 ollama_registry_tool.py export-queue
python3 ollama_registry_tool.py status
python3 ollama_registry_tool.py list-pending
python3 ollama_registry_tool.py list-group uncensored
python3 ollama_registry_tool.py apply-default-groups
```

**Adding a newly discovered model**

1. Add the tag to **`registry/OLLAMA_MODEL_REGISTRY.json`** → `queue` array (position = priority) and a **`models.<tag>`** object (at least `"approx_size_gb": null` and empty `pull` / `archive` stubs — copy an existing entry).
2. Run **`export-queue`** so **`registry/TARGET_QUEUE_ORDERED.txt`** matches.
3. Optionally run **`merge-manifest`** after the next successful sync so archive columns stay aligned with ollama-hosting.

---

## Related repos / paths

| Where | What |
|-------|------|
| `model-archival/…/ollama-hosting/scripts/ollama-sync.sh` | Sync job |
| `model-archival/…/docs/OLLAMA-CACHE-POLICY.md` | Single vs multi-disk policy, rotation |
| `model-archival/…/docs/data/ollama-archival-global-manifest.yaml` | **Authoritative** “which tag on which disk” after inventory |
| `model-archival/…/docs/OLLAMA-ARCHIVAL-MODEL-MAP.md` | Human-readable map |
| `ollama-hosting/docs/OLLAMA-ONE-DISK-OFFLOAD.md` | Short operator loop before `ollama rm` |
| `ollama-hosting/systemd/` | **Timer removed** — see **`README-ollama-sync-timer.md`** to disable any previously installed units |

---

## Contradictions we are resolving

- **“One disk only”** (d5) vs **“use every VM disk with space”** — policy is configurable via **`ARCHIVAL_VM_SITE_CYCLE`**. Spreading across d2/d3/d1 is fine if you **avoid duplicate full mirrors** unless you intend redundancy; see **`OLLAMA-CACHE-POLICY.md`**.
- **TARGET_MODEL_LIST vs CSV vs queue file** — registry + tool unify **intent + state**; markdown stays narrative and sizing tables.
