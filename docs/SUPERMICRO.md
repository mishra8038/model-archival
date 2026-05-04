# Supermicro GPU host (Ollama + local inference)

This document situates the **Supermicro 1028GQ-TXR** in the model-archival monorepo: what it is for, where configuration lives in git, and how it connects to the **archival VM** and Hugging Face archiver.

---

## Role in the monorepo

| Function | Where it runs | What the monorepo holds |
|----------|---------------|-------------------------|
| **Served Ollama weights** (GGUF-class blobs, multi-GPU inference) | Supermicro LAN host | Mirror of pull scripts, model queues, `ollama.service`, and client env **examples** under **`ollama-hosting/supermicro-rig/`** |
| **Rsync archive** of `~/.ollama` → disk VM | Workstation or VM triggers | **`ollama-hosting/scripts/ollama-sync.sh`**, rotation state, inventory — see **`ollama-hosting/docs/SYNC-JOB.md`** |
| **HF weight archival** (safetensors / full trees) | Archival VM (`/mnt/models-d1` … **`/mnt/models-d5`**) | **`model-archival/`** — separate from Ollama’s blob layout |

Supermicro is **not** the primary home of `run_state.json` or the HF archiver; it is the **hot inference + Ollama pull** box. After models are copied to the archival VM, you may prune the Supermicro cache per **`ollama-hosting/docs/OLLAMA-CACHE-POLICY.md`**.

**Deploy direction:** do **not** push pull kits, registry files, or Ollama data **from the archival VM to Supermicro**. Treat the VM as archive-only for that flow; update Supermicro from **git** (e.g. **`ollama-hosting/scripts/deploy-ollama-pull-kit-to-supermicro.sh`** from a dev machine). See **`ollama-hosting/docs/OLLAMA-ARCHIVE-WORKFLOW.md`**.

---

## Canonical paths

| Kind | Path |
|------|------|
| **In-repo mirror** (pull lists, scripts, systemd unit, Aider/Hermes/OpenClaw examples) | `ollama-hosting/supermicro-rig/` |
| **Full host bootstrap narrative** (hardware, NVIDIA, Gemma tags, long-running pull instructions) | `ollama-hosting/supermicro-rig/SUPERMICRO-HOST-README.md` (copy of `~/z/env/dev-environment/supermicro/README.md`) |
| **Live operator tree** (edit here first, then refresh the repo mirror) | `~/z/env/dev-environment/supermicro/` on your workstation or the host |

When the dev-environment tree changes, copy updated files into **`ollama-hosting/supermicro-rig/`** so the monorepo stays the durable reference.

---

## Network anchors (typical)

| Host | Role | Default SSH (examples in scripts) |
|------|------|-----------------------------------|
| Supermicro | Ollama `:11434`, pulls | `x@192.168.8.106` |
| Archival VM | `/mnt/models-d1` … `/mnt/models-d5`, HF archiver, Ollama **archive** roots | `ubuntu@192.168.8.32` |

Adjust with **`SUPER_OLLAMA_REMOTE`**, **`ARCHIVAL_VM`**, and related env vars documented in **`ollama-hosting/docs/SYNC-JOB.md`**.

---

## Hardware summary (from host README)

- **Model:** Supermicro 1028GQ-TXR  
- **RAM:** 256 GB  
- **GPUs:** 4× Tesla P100-SXM2-16GB  
- **OS:** Ubuntu 24.04.x (see **`SUPERMICRO-HOST-README.md`** for kernel/driver notes)  

Pascal has no native **bfloat16**; Ollama stacks in this project target **Q4_K_M / Q8_0** (and similar) rather than BF16 blobs.

---

## Operator checklist

1. **Service:** `systemctl status ollama` — listen **`0.0.0.0:11434`** if LAN clients are used.  
2. **Pulls:** prefer **`ollama-hosting/scripts/ollama-pull-queue`** (default one model per run, ~4 MiB/s via `trickle`; registry + **`registry/TARGET_QUEUE_ORDERED.txt`**); or **`supermicro-rig/scripts/pull-ollama-stack.sh`** (symlink to **`../scripts/`**). Queue files under **`supermicro-rig/models/`** symlink **`../registry/`**.  
3. **Stuck partials:** **`ollama-hosting/scripts/ollama-clean-partials`** — default inspect-only; **`--delete`** only when abandoning resume (see script header).  
4. **Archive:** `cd ollama-hosting && ./scripts/ollama-sync.sh` — optional **`./scripts/ollama-registry-sync`** to merge manifest + CSV into **`registry/OLLAMA_MODEL_REGISTRY.json`** (see **SYNC-JOB**).  
5. **Prune supermicro:** only after VM copy is verified — **`ollama-hosting/docs/OLLAMA-ARCHIVAL-MODEL-MAP.md`** and **`scripts/ollama-supermicro-prune-plan.sh`**.

---

## Related documentation

| Document | Purpose |
|----------|---------|
| [`../ollama-hosting/README.md`](../ollama-hosting/README.md) | Layout of `ollama-hosting/`, `uv sync`, quick commands |
| [`../ollama-hosting/docs/SYNC-JOB.md`](../ollama-hosting/docs/SYNC-JOB.md) | Ollama rsync job specification |
| [`../ollama-hosting/docs/OLLAMA-CACHE-POLICY.md`](../ollama-hosting/docs/OLLAMA-CACHE-POLICY.md) | Retention, rotation, inventory files |
| [`PROJECT-PROMPT-AND-REQUIREMENTS.md`](PROJECT-PROMPT-AND-REQUIREMENTS.md) | Whole-monorepo prompt + subprojects |
| [`PROJECTS.md`](PROJECTS.md) | Per-directory summary including **`ollama-hosting/`** |
