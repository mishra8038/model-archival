#!/usr/bin/env python3
"""Emit machine-readable archive inventories under docs/archive-inventory/ (repo root).

Produces JSON (+ compact Markdown) for GitHub archival:
  - Per-drive model maps from registries + optional live mount scan
  - Manifest summaries and optional per-file SHA-256 from manifest.json
  - code-archival project list, gdrive roots, monorepo scope summary

Run from repository root:

  uv run --directory model-archival python3 ../scripts/generate-archive-inventory.py

With archive host paths (optional):

  ARCHIVER_MODELS_MOUNT=/mnt/models \\
  ARCHIVER_RUN_STATE=/mnt/models/d3/run_state.json \\
  uv run --directory model-archival python3 ../scripts/generate-archive-inventory.py \\
    --include-file-checksums
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "docs/archive-inventory"
MA = REPO / "model-archival/config/registry.yaml"
DRIVES_YAML = REPO / "model-archival/config/drives.yaml"
LEG = REPO / "model-archival/config/registry-legacy.yaml"
SP = REPO / "model-archival/config/registry-specialists.yaml"
CODE_REG = REPO / "code-archival/registry.yaml"
GD_REG = REPO / "gdrive-archival/gdrive-registry.yaml"
FP_REG = REPO / "fingerprints/config/registry.yaml"


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
    gd_cfg = REPO / "gdrive-archival/config.yaml"
    if gd_cfg.is_file():
        try:
            cfg = yaml.safe_load(gd_cfg.read_text(encoding="utf-8")) or {}
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


def load_drives_cfg(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(k): dict(v) for k, v in data.items() if isinstance(v, dict)}


def load_registry_models(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    root = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(root.get("models") or [])


def fp_registry_model_count() -> Optional[int]:
    if not FP_REG.is_file():
        return None
    text = FP_REG.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^#\s*Models:\s*(\d+)", text, re.MULTILINE)
    return int(m.group(1)) if m else None


def load_manifest(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def manifest_digest(manifest: dict) -> str:
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def merge_registry_entries(
    sources: list[tuple[Path, list[dict]]],
) -> dict[str, dict[str, Any]]:
    """id -> merged entry with registry_sources list (master first; later files fill gaps only)."""
    by_id: dict[str, dict[str, Any]] = {}
    for reg_path, models in sources:
        src = str(reg_path.relative_to(REPO))
        for raw in models:
            e = dict(raw)
            mid = str(e["id"])
            if mid not in by_id:
                by_id[mid] = dict(e)
                by_id[mid]["registry_sources"] = [src]
                continue
            existing = by_id[mid]
            rs = existing.setdefault("registry_sources", [])
            if src not in rs:
                rs.append(src)
            for k, v in e.items():
                if k in ("id", "registry_sources"):
                    continue
                cur = existing.get(k)
                empty = cur is None or cur == "" or cur == []
                if empty and v not in (None, "", []):
                    existing[k] = v
    return by_id


def scan_drive_trees(
    mount: Path,
    drive_labels: list[str],
) -> list[dict[str, Any]]:
    """Find revision dirs containing manifest.json not necessarily in registry."""
    found: list[dict[str, Any]] = []
    subdirs = ("raw", "quantized", "uncensored")
    for d in drive_labels:
        base = mount / d
        if not base.is_dir():
            continue
        for sub in subdirs:
            root = base / sub
            if not root.is_dir():
                continue
            for org in sorted(root.iterdir()):
                if not org.is_dir() or org.name.startswith("."):
                    continue
                for repo in sorted(org.iterdir()):
                    if not repo.is_dir() or repo.name.startswith("."):
                        continue
                    for rev in sorted(repo.iterdir()):
                        if not rev.is_dir() or rev.name.startswith("."):
                            continue
                        mf = rev / "manifest.json"
                        if mf.is_file():
                            rel = mf.parent.relative_to(mount)
                            found.append(
                                {
                                    "path_relative": str(rel).replace("\\", "/"),
                                    "hf_repo_guess": f"{org.name}/{repo.name}",
                                    "revision": rev.name,
                                    "content_subdir": sub,
                                    "drive": d,
                                }
                            )
    return found


def summarize_global_index(
    index_path: Path,
    max_lines: int,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "path": str(index_path),
        "exists": index_path.is_file(),
        "line_count": 0,
        "tail_records": [],
    }
    if not index_path.is_file() or max_lines <= 0:
        return out
    lines = index_path.read_text(encoding="utf-8", errors="replace").splitlines()
    out["line_count"] = len(lines)
    tail = lines[-max_lines:] if len(lines) > max_lines else lines
    for line in tail:
        line = line.strip()
        if not line:
            continue
        try:
            out["tail_records"].append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def load_code_archival_projects(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    repos = data.get("repos") or []
    out: list[dict[str, Any]] = []
    for r in repos:
        if not isinstance(r, dict):
            continue
        out.append(
            {
                "id": r.get("id"),
                "github": r.get("github"),
                "category": r.get("category"),
                "risk": r.get("risk"),
                "licence": r.get("licence"),
                "notes": (r.get("notes") or "").strip() if r.get("notes") else None,
            }
        )
    return out


def build_model_record(
    entry: dict,
    mount: Path,
    state_map: dict[str, str] | None,
    include_file_checksums: bool,
) -> dict[str, Any]:
    mid = entry["id"]
    rel = model_relpath(entry)
    full = mount / rel
    manifest_path = full / "manifest.json"
    manifest = load_manifest(manifest_path)
    rec: dict[str, Any] = {
        "id": mid,
        "hf_repo": entry.get("hf_repo"),
        "tier": entry.get("tier"),
        "drive": entry.get("drive"),
        "priority": entry.get("priority"),
        "licence": entry.get("licence"),
        "requires_auth": entry.get("requires_auth"),
        "commit_sha_registry": entry.get("commit_sha"),
        "quant_levels": entry.get("quant_levels") or [],
        "parent_model": entry.get("parent_model"),
        "method": entry.get("method"),
        "notes": entry.get("notes"),
        "legacy": entry.get("legacy", False),
        "registry_sources": entry.get("registry_sources", []),
        "path_relative": rel,
        "path_absolute": str(full),
        "on_disk": {
            "revision_dir_exists": full.is_dir(),
            "manifest_present": manifest_path.is_file(),
        },
        "download_status": state_map.get(mid) if state_map is not None else None,
    }
    if manifest:
        files = manifest.get("files") or []
        rec["manifest"] = {
            "model_id": manifest.get("model_id"),
            "hf_repo": manifest.get("hf_repo"),
            "commit_sha": manifest.get("commit_sha"),
            "tier": manifest.get("tier"),
            "archived_at": manifest.get("archived_at"),
            "file_count": manifest.get("file_count", len(files)),
            "total_size_bytes": manifest.get("total_size_bytes"),
            "manifest_sha256": manifest_digest(manifest),
        }
        if include_file_checksums:
            rec["manifest"]["files"] = files
    else:
        rec["manifest"] = None
    return rec


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_models_by_drive_md(
    path: Path,
    by_drive: dict[str, list[dict[str, Any]]],
    drives_cfg: dict[str, dict[str, Any]],
) -> None:
    lines: list[str] = [
        "# Models by drive (registry layout)",
        "",
        "Generated by `scripts/generate-archive-inventory.py`. "
        "See [`README.md`](README.md) for regeneration and JSON companions.",
        "",
    ]
    for d in sorted(by_drive.keys()):
        role = ""
        if d in drives_cfg:
            role = str(drives_cfg[d].get("role", "") or "")
        lines.append(f"## Drive `{d}`")
        if role:
            lines.append(f"*{role}*")
        lines.append("")
        lines.append("| Model `id` | Tier | Path (relative to models mount) | Manifest | Status |")
        lines.append("|------------|------|-----------------------------------|----------|--------|")
        for rec in sorted(by_drive[d], key=lambda x: x["id"]):
            st = rec.get("download_status")
            st_cell = st if st is not None else "—"
            mf = "yes" if rec.get("manifest") else ("yes" if rec["on_disk"].get("manifest_present") else "no")
            pr = rec.get("path_relative", "")
            lines.append(
                f"| `{rec['id']}` | {rec.get('tier', '')} | `{pr}` | {mf} | {st_cell} |"
            )
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_code_projects_md(path: Path, projects: list[dict[str, Any]]) -> None:
    lines = [
        "# code-archival — registered projects",
        "",
        f"**Count:** {len(projects)} (from `code-archival/registry.yaml`).",
        "",
        "| id | category | risk | licence |",
        "|----|----------|------|---------|",
    ]
    for p in sorted(projects, key=lambda x: (x.get("id") or "")):
        pid = p.get("id") or ""
        lines.append(
            f"| `{pid}` | {p.get('category') or ''} | {p.get('risk') or ''} | {p.get('licence') or ''} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write docs/archive-inventory/* JSON and MD lists.")
    parser.add_argument(
        "--include-file-checksums",
        action="store_true",
        help="Embed per-file path/sha256/size from each manifest.json (large JSON).",
    )
    parser.add_argument(
        "--global-index-max-lines",
        type=int,
        default=200,
        help="Append last N JSONL records from global_index.jsonl (0=skip). Default 200.",
    )
    args = parser.parse_args()

    mount = load_models_mount()
    run_state_path = Path(
        os.environ.get("ARCHIVER_RUN_STATE", "/mnt/models/d3/run_state.json")
    ).resolve()
    state_map = load_run_state_map(run_state_path)

    drives_cfg = load_drives_cfg(DRIVES_YAML)
    drive_labels = sorted(drives_cfg.keys())

    merged = merge_registry_entries(
        [
            (MA, load_registry_models(MA)),
            (LEG, load_registry_models(LEG)),
            (SP, load_registry_models(SP)),
        ]
    )
    models_list = [build_model_record(e, mount, state_map, args.include_file_checksums) for e in merged.values()]

    by_drive: dict[str, list[dict[str, Any]]] = {d: [] for d in drive_labels}
    for rec in models_list:
        d = rec.get("drive")
        if d in by_drive:
            by_drive[d].append(rec)

    registry_paths = {m["path_relative"] for m in models_list}
    disk_hits = scan_drive_trees(mount, drive_labels)
    orphans = [h for h in disk_hits if h["path_relative"] not in registry_paths]

    global_index_path = Path(
        os.environ.get(
            "ARCHIVER_GLOBAL_INDEX",
            str(mount / "d3" / "archive" / "checksums" / "global_index.jsonl"),
        )
    ).resolve()

    now = datetime.now(timezone.utc).isoformat()
    header = {
        "generated_at_utc": now,
        "models_mount": str(mount),
        "run_state_json": str(run_state_path),
        "run_state_loaded": state_map is not None,
        "global_index": summarize_global_index(global_index_path, args.global_index_max_lines),
    }

    monorepo = {
        "model_archival": {
            "master_registry": str(MA.relative_to(REPO)),
            "merged_unique_model_ids": len(merged),
        },
        "fingerprints": {
            "registry": str(FP_REG.relative_to(REPO)),
            "models_declared_in_header": fp_registry_model_count(),
        },
        "code_archival": {
            "registry": str(CODE_REG.relative_to(REPO)),
            "project_count": len(load_code_archival_projects(CODE_REG)),
        },
        "gdrive_archival": {
            "roots_registry": str(GD_REG.relative_to(REPO)),
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUT_DIR / "inventory-header.json", header)
    write_json(OUT_DIR / "models-merged.json", {"header": header, "models": sorted(models_list, key=lambda x: x["id"])})
    write_json(OUT_DIR / "models-by-drive.json", {"header": header, "drives": by_drive})
    write_json(
        OUT_DIR / "disk-manifest-hits.json",
        {
            "header": header,
            "hits": disk_hits,
            "orphan_manifest_paths": [o["path_relative"] for o in orphans],
        },
    )
    write_json(
        OUT_DIR / "archived-code-projects.json",
        {
            "header": header,
            "source": str(CODE_REG.relative_to(REPO)),
            "repos": load_code_archival_projects(CODE_REG),
        },
    )
    gd_raw: dict[str, Any] = {}
    if GD_REG.is_file():
        gd_raw = yaml.safe_load(GD_REG.read_text(encoding="utf-8")) or {}
    write_json(
        OUT_DIR / "gdrive-roots.json",
        {
            "header": header,
            "source": str(GD_REG.relative_to(REPO)),
            "roots": gd_raw.get("roots") or [],
            "d5_exclude": gd_raw.get("d5_exclude") or [],
        },
    )
    write_json(OUT_DIR / "monorepo-scope.json", {"header": header, **monorepo})

    write_models_by_drive_md(OUT_DIR / "models-by-drive.md", by_drive, drives_cfg)
    write_code_projects_md(
        OUT_DIR / "archived-code-projects.md",
        load_code_archival_projects(CODE_REG),
    )

    print(f"Wrote {OUT_DIR} — {len(models_list)} merged registry models, {len(disk_hits)} disk manifests, {len(orphans)} orphan paths")


if __name__ == "__main__":
    main()
