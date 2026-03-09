#!/usr/bin/env python3
"""Generate manifest.json and MANIFEST.md for code-archives.

Usage (from code-archival/):
    python3 gen-manifest.py

Outputs under /mnt/models/d5/code-archives:
    - manifest.json
    - MANIFEST.md
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
REGISTRY_PATH = SCRIPT_DIR / "registry.yaml"
ARCHIVE_DIR = Path("/mnt/models/d5/code-archives")
MANIFEST_JSON = ARCHIVE_DIR / "manifest.json"
MANIFEST_MD = ARCHIVE_DIR / "MANIFEST.md"


def main() -> None:
    if not REGISTRY_PATH.exists():
        raise SystemExit(f"registry.yaml not found at {REGISTRY_PATH}")
    if not ARCHIVE_DIR.exists():
        raise SystemExit(f"archive dir not found at {ARCHIVE_DIR}")

    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    repos = data.get("repos", [])

    # Deduplicate
    seen = set()
    unique_repos = []
    for r in repos:
        gh = (r.get("github") or "").strip()
        if gh and gh not in seen:
            seen.add(gh)
            unique_repos.append(r)

    manifest_entries = []
    for r in unique_repos:
        gh = (r.get("github") or "").strip()
        cat = r.get("category", "unknown")
        risk = r.get("risk", "medium")
        lic = r.get("licence", "unknown")

        safe_name = gh.replace("/", "__")

        canonical = gh
        status = "failed"
        reason = "not attempted or unknown error"
        tag = ""
        size = ""
        stars = 0
        archived_at = ""

        # Look for matching metadata.json
        for mf in sorted(ARCHIVE_DIR.glob("*/metadata.json")):
            try:
                m = json.loads(mf.read_text(encoding="utf-8"))
            except Exception:
                continue
            if m.get("github_repo", "") == gh or mf.parent.name == safe_name:
                canonical = m.get("github_repo", gh)
                status = "downloaded"
                reason = ""
                tag = m.get("release_tag", "")
                stars = m.get("stars", 0)
                archived_at = m.get("archived_at", "")
                td = mf.parent / "release"
                if td.exists():
                    tars = sorted(td.glob("*.tar.gz"))
                    if tars:
                        sz = tars[0].stat().st_size
                        size = (
                            f"{sz/1024/1024:.1f} MB"
                            if sz < 1024 ** 3
                            else f"{sz/1024**3:.2f} GB"
                        )
                break

        manifest_entries.append(
            {
                "github_repo": gh,
                "canonical_repo": canonical,
                "category": cat,
                "risk": risk,
                "licence": lic,
                "status": status,
                "reason": reason,
                "release_tag": tag,
                "stars": stars,
                "size": size,
                "archived_at": archived_at,
            }
        )

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = {
        "total": len(manifest_entries),
        "downloaded": sum(1 for e in manifest_entries if e["status"] == "downloaded"),
        "failed": sum(1 for e in manifest_entries if e["status"] == "failed"),
        "skipped": sum(1 for e in manifest_entries if e["status"] == "skipped"),
    }

    manifest = {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "summary": summary,
        "repos": manifest_entries,
    }

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    # manifest.json (atomic)
    tmp_json = MANIFEST_JSON.with_suffix(".json.tmp")
    tmp_json.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    tmp_json.replace(MANIFEST_JSON)

    # MANIFEST.md (atomic)
    lines = [
        "# Code-Archival Manifest",
        "",
        f"> Generated: {generated_at}",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|--------|-------|",
        f"| ✅ downloaded | {summary['downloaded']} |",
        f"| ❌ failed     | {summary['failed']} |",
        f"| ⏭️ skipped    | {summary['skipped']} |",
        f"| **Total**     | **{summary['total']}** |",
        "",
        "## All Repos",
        "",
        "| # | Repo | Category | Risk | Status | Tag | Size | Stars | Reason / Notes |",
        "|---|------|----------|------|--------|-----|------|-------|----------------|",
    ]
    icons = {"downloaded": "✅", "failed": "❌", "skipped": "⏭️"}
    for i, e in enumerate(manifest_entries, 1):
        icon = icons.get(e["status"], "❓")
        repo = e["github_repo"]
        canon = e["canonical_repo"]
        url = f"https://github.com/{canon}"
        label = (
            f"[{repo}]({url})" if canon == repo else f"[{repo}]({url}) → {canon}"
        )
        reason = e["reason"] or ""
        lines.append(
            f"| {i} | {label} | {e['category']} | {e['risk']} "
            f"| {icon} {e['status']} | {e['release_tag'] or '—'} "
            f"| {e['size'] or '—'} | {e['stars']:,} | {reason} |"
        )

    tmp_md = MANIFEST_MD.with_suffix(".md.tmp")
    tmp_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp_md.replace(MANIFEST_MD)

    print(f"Wrote {MANIFEST_JSON} and {MANIFEST_MD}")


if __name__ == "__main__":
    main()

