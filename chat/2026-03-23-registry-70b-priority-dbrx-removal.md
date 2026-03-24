# Registry: 70B+ → priority 4; DBRX removed

## DBRX

- Dropped **`databricks/dbrx-base`** and **`databricks/dbrx-instruct`** from **`model-archival/config/registry.yaml`** and **`model-archival/config/registry-specialists.yaml`** (weights not reliably available on HF from Databricks).
- If D5 **`run_state.json`** still has rows for those IDs, remove or mark skipped on the VM when convenient.

## 70B+ → lowest normal priority (`priority: 4`)

- In both registries, models that are **≥70B by id/hf_repo** (plus **full DeepSeek V3/R1**, **8×22B Mixtral-class**, **Grok-2**, **large Nemotron**, **Falcon-180B**, **405B Llama**, **671-class GGUF** names, etc.) are set to **`priority: 4`** (lowest band in `0–4` policy).
- **`registry.yaml` only:** also set **`mistralai/Mistral-Large-Instruct-2411`** and all **`meta-llama/Llama-4-*`** entries to **`priority: 4`** (large / MoE flagship class; not parsed from digits in id).
- **False-positive fix:** **`Salesforce/CoDA-*`** and **`apple/DiffuCoder-*`** in **`registry.yaml`** were briefly bumped to `4` because notes mentioned “130B tokens”; restored to **`1`** / **`2`** to match specialist registry and actual model size.

## Operational

- Re-sync YAML to the archiver VM and restart if you want the live queue to match.
- **`priority_overrides.json`** on D5: remove keys for deleted DBRX ids if present.
