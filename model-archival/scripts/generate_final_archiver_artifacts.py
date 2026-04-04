#!/usr/bin/env python3
"""Emit config/final_downloads.yaml, config/final_pending_registry.yaml, and
repo docs/MODEL-ARCHIVE-FINAL-STATUS.md.

final_downloads.yaml — active archiver queue:
  - All models from registry-specialists.yaml
  - Main + legacy models with tier D OR (tier C and priority <= 2)  [small hostable + uncensored]
  - Plus explicit near-term completes: medgemma-27b-it, Qwen3-4B-Instruct-2507,
    Qwen2.5-VL-72B-Instruct, NVIDIA Nemotron-3-Super-120B-A12B-FP8

final_pending_registry.yaml — same union scope as the status doc, but only models whose
archiver run_state is not **complete** or **skipped** (includes **not_in_run_state** when
the id has no entry in run_state.json). Regenerate together with the status doc.

MODEL-ARCHIVE-FINAL-STATUS.md — union of registry.yaml, registry-specialists.yaml,
registry-legacy.yaml, registry_high_risk.yaml, and final_downloads.yaml with
run_state status and optional on-disk hints.

Usage (from model-archival/):

  ssh USER@HOST cat /mnt/models/d3/run_state.json | \\
    uv run python scripts/generate_final_archiver_artifacts.py --run-state -

Or:

  uv run python scripts/generate_final_archiver_artifacts.py \\
    --run-state /mnt/models/d3/run_state.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MA_ROOT = Path(__file__).resolve().parents[1]
CONFIG = MA_ROOT / "config"
OUT_FINAL = CONFIG / "final_downloads.yaml"
OUT_PENDING = CONFIG / "final_pending_registry.yaml"
OUT_STATUS = REPO_ROOT / "docs" / "MODEL-ARCHIVE-FINAL-STATUS.md"

REG_MAIN = CONFIG / "registry.yaml"
REG_SPEC = CONFIG / "registry-specialists.yaml"
REG_LEG = CONFIG / "registry-legacy.yaml"
REG_RISK = CONFIG / "registry_high_risk.yaml"

PRIORITY_FINISH: tuple[str, ...] = (
    "google/medgemma-27b-it",
    "Qwen/Qwen3-4B-Instruct-2507",
    "Qwen/Qwen2.5-VL-72B-Instruct",
    "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8",
)

# Match archiver tmp_audit.REGISTRY_FILES (later file wins for duplicate ids).
ARCHIVER_MERGE_ORDER = (
    "registry.yaml",
    "registry-specialists.yaml",
    "registry-legacy.yaml",
    "registry_high_risk.yaml",
)


def load_models(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(data.get("models") or [])


def archiver_merge_entries() -> dict[str, dict[str, Any]]:
    """Same precedence as tmp_audit.REGISTRY_FILES (later file wins per id)."""
    merged: dict[str, dict[str, Any]] = {}
    for name in ARCHIVER_MERGE_ORDER:
        p = CONFIG / name
        for e in load_models(p):
            merged[str(e["id"])] = dict(e)
    return merged


def merge_union_for_docs(
    extra_final: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """First-seen wins fields; accumulate registry_sources (like generate-archive-inventory)."""
    sources: list[tuple[str, list[dict[str, Any]]]] = [
        ("model-archival/config/registry.yaml", load_models(REG_MAIN)),
        ("model-archival/config/registry-specialists.yaml", load_models(REG_SPEC)),
        ("model-archival/config/registry-legacy.yaml", load_models(REG_LEG)),
        ("model-archival/config/registry_high_risk.yaml", load_models(REG_RISK)),
        ("model-archival/config/final_downloads.yaml", extra_final),
    ]
    by_id: dict[str, dict[str, Any]] = {}
    for reg_label, models in sources:
        for raw in models:
            e = dict(raw)
            mid = str(e["id"])
            if mid not in by_id:
                by_id[mid] = e
                by_id[mid]["registry_sources"] = [reg_label]
                continue
            existing = by_id[mid]
            rs = existing.setdefault("registry_sources", [])
            if reg_label not in rs:
                rs.append(reg_label)
            for k, v in e.items():
                if k in ("id", "registry_sources"):
                    continue
                cur = existing.get(k)
                empty = cur is None or cur == "" or cur == []
                if empty and v not in (None, "", []):
                    existing[k] = v
    return by_id


def content_subdir(tier: str) -> str:
    if tier == "C":
        return "quantized"
    if tier == "D":
        return "uncensored"
    return "raw"


def expected_rel_path(entry: dict[str, Any]) -> str:
    hf_repo = str(entry["hf_repo"])
    org, name = hf_repo.split("/", 1)
    rev = entry.get("commit_sha") or "main"
    drive = entry.get("drive", "?")
    tier = str(entry.get("tier", "A"))
    return f"{drive}/{content_subdir(tier)}/{org}/{name}/{rev}"


def load_run_state(path: str | None, stdin_data: bytes | None) -> dict[str, Any]:
    if stdin_data is not None:
        return json.loads(stdin_data.decode("utf-8"))
    if path and path != "-":
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return {"models": {}}


def build_final_downloads_models() -> list[dict[str, Any]]:
    arch = archiver_merge_entries()
    main = load_models(REG_MAIN)
    leg = load_models(REG_LEG)
    spec = load_models(REG_SPEC)

    want_ids: set[str] = set()
    for e in spec:
        want_ids.add(str(e["id"]))
    for pool in (main, leg):
        for e in pool:
            t = e.get("tier")
            pr = e.get("priority")
            if t == "D":
                want_ids.add(str(e["id"]))
            elif t == "C" and pr is not None and int(pr) <= 2:
                want_ids.add(str(e["id"]))
    for mid in PRIORITY_FINISH:
        want_ids.add(mid)

    out: list[dict[str, Any]] = []
    for mid in sorted(want_ids):
        if mid not in arch:
            raise SystemExit(f"final_downloads: id not in merged archiver registries: {mid}")
        entry = dict(arch[mid])
        entry.pop("registry_sources", None)
        if mid in PRIORITY_FINISH:
            notes = str(entry.get("notes") or "")
            tag = "[final-queue near-term complete]"
            entry["notes"] = f"{tag} {notes}".strip()
        out.append(entry)
    return out


_PENDING_STATUS_ORDER: dict[str, int] = {
    "in_progress": 0,
    "pending": 1,
    "failed": 2,
    "not_in_run_state": 3,
}


def build_pending_registry_rows(
    union: dict[str, dict[str, Any]],
    rs_models: dict[str, Any],
    *,
    classify_missing: bool,
) -> list[dict[str, Any]]:
    """Rows for final_pending_registry: not complete and not skipped.

    If classify_missing is False (no --run-state provided), omit ids with no run_state
    entry so we do not mark the entire union as pending.
    """
    rows: list[dict[str, Any]] = []
    for mid in sorted(union.keys()):
        meta = rs_models.get(mid, {})
        raw_st = meta.get("status")
        if raw_st is None:
            if not classify_missing:
                continue
            st_label = "not_in_run_state"
        else:
            st_label = str(raw_st)
        if st_label in ("complete", "skipped"):
            continue
        e = union[mid]
        rel = expected_rel_path(e)
        rec: dict[str, Any] = {
            "id": mid,
            "hf_repo": str(e.get("hf_repo", mid)),
            "run_state_status": st_label,
            "tier": e.get("tier"),
            "drive": e.get("drive"),
            "priority": e.get("priority"),
            "expected_path": rel,
            "registry_sources": [
                x.split("/")[-1] for x in (e.get("registry_sources") or [])
            ],
        }
        tb = meta.get("total_bytes")
        if isinstance(tb, int) and tb > 0:
            rec["total_gib"] = round(tb / (1024**3), 2)
        rows.append(rec)

    def sort_key(r: dict[str, Any]) -> tuple[int, str]:
        st = str(r.get("run_state_status", ""))
        return (_PENDING_STATUS_ORDER.get(st, 99), str(r["id"]))

    rows.sort(key=sort_key)
    return rows


def disk_probe(mount: Path, rel: str) -> tuple[bool, str]:
    full = mount / rel
    mf = full / "manifest.json"
    if mf.is_file():
        return True, str(full)
    if full.is_dir():
        return True, str(full)
    return False, str(full)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--run-state",
        default=None,
        help="Path to run_state.json, or '-' for stdin",
    )
    ap.add_argument(
        "--models-mount",
        default="/mnt/models",
        help="Root for optional on-disk probe (skip if missing)",
    )
    args = ap.parse_args()

    stdin_data: bytes | None = None
    if args.run_state == "-":
        stdin_data = sys.stdin.buffer.read()
        rs_path_note = "stdin"
    elif args.run_state:
        rs_path_note = args.run_state
    else:
        rs_path_note = "(none — statuses omitted)"

    rs_doc = load_run_state(
        None if stdin_data else args.run_state,
        stdin_data,
    )
    rs_models: dict[str, Any] = rs_doc.get("models") or {}
    run_state_explicit = stdin_data is not None or args.run_state is not None

    final_list = build_final_downloads_models()
    OUT_FINAL.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# Final archiver download queue (2026-04)\n"
        "# Criteria: all specialist registry models + tier D + tier C priority<=2 "
        "(small hostable quants) from main/legacy, plus near-term partial completes.\n"
        "#\n"
        "# Run:\n"
        "#   cd model-archival && uv run archiver --registry config/final_downloads.yaml download --all\n"
        "#\n"
        "# Regenerate this file + final_pending_registry.yaml + docs/MODEL-ARCHIVE-FINAL-STATUS.md:\n"
        "#   uv run python scripts/generate_final_archiver_artifacts.py --run-state /path/to/run_state.json\n"
    )
    OUT_FINAL.write_text(
        header + "\n" + yaml.safe_dump({"models": final_list}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    union = merge_union_for_docs(final_list)
    pending_rows = build_pending_registry_rows(
        union, rs_models, classify_missing=run_state_explicit
    )
    pcounts = Counter(str(r["run_state_status"]) for r in pending_rows)
    pend_by_status = ", ".join(f"`{k}`={v}" for k, v in sorted(pcounts.items()))

    mount = Path(args.models_mount)
    mount_ok = mount.is_dir()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        "# MODEL-ARCHIVE-FINAL-STATUS",
        "",
        f"_Generated: {now}_",
        "",
        "## Scope",
        "",
        "Merged registry IDs from `model-archival/config/registry.yaml`, ",
        "`registry-specialists.yaml`, `registry-legacy.yaml`, `registry_high_risk.yaml`, ",
        "and `final_downloads.yaml` (active queue). ",
        "Download **status** and **bytes** come from `run_state.json` when provided.",
        "",
        "### D3 scratch reclaim",
        "",
        "`uv run archiver audit-tmp --delete-reclaimable --apply` only removes ",
        "`reclaimable_tmp` (verified complete elsewhere + large leftover scratch). ",
        "If the audit reports **zero** such paths, D3 `.tmp` is mostly `active_partial`, ",
        "`wrong_drive_tmp`, or `metadata_only` — reclaim those only after manual review.",
        "",
        "### Falcon-180B partial",
        "",
        "Partial `tiiuae/falcon-180B` scratch should live under **`d1/.tmp`** (registry drive d1). ",
        "If still on D5, move: `mv /mnt/models/d5/.tmp/tiiuae_falcon-180B /mnt/models/d1/.tmp/` ",
        "(cross-device move can take many minutes).",
        "",
        f"**run_state source:** `{rs_path_note}`",
        "",
        "## Canonical final list",
        "",
        "Use these together; they describe the same archival program at different granularity.",
        "",
        "| Artifact | Purpose |",
        "|----------|---------|",
        "| This document (`MODEL-ARCHIVE-FINAL-STATUS.md`) | Human-readable **union** of all configured model IDs plus live `run_state` and expected paths. |",
        "| `model-archival/config/final_downloads.yaml` | **Active download queue** (specialists + tier D + small tier C from main/legacy + near-term completes). |",
        "| `model-archival/config/final_pending_registry.yaml` | **Machine-readable pending set**: union IDs that are not `complete` or `skipped` in `run_state` (includes `not_in_run_state` when absent from `run_state.json`). |",
        "",
        "## Pending registry (summary)",
        "",
        "Authoritative file: `model-archival/config/final_pending_registry.yaml` (regenerated with this doc).",
        "",
        f"- **Pending row count:** {len(pending_rows)} (union IDs whose `run_state` is not `complete` or `skipped`).",
        f"- **By status (see YAML `metadata.counts_by_status`):** {pend_by_status or '—'}",
        "",
        "## Summary",
        "",
        f"- **Distinct model IDs (union):** {len(union)}",
        f"- **final_downloads.yaml rows:** {len(final_list)}",
        "",
    ]

    if rs_models:
        c = Counter(str(m.get("status", "pending")) for m in rs_models.values())
        lines.append("**run_state status counts:** " + ", ".join(f"{k}={v}" for k, v in sorted(c.items())))
        lines.append("")

    lines += [
        "## Model table",
        "",
        "| id | tier | drive | pri | run_state | total_GiB | on_disk | expected_path | registries |",
        "|---|:-:|:-:|:-:|---|---:|:---:|---|---|",
    ]

    for mid in sorted(union.keys()):
        e = union[mid]
        meta = rs_models.get(mid, {})
        st = meta.get("status", "—")
        tb = meta.get("total_bytes")
        gi = f"{tb / (1024**3):.1f}" if isinstance(tb, int) and tb > 0 else "—"
        rel = expected_rel_path(e)
        if mount_ok:
            ok, pabs = disk_probe(mount, rel)
            disk = "yes" if ok else "no"
            path_cell = f"`{rel}`"
        else:
            disk = "n/a"
            path_cell = f"`{rel}`"
        regsrc = ", ".join(f"`{x.split('/')[-1]}`" for x in e.get("registry_sources", []))
        lines.append(
            f"| `{mid}` | {e.get('tier', '—')} | {e.get('drive', '—')} | {e.get('priority', '—')} | "
            f"{st} | {gi} | {disk} | {path_cell} | {regsrc} |"
        )

    lines.append("")

    pending_doc = {
        "generated": now,
        "run_state_source": rs_path_note,
        "run_state_provided": run_state_explicit,
        "description": (
            "Union-scope models whose archiver status is not complete or skipped. "
            "not_in_run_state means no entry for this id in run_state.json."
        ),
        "counts_by_status": dict(sorted(pcounts.items())),
        "pending_model_count": len(pending_rows),
    }
    pending_header = (
        "# Final pending registry — union IDs not complete/skipped in run_state.\n"
        "# Regenerate with final_downloads.yaml + MODEL-ARCHIVE-FINAL-STATUS.md:\n"
        "#   cd model-archival && uv run python scripts/generate_final_archiver_artifacts.py \\\n"
        "#     --run-state /mnt/models/d3/run_state.json\n"
        "#\n"
        "# Without --run-state this file is written with an empty models list — always pass run_state\n"
        "# when refreshing from the archiver host.\n"
        "#\n"
    )
    OUT_PENDING.parent.mkdir(parents=True, exist_ok=True)
    OUT_PENDING.write_text(
        pending_header
        + yaml.safe_dump(
            {"metadata": pending_doc, "models": pending_rows},
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    OUT_STATUS.parent.mkdir(parents=True, exist_ok=True)
    OUT_STATUS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_FINAL.relative_to(REPO_ROOT)} ({len(final_list)} models)")
    print(f"Wrote {OUT_PENDING.relative_to(REPO_ROOT)} ({len(pending_rows)} pending rows)")
    print(f"Wrote {OUT_STATUS.relative_to(REPO_ROOT)} ({len(union)} rows)")


if __name__ == "__main__":
    main()
