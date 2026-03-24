# Registry gaps filled (ChemDFM, MedGemma, DBRX, retrosynthesis)

Added HF rows that were missing from prior coverage:

| `hf_repo` | Notes |
|-----------|--------|
| `OpenDFM/ChemDFM-v1.5-8B` | LLaMA-3-8B-based chemistry dialogue |
| `OpenDFM/ChemDFM-v2.0-14B` | Qwen2.5-14B-based v2 |
| `OpenDFM/RetroDFM-R-v0-8B` | Retrosynthesis LLM; **DeepRetro** is a framework (no single HF weights repo) |
| `google/medgemma-27b-text-it`, `medgemma-4b-it`, `medgemma-27b-it` | Gated — `requires_auth: true`, Gemma / Health AI ToU |
| ~~`databricks/dbrx-base`, `databricks/dbrx-instruct`~~ | **Removed (2026-03-23):** no longer reliably available from Databricks on Hugging Face. |

**RDKit:** still not a model — software dependency only (called out in RetroDFM/ChemDFM notes on main registry).

Files: `model-archival/config/registry.yaml`, `model-archival/config/registry-specialists.yaml` (mirrored for `-r config/registry-specialists.yaml` runs).

Validation: `load_registry` + `check_registry` OK for both files.

## 2026-03-22 — priority 0 + VM start

- Set **`priority: 0`** on all eight rows in both `registry.yaml` and `registry-specialists.yaml` (scheduler sorts effective priority ascending → these run before any `priority: 1+` model).
- **Deployed** registries to VM: `scp` → `/home/x/dev/model-archival/model-archiver/config/` (this repo’s canonical VM path is `model-archiver`, not `model-archival/`).
- Stopped a stale **`registry-specialists.yaml`** run (PID 18172); `scripts/stop.sh` can match the wrong process if `pgrep -f "archiver download"` hits a `bash -c` wrapper — prefer `--status` / PID file when debugging.
- Started **`screen -S archiver`** with **`bash scripts/run.sh --all --registry config/registry.yaml --skip-drive-space-check`** (full main queue + scheduled cap 0.75 MB/s 07:00–23:00). Previous long-running job used specialists only; switch to main registry was intentional so the new rows participate in the default queue.
