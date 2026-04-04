#!/usr/bin/env python3
"""
Suggest priority_overrides.json entries from on-disk progress vs run_state.json.

Lower effective priority = sooner (same rule as DriveScheduler). This script uses
strong negative values for "finish soon" and 99 to defer to the end of the queue.

Rules (defaults):
  - If run_state has total_bytes > 0 and on_disk/total >= --finish-ratio → --finish-priority
  - Else if total_bytes >= --large-bytes and 0 < ratio < --defer-below-ratio → --defer-priority
  - Scans all drives (d1–d5) under raw|quantized|uncensored for org/repo/* (max bytes).

Merge with existing JSON:  --merge /mnt/models/d3/priority_overrides.json --output path

Example (VM):
  uv run python scripts/compute-priority-overrides.py \\
    --registry config/registry-specialists.yaml \\
    --run-state /mnt/models/d3/run_state.json \\
    --mount /mnt/models \\
    --merge /mnt/models/d3/priority_overrides.json \\
    --output /mnt/models/d3/priority_overrides.json
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import yaml


def content_subdir(tier: str) -> str:
    if tier == "C":
        return "quantized"
    if tier == "D":
        return "uncensored"
    return "raw"


def dir_bytes(path: Path) -> int:
    if not path.is_dir():
        return 0
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            fp = Path(root) / name
            if name.endswith(".aria2"):
                continue
            try:
                total += fp.stat().st_size
            except OSError:
                pass
    return total


def max_bytes_for_repo(mount: Path, hf_repo: str, tier: str, drives: list[str]) -> int:
    org, name = hf_repo.split("/", 1)
    sub = content_subdir(tier)
    best = 0
    for drive in drives:
        base = mount / drive / sub / org / name
        if not base.is_dir():
            continue
        latest = base / "latest"
        if latest.is_symlink():
            try:
                best = max(best, dir_bytes(latest.resolve()))
            except OSError:
                pass
        for child in base.iterdir():
            if child.is_dir() and child.name != "latest":
                best = max(best, dir_bytes(child))
    return best


def main() -> None:
    ap = argparse.ArgumentParser(description="Compute priority override hints from disk vs run_state.")
    ap.add_argument("--registry", type=Path, required=True)
    ap.add_argument("--run-state", type=Path, required=True)
    ap.add_argument("--mount", type=Path, default=Path("/mnt/models"))
    ap.add_argument("--drives", default="d1,d2,d3,d5", help="Comma-separated drive labels to scan")
    ap.add_argument("--finish-ratio", type=float, default=0.48, help="At or above → finish soon")
    ap.add_argument("--finish-priority", type=int, default=-1000)
    ap.add_argument("--large-bytes", type=int, default=25 * 1024**3)
    ap.add_argument("--defer-below-ratio", type=float, default=0.42, help="Large model, progress below this → defer")
    ap.add_argument("--defer-priority", type=int, default=99)
    ap.add_argument(
        "--defer-id",
        action="append",
        default=[],
        metavar="MODEL_ID",
        help="Always assign defer priority (e.g. huge partial when run_state total_bytes is missing). Repeatable.",
    )
    ap.add_argument("--merge", type=Path, default=None, help="Existing JSON to merge into")
    ap.add_argument("--output", type=Path, default=None, help="Write merged JSON here")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    drives = [x.strip() for x in args.drives.split(",") if x.strip()]
    reg = yaml.safe_load(args.registry.read_text(encoding="utf-8"))
    rs = json.loads(args.run_state.read_text(encoding="utf-8"))
    models_map = rs.get("models") or {}

    suggested: dict[str, int] = {}
    for m in reg.get("models") or []:
        mid = m["id"]
        st = models_map.get(mid, {}).get("status", "pending")
        if st == "complete":
            continue
        planned = int(models_map.get(mid, {}).get("total_bytes") or 0)
        on_disk = max_bytes_for_repo(args.mount, m["hf_repo"], m.get("tier", "A"), drives)
        ratio = (on_disk / planned) if planned > 0 else 0.0

        if planned > 0 and ratio >= args.finish_ratio:
            suggested[mid] = args.finish_priority
        elif planned >= args.large_bytes and 0 < ratio < args.defer_below_ratio:
            suggested[mid] = args.defer_priority

    for mid in args.defer_id:
        suggested[mid] = args.defer_priority

    merged: dict[str, int] = {}
    if args.merge and args.merge.is_file():
        raw = json.loads(args.merge.read_text(encoding="utf-8"))
        merged = {k: int(v) for k, v in raw.items() if isinstance(k, str)}
    merged.update(suggested)

    print(json.dumps(suggested, indent=2))
    print("--- merged preview (first 20 keys touched by suggestion) ---", flush=True)
    for k in sorted(suggested.keys())[:20]:
        print(f"  {k}: {merged.get(k)}")

    if args.dry_run:
        return
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        tmp = args.output.with_suffix(args.output.suffix + ".tmp")
        tmp.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
        tmp.replace(args.output)
        print(f"Wrote {args.output} ({len(merged)} keys)", flush=True)


if __name__ == "__main__":
    main()
