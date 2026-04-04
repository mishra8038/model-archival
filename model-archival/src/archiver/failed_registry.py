"""
Classify download failures from run_state.json and emit a structured registry (YAML + Markdown).

Also ingests historical failures from incremental ``run-report-*.md`` files (same format as
``RunReport.record_model_fail`` / ``record_verification`` / ``record_model_skip``).

Categories (ordered classification):
  disk_space   — ENOSPC / no space left on device
  unavailable  — repo or file not found (404, resolve errors)
  auth         — 401/403, gated repo, access denied, token issues
  failed_shards — exhausted aria2/hub retries (shards, CDN, timeouts)
  verify       — post-download checksum / manifest verification
  other        — does not match above
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from archiver.models import ModelEntry, load_registry
from archiver.state import STATUS_FAILED, STATUS_SKIPPED
from archiver.tmp_audit import merge_registry_models

# Canonical category keys (stable for tooling)
CAT_DISK_SPACE = "disk_space"
CAT_UNAVAILABLE = "unavailable"
CAT_AUTH = "auth"
CAT_FAILED_SHARDS = "failed_shards"
CAT_VERIFY = "verify"
CAT_OTHER = "other"
CAT_SKIPPED_GATED = "skipped_gated"  # only when --include-skipped

_CATEGORY_ORDER = (
    CAT_DISK_SPACE,
    CAT_UNAVAILABLE,
    CAT_AUTH,
    CAT_FAILED_SHARDS,
    CAT_VERIFY,
    CAT_OTHER,
    CAT_SKIPPED_GATED,
)

_MAX_HISTORICAL_INCIDENTS_PER_MODEL = 12


@dataclass(frozen=True)
class HistoricalIncident:
    model_id: str
    error_text: str
    kind: str  # download_fail | verify_fail | skip
    report_path: str
    report_mtime_utc: str


def discover_run_report_paths(*dirs: Path) -> list[Path]:
    """Return sorted ``run-report-*.md`` paths under dirs that exist."""
    seen: set[Path] = set()
    out: list[Path] = []
    for d in dirs:
        if not d or not d.is_dir():
            continue
        for p in sorted(d.glob("run-report*.md")):
            rp = p.resolve()
            if rp not in seen:
                seen.add(rp)
                out.append(rp)
    out.sort(key=lambda x: x.stat().st_mtime)
    return out


def parse_run_report_file(path: Path) -> list[HistoricalIncident]:
    """
    Parse one RunReport markdown file for download failures, verification failures, skips.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = text.splitlines()
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        mtime = ""

    out: list[HistoricalIncident] = []
    current_model: Optional[str] = None
    awaiting_error = False

    i = 0
    while i < len(lines):
        line = lines[i]

        mo = re.match(r"^### ▶ `([^`]+)`\s*$", line)
        if mo:
            current_model = mo.group(1)
            awaiting_error = False
            i += 1
            continue

        if current_model and re.match(r"^- \*\*Failed:\*\*", line):
            awaiting_error = True
            i += 1
            continue

        if current_model and awaiting_error:
            merr = re.match(r"^- \*\*Error:\*\* `(.+)`\s*$", line)
            if merr:
                out.append(
                    HistoricalIncident(
                        model_id=current_model,
                        error_text=merr.group(1).strip(),
                        kind="download_fail",
                        report_path=str(path.resolve()),
                        report_mtime_utc=mtime,
                    )
                )
                awaiting_error = False
            i += 1
            continue

        mv = re.match(r"^#### ✗ Verification — `([^`]+)`\s*$", line)
        if mv:
            vid = mv.group(1)
            result_line = ""
            for j in range(i + 1, min(i + 20, len(lines))):
                if lines[j].startswith("- **Result:**"):
                    result_line = lines[j]
                    break
            if result_line and "FAILED" in result_line.upper():
                out.append(
                    HistoricalIncident(
                        model_id=vid,
                        error_text=f"verification: {result_line.strip()}",
                        kind="verify_fail",
                        report_path=str(path.resolve()),
                        report_mtime_utc=mtime,
                    )
                )
            current_model = None
            awaiting_error = False
            i += 1
            continue

        ms = re.match(r"^### — `([^`]+)` \(skipped\)\s*$", line)
        if ms:
            sid = ms.group(1)
            reason = ""
            for j in range(i + 1, min(i + 6, len(lines))):
                mr = re.match(r"^- \*\*Skipped:\*\* .*Reason:\s*(.+)$", lines[j])
                if mr:
                    reason = mr.group(1).strip()
                    break
            out.append(
                HistoricalIncident(
                    model_id=sid,
                    error_text=reason or "skipped (reason not parsed)",
                    kind="skip",
                    report_path=str(path.resolve()),
                    report_mtime_utc=mtime,
                )
            )
            current_model = None
            awaiting_error = False
            i += 1
            continue

        if line.startswith("### "):
            current_model = None
            awaiting_error = False

        i += 1

    return out


def _report_timestamp_sort_key(report_path: str) -> str:
    """Derive an ISO-like sort key from ``run-report-YYYY-MM-DD_HH-MM-SS.md`` filename."""
    m = re.search(
        r"run-report-(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})\.md",
        report_path,
    )
    if m:
        return f"{m.group(1)}T{m.group(2)}:{m.group(3)}:{m.group(4)}"
    return ""


def _aggregate_historical(
    report_paths: list[Path],
) -> dict[str, list[HistoricalIncident]]:
    by_id: dict[str, list[HistoricalIncident]] = defaultdict(list)
    seen_key: set[tuple[str, str, str]] = set()
    for rp in report_paths:
        for inc in parse_run_report_file(rp):
            key = (inc.model_id, inc.error_text[:500], inc.report_path)
            if key in seen_key:
                continue
            seen_key.add(key)
            by_id[inc.model_id].append(inc)
    for mid in by_id:
        by_id[mid].sort(
            key=lambda x: (_report_timestamp_sort_key(x.report_path), x.report_mtime_utc),
            reverse=True,
        )
    return by_id


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def classify_failure_reason(message: str) -> tuple[str, str]:
    """
    Return (category, short_human_label) from error/last_error text.
    """
    raw = message or ""
    m = _norm(raw)

    if "no space left on device" in m or "enospc" in m or "errno 28" in m:
        return CAT_DISK_SPACE, "no space left on device"
    if "disk space / abandoned" in m or "download abandoned" in m:
        return CAT_DISK_SPACE, "disk space / abandoned"

    if "cannot resolve hf repo" in m or "repositorynotfound" in m.replace(" ", ""):
        return CAT_UNAVAILABLE, "repository not found / cannot resolve"
    if re.search(r"\b404\b", raw) and (
        "client error" in m or "not found" in m or "error" in m
    ):
        return CAT_UNAVAILABLE, "HTTP 404 / not found"
    if "entrynotfound" in m.replace(" ", "") or "not found on the hub" in m:
        return CAT_UNAVAILABLE, "file or revision not on hub"

    if "access denied" in m or "gated repo" in m:
        return CAT_AUTH, "gated / access denied"
    if re.search(r"\b403\b", raw) and "client error" in m:
        return CAT_AUTH, "HTTP 403"
    if re.search(r"\b401\b", raw) and "client error" in m:
        return CAT_AUTH, "HTTP 401"
    if "no hf token" in m or "token cannot access" in m:
        return CAT_AUTH, "HF token missing or insufficient"

    if (
        "checksum verification failed" in m
        or "sha-256 mismatch" in m
        or "sha256 mismatch" in m
        or "verification failed" in m
    ):
        return CAT_VERIFY, "checksum / verification"

    if "after 5 attempts" in m or "after 10 attempts" in m:
        return CAT_FAILED_SHARDS, "download retries exhausted"
    if "aria2c error" in m or "download aborted" in m:
        return CAT_FAILED_SHARDS, "aria2 / transport abort"
    if "tls connection" in m or "ssl/tls handshake" in m:
        return CAT_FAILED_SHARDS, "TLS / transport (handshake)"
    if m.startswith("failed to download ") and "attempts" in m:
        return CAT_FAILED_SHARDS, "shard download failed (retries)"

    return CAT_OTHER, "unclassified"


def _error_text(entry: dict[str, Any]) -> str:
    return (entry.get("last_error") or entry.get("error") or "").strip()


def _incident_to_dict(inc: HistoricalIncident) -> dict[str, Any]:
    return {
        "report_file": inc.report_path,
        "report_mtime_utc": inc.report_mtime_utc,
        "kind": inc.kind,
        "error": inc.error_text,
    }


def _row(
    mid: str,
    entry: dict[str, Any],
    reg: Optional[ModelEntry],
    err: str,
    category: str,
    short_label: str,
    *,
    primary_source: str = "run_state",
    historical_only: bool = False,
    historical_incidents: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": mid,
        "failure_category": category,
        "reason_kind": short_label,
        "run_state_status": entry.get("status") if entry else "—",
        "drive": entry.get("drive") if entry else None,
        "updated_at": entry.get("updated_at") if entry else None,
        "error": err,
        "primary_source": primary_source,
        "historical_only": historical_only,
    }
    if historical_incidents is not None:
        row["historical_incidents"] = historical_incidents
    if reg:
        row["hf_repo"] = reg.hf_repo
        row["tier"] = reg.tier
        row["registry_drive"] = reg.drive
        row["requires_auth"] = reg.requires_auth
    return row


def build_failed_registry_payload(
    *,
    state_path: Path,
    config_dir: Path,
    registry_path: Path,
    drives_path: Optional[Path],
    include_skipped: bool = False,
    include_historical: bool = True,
    historical_report_dirs: Optional[list[Path]] = None,
) -> dict[str, Any]:
    state_path = state_path.resolve()
    if not state_path.exists():
        raise FileNotFoundError(f"run_state not found: {state_path}")

    raw = json.loads(state_path.read_text(encoding="utf-8"))
    models_state: dict[str, Any] = raw.get("models", {})

    cfg = config_dir.resolve()
    dp = drives_path.resolve() if drives_path is not None else Path("/nonexistent")
    merged: dict[str, ModelEntry] = merge_registry_models(cfg, dp)
    if not merged and registry_path.exists():
        reg = load_registry(
            registry_path.resolve(),
            dp if dp.exists() else None,
        )
        merged = {m.id: m for m in reg.models}

    report_dirs: list[Path] = []
    if include_historical:
        report_dirs = [state_path.parent / "logs"]
        if historical_report_dirs:
            report_dirs.extend(Path(p).resolve() for p in historical_report_dirs)
        seen: set[Path] = set()
        uniq: list[Path] = []
        for p in report_dirs:
            rp = p.resolve()
            if rp not in seen:
                seen.add(rp)
                uniq.append(rp)
        report_dirs = uniq
    report_paths = discover_run_report_paths(*report_dirs) if include_historical else []
    hist_by_id = _aggregate_historical(report_paths) if report_paths else {}

    entries: dict[str, dict[str, Any]] = {}
    summary_status: dict[str, int] = defaultdict(int)
    historical_only_count = 0

    for mid, entry in sorted(models_state.items(), key=lambda x: x[0].lower()):
        st = entry.get("status", "")
        if st == STATUS_FAILED:
            summary_status["failed"] += 1
            err = _error_text(entry)
            cat, label = classify_failure_reason(err)
            hinc = [
                _incident_to_dict(x)
                for x in hist_by_id.get(mid, [])[:_MAX_HISTORICAL_INCIDENTS_PER_MODEL]
            ]
            entries[mid] = _row(
                mid,
                entry,
                merged.get(mid),
                err,
                cat,
                label,
                primary_source="run_state",
                historical_only=False,
                historical_incidents=hinc,
            )
        elif include_skipped and st == STATUS_SKIPPED:
            summary_status["skipped"] += 1
            err = _error_text(entry) or "skipped (gated / no token)"
            hinc = [
                _incident_to_dict(x)
                for x in hist_by_id.get(mid, [])[:_MAX_HISTORICAL_INCIDENTS_PER_MODEL]
            ]
            entries[mid] = _row(
                mid,
                entry,
                merged.get(mid),
                err,
                CAT_SKIPPED_GATED,
                "skipped",
                primary_source="run_state",
                historical_only=False,
                historical_incidents=hinc,
            )

    for mid, incidents in hist_by_id.items():
        if mid in entries:
            continue
        dl = [x for x in incidents if x.kind == "download_fail"]
        vf = [x for x in incidents if x.kind == "verify_fail"]
        sk = [x for x in incidents if x.kind == "skip"]
        rs_entry = models_state.get(mid, {})

        if dl or vf:
            pick = dl[0] if dl else vf[0]
            cat, label = classify_failure_reason(pick.error_text)
            hinc = [
                _incident_to_dict(x)
                for x in incidents[:_MAX_HISTORICAL_INCIDENTS_PER_MODEL]
            ]
            entries[mid] = _row(
                mid,
                rs_entry,
                merged.get(mid),
                pick.error_text,
                cat,
                label,
                primary_source="run_report",
                historical_only=True,
                historical_incidents=hinc,
            )
            historical_only_count += 1
        elif sk and include_skipped:
            pick = sk[0]
            hinc = [
                _incident_to_dict(x)
                for x in incidents[:_MAX_HISTORICAL_INCIDENTS_PER_MODEL]
            ]
            entries[mid] = _row(
                mid,
                rs_entry,
                merged.get(mid),
                pick.error_text,
                CAT_SKIPPED_GATED,
                "skipped (run report)",
                primary_source="run_report",
                historical_only=True,
                historical_incidents=hinc,
            )
            historical_only_count += 1

    by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sorted(entries.values(), key=lambda r: r["id"].lower()):
        cat = row["failure_category"]
        by_cat[cat].append(row)

    summary_by_category = {c: len(by_cat.get(c, [])) for c in _CATEGORY_ORDER if by_cat.get(c)}

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_state": str(state_path),
        "historical": {
            "enabled": include_historical,
            "report_files_scanned": len(report_paths),
            "report_directories": [str(p) for p in report_dirs],
            "distinct_models_from_reports": len(hist_by_id),
            "models_historical_only": historical_only_count,
        },
        "summary": {
            "total_failed": summary_status.get("failed", 0),
            "total_skipped_included": summary_status.get("skipped", 0) if include_skipped else 0,
            "by_category": summary_by_category,
            "total_rows": len(entries),
        },
        "categories": {c: by_cat[c] for c in _CATEGORY_ORDER if by_cat.get(c)},
    }


def write_failed_registry_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(
        payload,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )
    header = (
        "# Failed / skipped download registry — generated; refresh with:\n"
        "#   uv run archiver failed-registry\n"
        "# Optional: --state PATH  --include-skipped  --no-historical\n"
        "#   --reports-dir /mnt/models/d3/logs  (repeatable; default: <state-dir>/logs)\n\n"
    )
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(header + text, encoding="utf-8")
    tmp.replace(path)


def write_failed_registry_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Failed model registry",
        "",
        f"_Generated (UTC): `{payload['generated_at_utc']}`_",
        "",
        f"**Source:** `{payload['source_state']}`",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|--------|------:|",
    ]
    s = payload["summary"]
    lines.append(f"| Total failed (run_state) | {s['total_failed']} |")
    if s.get("total_skipped_included"):
        lines.append(f"| Skipped (included) | {s['total_skipped_included']} |")
    lines.append(f"| Total rows (merged) | {s.get('total_rows', '—')} |")
    lines.append("")
    lines.append("| Category | Models |")
    lines.append("|----------|-------:|")
    for cat, n in sorted(s.get("by_category", {}).items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| `{cat}` | {n} |")
    lines.append("")

    hist = payload.get("historical") or {}
    if hist.get("enabled"):
        lines.append("### Historical run reports (`run-report-*.md`)")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Report files scanned | {hist.get('report_files_scanned', 0)} |")
        lines.append(f"| Distinct models in reports | {hist.get('distinct_models_from_reports', 0)} |")
        lines.append(f"| Rows historical-only (not failed in run_state now) | {hist.get('models_historical_only', 0)} |")
        dirs = hist.get("report_directories") or []
        lines.append(f"| Directories | `{', '.join(dirs)}` |")
        lines.append("")

    cat_titles = {
        CAT_DISK_SPACE: "Disk space (ENOSPC)",
        CAT_UNAVAILABLE: "Unavailable (404 / resolve)",
        CAT_AUTH: "Auth / gated",
        CAT_FAILED_SHARDS: "Failed shards / retries exhausted",
        CAT_VERIFY: "Verification / checksum",
        CAT_OTHER: "Other",
        CAT_SKIPPED_GATED: "Skipped (gated / token)",
    }

    for cat, rows in payload.get("categories", {}).items():
        title = cat_titles.get(cat, cat)
        lines.append(f"## {title} (`{cat}`)")
        lines.append("")
        lines.append(
            "| Model id | Drive | Tier | Reason kind | Primary | Hist-only | "
            "#inc | Updated (UTC) |"
        )
        lines.append(
            "|----------|-------|------|-------------|---------|-----------|"
            "-----|---------------|"
        )
        for r in rows:
            mid = r["id"].replace("|", "\\|")
            drv = (r.get("drive") or "—").replace("|", "\\|")
            tier = (r.get("tier") or "—").replace("|", "\\|")
            rk = (r.get("reason_kind") or "—").replace("|", "\\|")
            prim = (r.get("primary_source") or "—").replace("|", "\\|")
            ho = "yes" if r.get("historical_only") else "—"
            ninc = len(r.get("historical_incidents") or [])
            upd = (r.get("updated_at") or "—")[:19].replace("|", "\\|")
            lines.append(
                f"| `{mid}` | {drv} | {tier} | {rk} | {prim} | {ho} | {ninc} | {upd} |"
            )
        lines.append("")
        lines.append("<details><summary>Error text + run-report history</summary>")
        lines.append("")
        for r in rows:
            lines.append(f"### `{r['id']}`")
            lines.append("")
            err = (r.get("error") or "—").strip()
            lines.append("**Primary error:**")
            lines.append("")
            lines.append("```")
            lines.append(err[:8000] if len(err) <= 8000 else err[:8000] + "\n… [truncated]")
            lines.append("```")
            lines.append("")
            hinc = r.get("historical_incidents") or []
            if hinc:
                lines.append("**Incidents from run reports (newest first):**")
                lines.append("")
                for hi in hinc[:20]:
                    rf = hi.get("report_file", "—")
                    k = hi.get("kind", "—")
                    lines.append(f"- `{k}` — `{rf}`")
                    e = (hi.get("error") or "—").strip()
                    lines.append("")
                    lines.append("```")
                    lines.append(e[:2000] if len(e) <= 2000 else e[:2000] + "\n… [truncated]")
                    lines.append("```")
                    lines.append("")
        lines.append("</details>")
        lines.append("")

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines), encoding="utf-8")
    tmp.replace(path)
