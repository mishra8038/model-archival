#!/usr/bin/env python3
"""
Match ``vllm-hosting/config/vllm-archive-manifest.yaml`` HF repos against the archiver:

1. **Merged registry** (``registry.yaml`` + ``registry-specialists.yaml`` + … — same order as ``tmp_audit``).
2. **run_state.json** on the infra drive (D3 by default from ``drives.yaml``).
3. **On-disk verified tree**: revision directory passes ``_check_manifest_complete`` (``manifest.json`` + files + ``.sha256`` sidecars), via ``find_verified_manifest_dirs`` when the model is in the registry, or a drive scan when it is not.

Run on the **archive VM** (or any host with drives mounted):

  cd model-archival
  uv run python scripts/vllm_manifest_vs_archiver.py
  uv run python scripts/vllm_manifest_vs_archiver.py --out-md ../vllm-hosting/reports/VLLM-VS-ARCHIVER.md

Optional: ``--run-state /path/to/run_state.json`` if infra moved.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

import yaml

# package imports when run as ``uv run python scripts/...`` from model-archival/
from archiver.downloader import _check_manifest_complete
from archiver.models import DriveConfig, ModelEntry, load_registry
from archiver.state import STATUS_COMPLETE, RunState
from archiver.tmp_audit import find_verified_manifest_dirs, merge_registry_models


CONTENT_SUBDIRS = ("raw", "quantized", "uncensored")


def _repo_root_from_script() -> Path:
    # .../model-archival/model-archival/scripts/this.py -> outer monorepo root
    return Path(__file__).resolve().parents[2]


def _model_archival_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def scan_disk_unregistered(hf_repo: str, drives: dict[str, DriveConfig]) -> list[str]:
    """Find verified revision dirs for *hf_repo* without a registry entry."""
    if "/" not in hf_repo:
        return []
    org, repo = hf_repo.split("/", 1)
    hits: list[str] = []
    for label, d in drives.items():
        mp = d.mount_point
        if not mp.is_dir():
            continue
        for sub in CONTENT_SUBDIRS:
            base = mp / sub / org / repo
            if not base.is_dir():
                continue
            try:
                for rev in sorted(base.iterdir()):
                    if rev.is_dir() and _check_manifest_complete(rev):
                        hits.append(f"{label}:{sub}:{rev}")
            except OSError:
                continue
    return hits


def lookup_registry_by_hf_repo(merged: dict[str, ModelEntry], hf_repo: str) -> Optional[ModelEntry]:
    for m in merged.values():
        if m.hf_repo == hf_repo:
            return m
    # Some registry rows use id != hf_repo (rare)
    return merged.get(hf_repo)


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare vLLM manifest to archiver registry + disk.")
    ap.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="vllm-archive-manifest.yaml (default: <repo-root>/vllm-hosting/config/...)",
    )
    ap.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Archiver config dir (default: <model-archival>/config)",
    )
    ap.add_argument(
        "--drives",
        type=Path,
        default=None,
        help="drives.yaml (default: <config-dir>/drives.yaml)",
    )
    ap.add_argument("--run-state", type=Path, default=None, help="run_state.json override")
    ap.add_argument("--out-md", type=Path, default=None, help="Write Markdown report to this path")
    ap.add_argument("--json", action="store_true", help="Print JSON rows to stdout")
    args = ap.parse_args()

    repo_root = _repo_root_from_script()
    ma_root = _model_archival_root_from_script()
    manifest_path = args.manifest or (repo_root / "vllm-hosting" / "config" / "vllm-archive-manifest.yaml")
    config_dir = args.config_dir or (ma_root / "config")
    drives_path = args.drives or (config_dir / "drives.yaml")

    if not manifest_path.is_file():
        print(f"Missing manifest: {manifest_path}", file=sys.stderr)
        return 2
    if not drives_path.is_file():
        print(f"Missing drives.yaml: {drives_path}", file=sys.stderr)
        return 2

    doc = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    entries: list[dict[str, Any]] = doc.get("entries") or []

    # Minimal drives load for merge_registry_models (needs paths on every label referenced)
    reg0 = load_registry(config_dir / "registry.yaml", drives_path)
    drives = reg0.drives
    merged = merge_registry_models(config_dir, drives_path)

    state_path = args.run_state
    if state_path is None:
        d3 = drives.get("d3")
        state_path = (d3.mount_point / "run_state.json") if d3 else Path("/mnt/models/d3/run_state.json")
    run_state: Optional[RunState] = None
    if state_path.is_file():
        run_state = RunState(state_path)

    rows: list[dict[str, Any]] = []
    for e in entries:
        hf_repo = e["hf_repo"]
        cat = e.get("target_category", "")
        gib = e.get("approx_disk_gib")
        m = lookup_registry_by_hf_repo(merged, hf_repo)
        reg_id = m.id if m else None
        state_s = "—"
        if run_state and reg_id:
            state_s = run_state.get_model_status(reg_id)
        elif run_state:
            state_s = run_state.get_model_status(hf_repo)

        disk_hits: list[str] = []
        if m:
            disk_hits = find_verified_manifest_dirs(m, drives)
        if not disk_hits:
            disk_hits = scan_disk_unregistered(hf_repo, drives)

        verified = bool(disk_hits)
        summary = "verified_on_disk" if verified else ("in_registry_only" if m else "not_in_registry")
        if m and state_s == STATUS_COMPLETE and not verified:
            summary = "state_complete_disk_uncertain"
        if m and state_s not in (STATUS_COMPLETE, "—") and not verified:
            summary = f"state_{state_s}"

        rows.append(
            {
                "hf_repo": hf_repo,
                "target_category": cat,
                "approx_disk_gib": gib,
                "registry_id": reg_id,
                "run_state": state_s,
                "verified_paths": disk_hits,
                "match_summary": summary,
            }
        )

    if args.json:
        print(json.dumps(rows, indent=2))
    elif not args.out_md:
        n_ver = sum(1 for r in rows if r["verified_paths"])
        n_reg = sum(1 for r in rows if r["registry_id"])
        print(f"# vLLM manifest vs archiver ({len(rows)} repos)")
        print(f"- Manifest: {manifest_path}")
        print(f"- run_state: {state_path} ({'present' if state_path.is_file() else 'missing'})")
        print(f"- Verified on disk (manifest+sidecars): **{n_ver}** / {len(rows)}")
        print(f"- Found in merged registry: **{n_reg}** / {len(rows)}")
        print()
        for r in rows:
            mark = "OK" if r["verified_paths"] else "—"
            paths = "; ".join(r["verified_paths"]) if r["verified_paths"] else "—"
            if len(paths) > 140:
                paths = paths[:137] + "…"
            reg = r["registry_id"] or "—"
            print(f"{mark}\t{r['hf_repo']}\t{r['target_category']}\t{r['run_state']}\t{reg}\t{paths}")
    else:
        # --out-md only: brief summary on stderr
        n_ver = sum(1 for r in rows if r["verified_paths"])
        print(
            f"vLLM vs archiver: {n_ver}/{len(rows)} verified on disk; "
            f"run_state={state_path} ({'ok' if state_path.is_file() else 'missing'})",
            file=sys.stderr,
        )

    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        n_ver = sum(1 for r in rows if r["verified_paths"])
        lines = [
            "# vLLM archive manifest vs archiver",
            "",
            f"- **Manifest:** `{manifest_path}`",
            f"- **run_state.json:** `{state_path}` ({'present' if state_path.is_file() else '**missing**'})",
            f"- **Merged registry:** `{config_dir}` (`registry.yaml` + `registry-specialists.yaml` + …)",
            f"- **Verified on disk** (complete `manifest.json` + `.sha256` sidecars): **{n_ver}** / {len(rows)}",
            "",
            "| Status | HF repo | Category | run_state | Registry id | Verified path(s) |",
            "|--------|---------|----------|-----------|-------------|------------------|",
        ]
        for r in rows:
            st = "yes" if r["verified_paths"] else "no"
            paths = "<br>".join(f"`{p}`" for p in r["verified_paths"]) if r["verified_paths"] else "—"
            reg = f"`{r['registry_id']}`" if r["registry_id"] else "—"
            lines.append(
                f"| {st} | `{r['hf_repo']}` | {r.get('target_category') or '—'} | `{r['run_state']}` | {reg} | {paths} |"
            )
        args.out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Wrote {args.out_md}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
