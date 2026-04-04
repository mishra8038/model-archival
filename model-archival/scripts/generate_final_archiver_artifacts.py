#!/usr/bin/env python3
"""Emit config/final_downloads.yaml and repo docs/MODEL-ARCHIVE-FINAL-STATUS.md.

final_downloads.yaml — active archiver queue:
  - All models from registry-specialists.yaml
  - Main + legacy models with tier D OR (tier C and priority <= 2)  [small hostable + uncensored]
  - Plus explicit near-term completes: medgemma-27b-it, Qwen3-4B-Instruct-2507,
    Qwen2.5-VL-72B-Instruct, NVIDIA Nemotron-3-Super-120B-A12B-FP8

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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MA_ROOT = Path(__file__).resolve().parents[1]
CONFIG = MA_ROOT / "config"
OUT_FINAL = CONFIG / "final_downloads.yaml"
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
        "# Regenerate this file + docs/MODEL-ARCHIVE-FINAL-STATUS.md:\n"
        "#   uv run python scripts/generate_final_archiver_artifacts.py --run-state /path/to/run_state.json\n"
    )
    OUT_FINAL.write_text(
        header + "\n" + yaml.safe_dump({"models": final_list}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    union = merge_union_for_docs(final_list)
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
        "## Summary",
        "",
        f"- **Distinct model IDs (union):** {len(union)}",
        f"- **final_downloads.yaml rows:** {len(final_list)}",
        "",
    ]

    if rs_models:
        from collections import Counter

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
    OUT_STATUS.parent.mkdir(parents=True, exist_ok=True)
    OUT_STATUS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_FINAL.relative_to(REPO_ROOT)} ({len(final_list)} models)")
    print(f"Wrote {OUT_STATUS.relative_to(REPO_ROOT)} ({len(union)} rows)")


if __name__ == "__main__":
    main()
