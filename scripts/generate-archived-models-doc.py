#!/usr/bin/env python3
"""Emit docs/ARCHIVED-MODELS.md from registries (run from repo root)."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
MA = REPO / "model-archival/config/registry.yaml"
LEG = REPO / "model-archival/config/registry-legacy.yaml"
SP = REPO / "model-archival/config/registry-specialists.yaml"
OUT = REPO / "docs/ARCHIVED-MODELS.md"


def bullets(ids: list[str]) -> str:
    return "\n".join(f"- `{x}`" for x in ids)


def main() -> None:
    root = yaml.safe_load(MA.read_text())
    entries = root["models"]
    n_entries = len(entries)
    ids_unique = sorted({e["id"] for e in entries})
    n_unique = len(ids_unique)

    by_tier: dict[str, int] = {}
    for e in entries:
        t = e.get("tier", "?")
        by_tier[t] = by_tier.get(t, 0) + 1

    d_ids = sorted(e["id"] for e in entries if e.get("tier") == "D")
    unc_pat = re.compile(
        r"abliterat|lorablat|dolphin|Dolphin|huihui-ai|tensorblock|mlabonne|failspy|"
        r"CombinHorizon|FINGU-AI|rombodawg|cognitivecomputations",
        re.I,
    )
    unc_core = sorted(x for x in d_ids if unc_pat.search(x))
    other_d = sorted(x for x in d_ids if x not in unc_core)

    def tier_ids(t: str) -> list[str]:
        return sorted(e["id"] for e in entries if e.get("tier") == t)

    E = tier_ids("E")
    guards = sorted(
        x for x in E if x.startswith(("meta-llama/Llama-Guard", "meta-llama/Llama-Prompt-Guard"))
    )
    reasoning_e = sorted(x for x in E if x not in guards)
    F = tier_ids("F")
    G = tier_ids("G")

    leg = yaml.safe_load(LEG.read_text())
    legacy_ids = sorted({m["id"] for m in leg["models"]})

    sp_root = yaml.safe_load(SP.read_text())
    sp_ids = sorted(m["id"] for m in sp_root["models"])

    today = date.today().isoformat()

    tier_desc = {
        "A": "Frontier general / instruct / MoE bases",
        "B": "Code models, embeddings, some tabular",
        "C": "GGUF quant checkpoints (bartowski / unsloth / tensorblock / Qwen releases)",
        "D": "Uncensored / abliterated / merges + some large Nemotron (drive placement)",
        "E": "Reasoning, long-CoT, guards",
        "F": "Vision, multimodal, medical VL",
        "G": "Math, chemistry, diffusion code, research",
    }
    tier_table = "\n".join(
        f"| **{t}** | {tier_desc.get(t, 'see registry notes')} | {by_tier[t]} |"
        for t in sorted(by_tier.keys())
    )

    dup_note = ""
    if n_entries != n_unique:
        dup_note = (
            f"\n> **Note:** The master registry has `{n_entries}` rows but only `{n_unique}` "
            "distinct `id` values (`open-r1/OlympicCoder-32B` appears twice). "
            "Consider deduplicating `registry.yaml`.\n\n"
        )

    body = f"""# Archived models — inventory

This document summarises what the **model-archival** monorepo is configured to preserve.
**Authoritative sources** are the YAML registries; this file can be regenerated from the repository root with:

`uv run --directory model-archival python3 ../scripts/generate-archived-models-doc.py`

**Last regenerated:** {today}

---

## Scope across subprojects

| Subproject | What is archived | Authoritative file | Scale (this snapshot) |
| ---------- | ---------------- | ------------------ | --------------------- |
| **model-archival** | Full Hugging Face weight trees (safetensors / GGUF) | `model-archival/config/registry.yaml` | **{n_entries}** registry rows (**{n_unique}** unique `id` values) |
| **model-archival** (legacy queue) | Older or superseded chat models (optional `--registry` / `--include-legacy`) | `model-archival/config/registry-legacy.yaml` | **{len(legacy_ids)}** models |
| **model-archival** (specialist queue) | STEM, biomedical, legal, math, vision, reward, extended niche targets | `model-archival/config/registry-specialists.yaml` | **{len(sp_ids)}** models |
| **fingerprints** | LFS SHA-256 fingerprints only (no weights) | `fingerprints/config/registry.yaml` | **~2,769** repos (see file header; leaderboard-scale) |
| **code-archival** | GitHub tarballs + shallow clones of AI tooling | `code-archival/registry.yaml` | **245** projects |
| **gdrive-archival** | Optional cloud replica of selected trees | `gdrive-archival/gdrive-registry.yaml`, staging dirs | varies |

**Download state** (pending / complete / failed) for weights lives on the metadata drive in `run_state.json`, not in this repo.

---

## Tier counts (master weight registry)

Distribution of `tier` in `registry.yaml` (rows, not unique ids):

| Tier | Role (summary) | Count |
| ---- | -------------- | ----- |
{tier_table}

{dup_note}---

## Uncensored, abliterated, and alignment-relaxed weights

These are **community or merge models** aimed at reduced refusals, abliterated instruction tuning,
Dolphin-family uncensored chat, or related GGUF packs. They are the subset of **tier D** that matches
abliteration / Dolphin / huihui-ai / tensorblock / similar naming (**{len(unc_core)}** models).

{bullets(unc_core)}

### Tier D — large checkpoints (not “uncensored” branding)

The remaining **tier D** rows are **NVIDIA Nemotron** scale checkpoints grouped on tier D for capacity / policy; they are not abliterated variants.

{bullets(other_d)}

---

## Specialty and domain models

### By tier in the master registry

**Tier E — reasoning, games / long CoT**

{bullets(reasoning_e)}

**Tier E — safety / guardrails**

{bullets(guards)}

**Tier F — vision, multimodal, medical VL**

{bullets(F)}

**Tier G — math, chemistry, code-diffusion, tabular, research**

{bullets(G)}

### Specialist registry (`registry-specialists.yaml`)

Curated queue for **biomedical**, **chemistry**, **legal**, **math**, **embeddings**, **vision**,
**reward models**, **DBRX**, **Grok**, Nemotron variants, and related GGUF / abliterated complements.
Many entries overlap the master list; use this file when running a **specialist-first** download pass.

{bullets(sp_ids)}

---

## Legacy registry (`registry-legacy.yaml`)

Excluded from default `--all` runs unless you pass the legacy registry and `--include-legacy`.
**{len(legacy_ids)}** models:

{bullets(legacy_ids)}

---

## Complete master list (`registry.yaml`)

All **unique** `id` values in the master registry (**{n_unique}** models):

{bullets(ids_unique)}
"""
    OUT.write_text(body, encoding="utf-8")
    print(f"Wrote {OUT} ({n_unique} unique master ids)")


if __name__ == "__main__":
    main()
