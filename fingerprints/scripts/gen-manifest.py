#!/usr/bin/env python3
"""Generate MANIFEST.md for model fingerprints.

Usage (from fingerprints/):
    uv run python3 scripts/gen-manifest.py

Output: /mnt/models/d1/model-checksums/MANIFEST.md
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REG_PATH = ROOT / "config" / "registry.yaml"
STATE_PATH = Path("/mnt/models/d1/model-checksums/run_state.json")
OUT_MD = Path("/mnt/models/d1/model-checksums/MANIFEST.md")


def status_icon(status: str) -> str:
    return {
        "complete": "✅",
        "pending": "⏳",
        "in_progress": "🔄",
        "failed": "❌",
        "skipped": "⏭️",
    }.get(status, "❓")


def main() -> None:
    if not REG_PATH.exists():
        raise SystemExit(f"Registry not found: {REG_PATH}")
    if not STATE_PATH.exists():
        raise SystemExit(f"run_state.json not found: {STATE_PATH}")

    reg = yaml.safe_load(REG_PATH.read_text(encoding="utf-8")) or {}
    state = json.loads(STATE_PATH.read_text(encoding="utf-8")) or {}

    models_reg = reg.get("models", [])
    models_state: dict[str, dict] = state if isinstance(state, dict) else {}

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    rows = []
    for m in models_reg:
        repo = m["hf_repo"]
        fam = m.get("family", "?")
        tier = m.get("tier", "?")
        importance = m.get("importance", "?")

        st = models_state.get(repo, {})
        status = st.get("status", "pending")
        tag = st.get("release_tag") or st.get("tag") or "—"
        files = st.get("file_count") or st.get("files") or 0

        rows.append((fam, tier, repo, status, importance, tag, int(files)))

    rows.sort(key=lambda r: (r[1], r[0], r[2]))  # tier, family, repo

    stats = Counter(r[3] for r in rows)

    lines = [
        "# Model Fingerprints Manifest",
        "",
        f"> Generated: {now}",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|--------|-------|",
    ]
    for status, count in sorted(stats.items()):
        lines.append(f"| {status_icon(status)} {status} | {count} |")
    lines.append(f"| **Total** | **{len(rows)}** |")

    lines += [
        "",
        "## Models",
        "",
        "| Tier | Family | Repo | Status | Tag | Files | Importance |",
        "|------|--------|------|--------|-----|-------|------------|",
    ]
    for fam, tier, repo, status, importance, tag, files in rows:
        icon = status_icon(status)
        lines.append(
            f"| {tier} | {fam} | `{repo}` | {icon} {status} | {tag} | {files} | {importance} |"
        )

    content = "\n".join(lines) + "\n"
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_MD.with_suffix(".md.tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(OUT_MD)
    print(f"Wrote {OUT_MD} for {len(rows)} models")


if __name__ == "__main__":
    main()

