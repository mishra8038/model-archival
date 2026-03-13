# Disks and Distribution of Artifacts

Physical disk layout, roles, and how artifacts are distributed across drives.

---

## Disk layout (VM)

| Label | Device  | Mount           | Size   | Role |
|-------|---------|-----------------|--------|------|
| D1    | /dev/sdc | /mnt/models/d1 | 5.5 TB | Large Tier A/B models + `.tmp/` scratch |
| D2    | /dev/sdd | /mnt/models/d2 | 2.7 TB | Mid-size Tier A/B + Tier D uncensored raw |
| D3    | /dev/sde | /mnt/models/d3 | 2.7 TB | Tier C/D GGUF, Tier E/F/G (reasoning, vision, math, research) |
| D5    | /dev/sdb | /mnt/models/d5 | 916 GB | Metadata, logs, state, STATUS.md, tooling-archive |

- **Root SSD:** No model data. Only Python env and logs symlink. All important writes use atomic semantics (write to `.tmp` then rename).
- **Before reboot:** Always run `local/stop.sh` and wait for "stopped cleanly" to avoid filesystem corruption on model drives.

---

## Distribution of artifacts by drive

### D1 — /mnt/models/d1

- **Model weights:** Tier A large (DeepSeek-V3, DeepSeek-R1, Qwen3-32B, Qwen3-235B-A22B, Llama-3.1-405B, Llama-3.3-70B, Mistral-Large, Command R+, DeepSeek-Coder-V2-Instruct), Tier F large (Qwen2.5-VL-72B, Llama-3.2-90B-Vision).
- **Scratch:** `D1/.tmp/` — in-progress downloads only; ~2.3 TB headroom for partials.
- **Fingerprints:** `D1/model-checksums/` — default output for the checksum crawler (index.jsonl, per-repo fingerprint files, leaderboard-snapshots).
- **Code archival:** `D1/code-archival/` — source snapshots from code-archival (if configured to use D1).
- **Role (drives.yaml):** "Raw giants (Tier A large + Tier B large)" + tmp_dir for scratch.

### D2 — /mnt/models/d2

- **Model weights:** Tier A mid-size (DeepSeek distills, Qwen2.5/3 72B→7B, Llama-3.1-70B/8B, Gemma 3, Mistral-Small-24B, Phi-4, Command R+ 08-2024, Nemotron-70B, Tulu-3-70B), Tier B (Qwen2.5-Coder, Qwen3-Coder-30B-A3B, DeepSeek-Coder-V2-Lite, Devstral, Codestral, OlympicCoder, StarCoder2), Tier D raw (huihui-ai abliterated, Dolphin, mlabonne, etc.).
- **Role (drives.yaml):** "Raw mid-size (Tier A remainder + Tier B small + Tier D uncensored raw)". Note: D2 may be marked FULL; no new writes in that case.

### D3 — /mnt/models/d3

- **Model weights:** Tier C GGUF (unsloth DeepSeek-R1/V3, bartowski distills and instruct GGUF, Qwen, Llama, Mistral, Phi-4, Gemma, Codestral, Devstral), Tier D GGUF (tensorblock/mlabonne abliterated GGUF), Tier E (QwQ-32B, OlympicCoder, Sky-T1), Tier F small (Qwen2.5-VL-7B, Gemma-3-4b-it, Llama-3.2-11B-Vision), Tier G (Qwen2.5-Math, DeepSeek-R1-Distill-Qwen-7B).
- **Role (drives.yaml):** "Quantized GGUF (Tier C + Tier D quants)" plus research/experimental/reasoning/vision/math as documented in the registry.

### D5 — /mnt/models/d5

- **State and dashboard:** `run_state.json`, `STATUS.md`, run reports.
- **Metadata archive:** `archive/` — replicated to all drives after each model completion (weight files are not duplicated).
- **Logs:** `logs/` (often symlinked from project root).
- **Tooling mirrors:** `tooling-archive/<id>.git` — bare git repos for tooling projects from registry.
- **Role (drives.yaml):** "Metadata: archive/, logs, run_state.json, STATUS.md".

---

## Design rules

- **No model data on root SSD.** All weight and scratch I/O goes to D1/D2/D3.
- **Scratch only on D1.** In-progress downloads and `.tmp` live in `D1/.tmp/`; never on D5 or root.
- **D5 is source of truth for status.** run_state.json and STATUS.md live only on D5; archive/ is then synced to other drives.
- **Space-aware placement.** Large BF16 models on D1/D2; GGUF and research on D3. When adding models, check drive usage and topology (future `config/topology.yaml` or equivalent).
- **Physical disk IDs.** Optionally fill `by_id` and `serial` in drives.yaml so drive roles can be restored after VM/host or Proxmox mapping changes.
