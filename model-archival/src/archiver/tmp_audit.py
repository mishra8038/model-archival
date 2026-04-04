"""
Cross-drive audit of archiver scratch directories (``<mount>/.tmp/<model>``).

Compares partial trees to ``run_state.json`` and final ``raw|quantized|uncensored``
layouts (``manifest.json`` + ``.sha256`` sidecars). Writes JSON + Markdown under
D3 infra ``logs/`` for operational decisions — read-only unless ``--apply`` is used
with an explicit delete mode.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from archiver.downloader import _check_manifest_complete
from archiver.models import DriveConfig, ModelEntry, load_registry
from archiver.state import (
    STATUS_COMPLETE,
    STATUS_FAILED,
    STATUS_IN_PROGRESS,
    STATUS_PENDING,
)

REGISTRY_FILES = (
    "registry.yaml",
    "registry-specialists.yaml",
    "registry-legacy.yaml",
    "registry_high_risk.yaml",
)

METADATA_BYTES = 1_000_000  # below this → "metadata_only" scratch
PARTIAL_BYTES = 10_000_000  # above → likely real partial weights


def _infra_root(reg_drives: dict[str, DriveConfig]) -> Path:
    d3 = reg_drives.get("d3")
    return d3.mount_point if d3 else Path("/tmp/archiver")


def merge_registry_models(config_dir: Path, drives_path: Path) -> dict[str, ModelEntry]:
    """Later files override earlier for duplicate ``id``."""
    merged: dict[str, ModelEntry] = {}
    for name in REGISTRY_FILES:
        p = config_dir / name
        if not p.exists():
            continue
        reg = load_registry(p, drives_path)
        for m in reg.models:
            merged[m.id] = m
    return merged


def tmp_folder_to_model_id(folder_name: str, by_tmp_name: dict[str, str]) -> Optional[str]:
    if folder_name in by_tmp_name:
        return by_tmp_name[folder_name]
    if "_" not in folder_name:
        return None
    org, rest = folder_name.split("_", 1)
    candidate = f"{org}/{rest}"
    return candidate


def scan_tmp_tree(tmp_subdir: Path) -> dict[str, Any]:
    total = 0
    n_files = 0
    n_aria2 = 0
    largest: list[tuple[str, int]] = []
    for root, _, files in os.walk(tmp_subdir):
        for fn in files:
            p = Path(root) / fn
            try:
                sz = p.stat().st_size
            except OSError:
                continue
            total += sz
            n_files += 1
            rel = p.relative_to(tmp_subdir)
            if fn.endswith(".aria2"):
                n_aria2 += 1
            largest.append((str(rel), sz))
    largest.sort(key=lambda x: -x[1])
    return {
        "bytes": total,
        "n_files": n_files,
        "n_aria2": n_aria2,
        "largest_files": largest[:8],
    }


def find_verified_manifest_dirs(m: ModelEntry, drives: dict[str, DriveConfig]) -> list[str]:
    """Return ``label:path`` strings for revision dirs with a verified manifest."""
    org, repo = m.hf_repo.split("/", 1)
    sub = m.content_subdir
    out: list[str] = []
    for label, d in drives.items():
        base = d.mount_point / sub / org / repo
        if not base.is_dir():
            continue
        if m.commit_sha:
            md = base / m.commit_sha
            if md.is_dir() and _check_manifest_complete(md):
                out.append(f"{label}:{md}")
            continue
        try:
            for rev in sorted(base.iterdir()):
                if rev.is_dir() and _check_manifest_complete(rev):
                    out.append(f"{label}:{rev}")
        except OSError:
            continue
    return out


def classify(
    *,
    scan: dict[str, Any],
    rs_status: str,
    verified_paths: list[str],
    in_registry: bool,
    drive_match: Optional[bool],
) -> str:
    b = scan["bytes"]
    if verified_paths and b >= METADATA_BYTES:
        return "reclaimable_tmp"
    if verified_paths and b < METADATA_BYTES:
        return "complete_no_scratch"
    if rs_status == STATUS_COMPLETE and b >= METADATA_BYTES:
        return "run_state_complete_tmp_leftover"
    if not in_registry:
        return "unknown_tmp"
    if b < METADATA_BYTES:
        return "metadata_only"
    if drive_match is False:
        return "wrong_drive_tmp"
    if rs_status in (STATUS_IN_PROGRESS, STATUS_PENDING, STATUS_FAILED) or scan["n_aria2"]:
        return "active_partial"
    return "partial_or_stale"


@dataclass
class TmpAuditRecord:
    tmp_drive_label: str
    tmp_path: str
    tmp_folder: str
    model_id: Optional[str]
    in_registry: bool
    registry_drive: Optional[str]
    tmp_matches_registry_drive: Optional[bool]
    run_state_status: str
    run_state_updated: Optional[str]
    scratch_bytes: int
    scratch_n_files: int
    scratch_n_aria2: int
    largest_files: list[list[Any]] = field(default_factory=list)
    verified_manifest_paths: list[str] = field(default_factory=list)
    classification: str = ""
    notes: str = ""


def run_tmp_audit(
    *,
    config_dir: Path,
    registry_path: Path,
    drives_path: Path,
    infra: Optional[Path] = None,
) -> tuple[dict[str, Any], list[TmpAuditRecord]]:
    drives_path = drives_path.resolve()
    config_dir = config_dir.resolve()

    reg0 = load_registry(registry_path, drives_path)
    drives = reg0.drives
    merged = merge_registry_models(config_dir, drives_path)
    by_tmp = {m.id.replace("/", "_"): m.id for m in merged.values()}

    state_path = (infra or _infra_root(drives)) / "run_state.json"
    if state_path.exists():
        try:
            data = json.loads(state_path.read_text(encoding="utf-8")).get("models", {})
        except Exception:
            data = {}
    else:
        data = {}

    records: list[TmpAuditRecord] = []

    for label, d in sorted(drives.items()):
        scratch = d.mount_point / ".tmp"
        if not scratch.is_dir():
            continue
        try:
            children = sorted(scratch.iterdir())
        except OSError as e:
            records.append(
                TmpAuditRecord(
                    tmp_drive_label=label,
                    tmp_path=str(scratch),
                    tmp_folder="(unreadable)",
                    model_id=None,
                    in_registry=False,
                    registry_drive=None,
                    tmp_matches_registry_drive=None,
                    run_state_status="—",
                    run_state_updated=None,
                    scratch_bytes=0,
                    scratch_n_files=0,
                    scratch_n_aria2=0,
                    classification="error",
                    notes=str(e),
                )
            )
            continue

        for child in children:
            if not child.is_dir():
                continue
            folder = child.name
            mid = tmp_folder_to_model_id(folder, by_tmp)
            m = merged.get(mid) if mid else None
            if mid and m is None and folder in by_tmp:
                mid = by_tmp[folder]
                m = merged.get(mid)
            in_reg = m is not None
            reg_drive = m.drive if m else None
            match = (label == reg_drive) if reg_drive else None

            scan = scan_tmp_tree(child)
            if mid:
                rs = data.get(mid, {})
                rs_status = rs.get("status", STATUS_PENDING)
                rs_upd = rs.get("updated_at")
            else:
                rs_status = "—"
                rs_upd = None

            verified: list[str] = []
            if m:
                verified = find_verified_manifest_dirs(m, drives)

            klass = classify(
                scan=scan,
                rs_status=rs_status if rs_status != "—" else STATUS_PENDING,
                verified_paths=verified,
                in_registry=in_reg,
                drive_match=match,
            )

            notes_parts: list[str] = []
            if not in_reg and mid:
                notes_parts.append("folder name not in merged registry files")
            if match is False:
                notes_parts.append(f"tmp on {label} but registry drive={reg_drive}")

            records.append(
                TmpAuditRecord(
                    tmp_drive_label=label,
                    tmp_path=str(scratch),
                    tmp_folder=folder,
                    model_id=mid,
                    in_registry=in_reg,
                    registry_drive=reg_drive,
                    tmp_matches_registry_drive=match,
                    run_state_status=rs_status,
                    run_state_updated=rs_upd,
                    scratch_bytes=scan["bytes"],
                    scratch_n_files=scan["n_files"],
                    scratch_n_aria2=scan["n_aria2"],
                    largest_files=scan["largest_files"],
                    verified_manifest_paths=verified,
                    classification=klass,
                    notes="; ".join(notes_parts),
                )
            )

    now = datetime.now(timezone.utc).isoformat()
    summary: dict[str, int] = {}
    for r in records:
        summary[r.classification] = summary.get(r.classification, 0) + 1

    payload: dict[str, Any] = {
        "generated_at_utc": now,
        "config_dir": str(config_dir),
        "registry_files": [str(config_dir / n) for n in REGISTRY_FILES if (config_dir / n).exists()],
        "run_state_path": str(state_path),
        "summary_by_classification": summary,
        "records": [
            {
                "tmp_drive_label": r.tmp_drive_label,
                "tmp_path": r.tmp_path,
                "tmp_folder": r.tmp_folder,
                "model_id": r.model_id,
                "in_registry": r.in_registry,
                "registry_drive": r.registry_drive,
                "tmp_matches_registry_drive": r.tmp_matches_registry_drive,
                "run_state_status": r.run_state_status,
                "run_state_updated": r.run_state_updated,
                "scratch_bytes": r.scratch_bytes,
                "scratch_n_files": r.scratch_n_files,
                "scratch_n_aria2": r.scratch_n_aria2,
                "largest_files": r.largest_files,
                "verified_manifest_paths": r.verified_manifest_paths,
                "classification": r.classification,
                "notes": r.notes,
            }
            for r in records
        ],
    }
    return payload, records


def write_tmp_audit_artifacts(
    infra: Path,
    payload: dict[str, Any],
    records: list[TmpAuditRecord],
) -> tuple[Path, Path]:
    log_dir = infra / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    json_path = log_dir / "TMP-SCRATCH-AUDIT.json"
    md_path = log_dir / "TMP-SCRATCH-AUDIT.md"

    tmpj = json_path.with_suffix(".json.tmp")
    tmpj.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmpj, json_path)

    class_hints = {
        "reclaimable_tmp": "Verified install elsewhere; large `.tmp` leftover — delete after spot-check.",
        "complete_no_scratch": "Verified complete; tiny `.tmp` only.",
        "run_state_complete_tmp_leftover": "`run_state` complete but large scratch — verify manifest, then often reclaimable.",
        "active_partial": "Resume-capable partials (keep if finishing download).",
        "wrong_drive_tmp": "Scratch drive ≠ registry `drive:` — merge or align registry / `--storage-drive`.",
        "metadata_only": "HF metadata only; negligible size.",
        "unknown_tmp": "Not in merged registry — map manually.",
        "partial_or_stale": "Large scratch, unclear — inspect `largest_files` + `run_state`.",
        "error": "Could not read directory.",
    }

    lines = [
        "# Archiver scratch audit (`.tmp`)",
        "",
        f"_UTC: {payload['generated_at_utc']}_",
        "",
        "Source: merged registry files in `config/` + `run_state.json` + on-disk `manifest.json` "
        "(files + `.sha256` sidecars, same rule as the downloader).",
        "",
        "## Summary",
        "",
        "| Classification | Count | Hint |",
        "|----------------|------:|------|",
    ]
    for cname, count in sorted(
        payload["summary_by_classification"].items(), key=lambda x: (-x[1], x[0])
    ):
        hint = class_hints.get(cname, "—")
        lines.append(f"| `{cname}` | {count} | {hint} |")
    lines += [
        "",
        f"**JSON (machine-readable):** `{json_path}`",
        "",
        "## Per-folder status (all drives)",
        "",
        "| Drive | Folder | Model id | Reg `drive` | `run_state` | Bytes | Class | Verified manifest |",
        "|-------|--------|----------|-------------|-------------|------:|-------|-------------------|",
    ]

    def fmt_bytes(n: int) -> str:
        if n < 1024:
            return f"{n} B"
        v = float(n)
        for unit in ("KB", "MB", "GB", "TB"):
            v /= 1024.0
            if v < 1024.0 or unit == "TB":
                return f"{v:.1f} {unit}"
        return f"{v:.1f} TB"

    for r in sorted(records, key=lambda x: (-x.scratch_bytes, x.tmp_drive_label, x.tmp_folder)):
        vm = ", ".join(f"`{p}`" for p in r.verified_manifest_paths[:2])
        if len(r.verified_manifest_paths) > 2:
            vm += f" (+{len(r.verified_manifest_paths) - 2})"
        mid = f"`{r.model_id}`" if r.model_id else "—"
        rd = r.registry_drive or "—"
        lines.append(
            f"| {r.tmp_drive_label} | `{r.tmp_folder}` | {mid} | {rd} | "
            f"{r.run_state_status} | {fmt_bytes(r.scratch_bytes)} | `{r.classification}` | {vm or '—'} |"
        )

    lines += [
        "",
        "## Largest scratch trees",
        "",
        "| Bytes | Drive | Folder | Classification |",
        "|------:|-------|--------|----------------|",
    ]
    for r in sorted(records, key=lambda x: -x.scratch_bytes)[:40]:
        lines.append(
            f"| {fmt_bytes(r.scratch_bytes)} | {r.tmp_drive_label} | `{r.tmp_folder}` | `{r.classification}` |"
        )

    lines += [
        "",
        "## Commands",
        "",
        "- Regenerate: `uv run archiver audit-tmp` (from `model-archival/`).",
        "- Reclaim **only** paths classified `reclaimable_tmp` after manual spot-check:",
        "  `uv run archiver audit-tmp --delete-reclaimable --apply`",
        "",
    ]

    tmpm = md_path.with_suffix(".md.tmp")
    tmpm.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmpm, md_path)

    return json_path, md_path


def delete_reclaimable_tmp(
    records: list[TmpAuditRecord],
    *,
    apply: bool,
) -> list[str]:
    """Remove `.tmp` dirs classified as reclaimable_tmp. Caller must pass apply=True."""
    actions: list[str] = []
    for r in records:
        if r.classification != "reclaimable_tmp":
            continue
        path = Path(r.tmp_path) / r.tmp_folder
        if not path.is_dir():
            continue
        if apply:
            import shutil

            shutil.rmtree(path)
            actions.append(f"deleted {path}")
        else:
            actions.append(f"would delete {path}")
    return actions
