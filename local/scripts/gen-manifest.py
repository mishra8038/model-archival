#!/usr/bin/env python3
"""Generate MANIFEST.md from run_state.json and config/registry.yaml.

Usage (from local/):
    uv run python3 scripts/gen-manifest.py

Output: /mnt/models/d5/MANIFEST.md
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REG_PATH   = REPO_ROOT / "config" / "registry.yaml"
STATE_PATH = Path("/mnt/models/d5/run_state.json")
MANIFEST   = Path("/mnt/models/d5/MANIFEST.md")


def status_icon(s: str) -> str:
    return {
        "complete":    "✅",
        "in_progress": "🔄",
        "failed":      "❌",
        "skipped":     "⏭️",
        "pending":     "⏳",
    }.get(s, "❓")


def main() -> None:
    reg   = yaml.safe_load(REG_PATH.read_text())
    state = json.loads(STATE_PATH.read_text())
    now   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    rows = []
    for m in reg["models"]:
        ms        = state["models"].get(m["id"], {})
        status    = ms.get("status", "pending")
        completed = (ms.get("completed_at") or "")[:10]
        size_gb   = ms.get("total_bytes", 0) / 1024 ** 3
        size_str  = f"{size_gb:.1f} GB" if size_gb > 0.01 else ""
        rows.append((m.get("tier", "?"), m["id"], m.get("drive", "?"),
                     status, size_str, size_gb, completed))

    rows.sort(key=lambda r: (r[0], r[1]))

    stats: dict[str, int] = {}
    for r in rows:
        stats[r[3]] = stats.get(r[3], 0) + 1

    total_dl = sum(r[5] for r in rows)
    n_complete = stats.get("complete", 0)

    lines = [
        "# Model Archival Manifest",
        "",
        f"> Generated: {now}",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|--------|-------|",
    ]
    for k, v in sorted(stats.items()):
        lines.append(f"| {status_icon(k)} {k} | {v} |")
    lines.append(f"| **Total** | **{len(rows)}** |")
    lines += [
        "",
        f"**Downloaded so far:** {total_dl:.1f} GB across {n_complete} completed models",
        "",
        "## Models",
        "",
        "| Tier | Model | Drive | Status | Size | Completed |",
        "|------|-------|-------|--------|------|-----------|",
    ]
    for tier, model_id, drive, status, size_str, _, completed in rows:
        icon = status_icon(status)
        lines.append(f"| {tier} | `{model_id}` | {drive} | {icon} {status} | {size_str} | {completed} |")

    content = "\n".join(lines) + "\n"

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_suffix(".md.tmp")
    tmp.write_text(content)
    tmp.replace(MANIFEST)

    print(f"MANIFEST.md → {MANIFEST}")
    print(f"  {stats}")
    print(f"  {total_dl:.1f} GB downloaded")


if __name__ == "__main__":
    main()
