#!/usr/bin/env python3
"""Emit docs/ARCHIVED-MODELS.md from registries (run from repo root).

Enriches the master registry with expected on-disk paths, optional download status
(run_state.json), optional GDrive registry-upload tracker, and live dir/manifest
checks when those paths exist on the machine running this script.

Environment (optional):
  ARCHIVER_RUN_STATE   — path to run_state.json (default: /mnt/models/d5/run_state.json)
  ARCHIVER_MODELS_MOUNT — models root (default: from gdrive-archival/config.yaml or /mnt/models)
"""
from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
MA = REPO / "model-archival/config/registry.yaml"
DRIVES = REPO / "model-archival/config/drives.yaml"
LEG = REPO / "model-archival/config/registry-legacy.yaml"
SP = REPO / "model-archival/config/registry-specialists.yaml"
GD_CFG = REPO / "gdrive-archival/config.yaml"
GD_UPLOAD_STATE = REPO / "gdrive-archival/logs/registry-upload-state.json"
OUT = REPO / "docs/ARCHIVED-MODELS.md"


def bullets(ids: list[str]) -> str:
    return "\n".join(f"- `{x}`" for x in ids)


def content_subdir(tier: str) -> str:
    if tier == "C":
        return "quantized"
    if tier == "D":
        return "uncensored"
    return "raw"


def model_relpath(entry: dict) -> str:
    hf_repo = entry["hf_repo"]
    org, name = hf_repo.split("/", 1)
    rev = entry.get("commit_sha") or "main"
    drive = entry["drive"]
    return f"{drive}/{content_subdir(entry['tier'])}/{org}/{name}/{rev}"


def load_models_mount() -> Path:
    env = os.environ.get("ARCHIVER_MODELS_MOUNT")
    if env:
        return Path(env).resolve()
    if GD_CFG.is_file():
        try:
            cfg = yaml.safe_load(GD_CFG.read_text()) or {}
            mp = cfg.get("models_mount")
            if mp:
                return Path(mp).resolve()
        except (OSError, yaml.YAMLError):
            pass
    return Path("/mnt/models")


def load_run_state_map(path: Path) -> dict[str, str] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    out: dict[str, str] = {}
    for mid, meta in (data.get("models") or {}).items():
        if isinstance(meta, dict):
            out[str(mid)] = str(meta.get("status", "pending"))
    return out


def load_gdrive_completed(path: Path) -> set[str] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    raw = data.get("completed_models")
    if not isinstance(raw, list):
        return set()
    return {str(x).strip().strip("/") for x in raw if x}


def md_row(cells: list[str]) -> str:
    def esc(x: str) -> str:
        return x.replace("|", "\\|").replace("\n", " ")

    return "| " + " | ".join(esc(c) for c in cells) + " |"


def build_status_section(
    entries: list[dict],
    mount: Path,
    run_state_path: Path,
    state_map: dict[str, str] | None,
    gdrive_done: set[str] | None,
) -> str:
    rows: list[str] = [
        "## Paths, download status, and Google Drive",
        "",
        "Expected layout matches `ModelEntry.model_dir` in the archiver: "
        "`<models_mount>/<drive>/<raw|quantized|uncensored>/<org>/<repo>/<rev>` "
        "where `rev` is `commit_sha` or `main` when still unpinned.",
        "",
        "| Item | Value |",
        "|------|-------|",
        f"| `models_mount` (this run) | `{mount}` |",
        f"| `run_state.json` | `{run_state_path}` {'loaded' if state_map is not None else '*(missing on this host — no Download column)*'} |",
        f"| GDrive tracker | `{GD_UPLOAD_STATE.relative_to(REPO)}` {'loaded' if gdrive_done is not None else '*(missing — no GDrive column)*'} |",
        "",
    ]

    if state_map is not None:
        counts: dict[str, int] = {}
        for e in entries:
            st = state_map.get(e["id"], "pending")
            counts[st] = counts.get(st, 0) + 1
        summary = ", ".join(f"{k}: **{v}**" for k, v in sorted(counts.items()))
        rows.append(f"**Download status summary** (from run state): {summary}")
        rows.append("")

    if gdrive_done is not None:
        rels = [model_relpath(e) for e in entries]
        up = sum(1 for r in rels if r in gdrive_done)
        rows.append(
            f"**GDrive registry upload tracker:** **{up}** / **{len(rels)}** master-registry "
            "paths appear in `completed_models` (exact relpath match under `models_mount`)."
        )
        rows.append("")

    header = ["Model `id`", "Tier", "Path on disk"]
    sep = ["---", "---", "---"]
    if state_map is not None:
        header.append("Download")
        sep.append("---")
    header.extend(["Dir", "`manifest.json`"])
    sep.extend(["---", "---"])
    if gdrive_done is not None:
        header.append("GDrive")
        sep.append("---")

    rows.append(md_row(header))
    rows.append("| " + " | ".join(sep) + " |")

    for e in sorted(entries, key=lambda x: x["id"]):
        mid = e["id"]
        rel = model_relpath(e)
        full = mount / rel
        dir_ok = "yes" if full.is_dir() else "no"
        mf = "yes" if (full / "manifest.json").is_file() else "no"

        cells = [
            f"`{mid}`",
            str(e.get("tier", "")),
            f"`{full}`",
        ]
        if state_map is not None:
            cells.append(state_map.get(mid, "pending"))
        cells.extend([dir_ok, mf])
        if gdrive_done is not None:
            cells.append("yes" if rel in gdrive_done else "no")

        rows.append(md_row(cells))

    rows.append("")
    col_help = [
        "**Path on disk** — canonical archiver destination under `models_mount`.",
    ]
    if state_map is not None:
        col_help.append(
            "**Download** — `run_state.json` → `models.<id>.status` "
            "(pending / in_progress / complete / failed / skipped)."
        )
    col_help.append("**Dir** / **`manifest.json`** — checked on the host that ran this generator.")
    if gdrive_done is not None:
        col_help.append(
            "**GDrive** — `registry-upload-state.json` → `completed_models` (same relpaths as `upload_registry.py`)."
        )
    rows.append("**Columns:** " + " ".join(col_help))
    rows.append("")
    return "\n".join(rows)


def main() -> None:
    root = yaml.safe_load(MA.read_text())
    entries = root["models"]
    n_entries = len(entries)
    ids_unique = sorted({e["id"] for e in entries})
    n_unique = len(ids_unique)

    mount = load_models_mount()
    run_state_path = Path(
        os.environ.get("ARCHIVER_RUN_STATE", "/mnt/models/d5/run_state.json")
    ).resolve()
    state_map = load_run_state_map(run_state_path)
    gdrive_done = load_gdrive_completed(GD_UPLOAD_STATE)

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
            "distinct `id` values — reconcile duplicates in `registry.yaml`.\n\n"
        )

    status_section = build_status_section(entries, mount, run_state_path, state_map, gdrive_done)

    body = f"""# Archived models — inventory

This document summarises what the **model-archival** monorepo is configured to preserve.
**Authoritative sources** are the YAML registries; this file can be regenerated from the repository root with:

`uv run --directory model-archival python3 ../scripts/generate-archived-models-doc.py`

Optional: point at your archive host’s state and mounts:

`ARCHIVER_RUN_STATE=/mnt/models/d5/run_state.json ARCHIVER_MODELS_MOUNT=/mnt/models uv run --directory model-archival python3 ../scripts/generate-archived-models-doc.py`

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

Live **per-model download status** is normally on the metadata drive: `run_state.json`. This doc embeds a snapshot when that file (and optionally the GDrive tracker) is visible to the generator.

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

{status_section}

---

## Master registry index (`id` only)

Sorted **unique** `id` values (**{n_unique}** models):

{bullets(ids_unique)}
"""
    OUT.write_text(body, encoding="utf-8")
    print(f"Wrote {OUT} ({n_unique} unique master ids)")


if __name__ == "__main__":
    main()
