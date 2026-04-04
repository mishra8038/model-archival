"""
Approximate download queue order for capacity planning (matches scheduler sort keys).

Used when preflight aborts on low disk space or to preview work before a long run.
Does not perform network checks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import psutil

from archiver.models import ModelEntry, Registry
from archiver.state import RunState, STATUS_DEFERRED_LARGE, STATUS_SKIPPED


def load_priority_overrides(path: Optional[Path]) -> dict[str, int]:
    if not path or not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {
            k: int(v)
            for k, v in raw.items()
            if isinstance(k, str) and isinstance(v, (int, float))
        }
    except Exception:
        return {}


def scheduler_eligible_models(
    models: list[ModelEntry],
    state: RunState,
    token_results: dict[str, bool],
) -> tuple[list[ModelEntry], list[tuple[str, str]]]:
    """
    Same eligibility rules as ``DriveScheduler.build_queue`` (no skipped-gated state write).

    Returns ``(eligible, excluded)`` where *excluded* is ``(model_id, reason)``.
    """
    excluded: list[tuple[str, str]] = []
    eligible: list[ModelEntry] = []
    for m in models:
        if state.is_complete(m.id):
            excluded.append((m.id, "complete"))
            continue
        st = state.get_model_status(m.id)
        if st == STATUS_SKIPPED:
            excluded.append((m.id, "skipped"))
            continue
        if st == STATUS_DEFERRED_LARGE:
            excluded.append((m.id, "deferred_large"))
            continue
        if m.requires_auth and not token_results.get(m.id, True):
            excluded.append((m.id, "gated (no access)"))
            continue
        if m.requires_auth and not token_results:
            if m.priority >= 2:
                excluded.append((m.id, "gated deferred (no HF_TOKEN)"))
                continue
        eligible.append(m)
    return eligible, excluded


def group_by_drive_ordered(
    eligible: list[ModelEntry],
    overrides: dict[str, int],
    drive_labels: list[str],
) -> list[tuple[str, list[ModelEntry]]]:
    """
    One entry per configured *drive_labels* (e.g. d1…d5 order). Models on that drive
    sorted by ``(effective_priority, model_id)`` — order used when a slot opens on that disk.
    """
    from collections import defaultdict

    buck: dict[str, list[ModelEntry]] = defaultdict(list)
    for m in eligible:
        buck[m.drive].append(m)
    for lab in buck:
        buck[lab].sort(key=lambda m: (overrides.get(m.id, m.priority), m.id))
    return [(lab, list(buck.get(lab, []))) for lab in drive_labels]


def approximate_download_order(
    models: list[ModelEntry],
    overrides: dict[str, int],
) -> list[ModelEntry]:
    """
    Deterministic order: ``(effective_priority, drive, model_id)`` — same key as
    ``DriveScheduler._next_model`` candidate sort. With a single worker this is exact;
    with multiple workers and bandwidth gating, actual interleaving may differ.
    """
    return sorted(
        models,
        key=lambda m: (overrides.get(m.id, m.priority), m.drive, m.id),
    )


def drive_free_space_gib(registry: Registry) -> dict[str, tuple[float, float, float]]:
    """``label -> (free_gib, total_gib, used_percent)`` using binary GiB."""
    out: dict[str, tuple[float, float, float]] = {}
    for label, d in sorted(registry.drives.items()):
        mp = d.mount_point
        if not mp.exists():
            out[label] = (0.0, 0.0, 100.0)
            continue
        u = psutil.disk_usage(str(mp))
        gib = 1024**3
        out[label] = (u.free / gib, u.total / gib, float(u.percent))
    return out
