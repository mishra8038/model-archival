"""
D1 disk + HF evaluation for registry models with ``drive: d1``.

Used by ``scripts/evaluate_d1_incomplete.py`` and ``scripts/d1_prune_low_progress.py``.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Optional

import yaml
from huggingface_hub import HfApi
from huggingface_hub.utils import GatedRepoError, RepositoryNotFoundError

from archiver.downloader import (
    _check_manifest_complete,
    estimate_remaining_download_bytes,
    resolve_model_archive_files,
)
from archiver.models import load_registry


def load_narrow_ids(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {row["id"] for row in data.get("models", []) if row.get("id")}


def best_complete_rev(repo_base: Path) -> Optional[Path]:
    if not repo_base.is_dir():
        return None
    try:
        children = sorted(p for p in repo_base.iterdir() if p.is_dir())
    except OSError:
        return None
    for rev in children:
        if _check_manifest_complete(rev):
            return rev
    return None


def progress_pct(remaining: Optional[int], total_hf: Optional[int]) -> Optional[float]:
    if total_hf is None or total_hf <= 0:
        return None
    if remaining is None:
        return None
    return 100.0 * (total_hf - remaining) / total_hf


def gather_d1_incomplete_rows(
    *,
    registry_path: Path,
    drives_path: Path,
    narrow_registry_path: Optional[Path],
    api: HfApi,
) -> tuple[Any, int, list[dict[str, Any]], set[str]]:
    """
    Returns ``(d1_drive_config, complete_n, incomplete_rows, narrow_ids)``.
    Each incomplete row includes ``repo_base``, ``tmp_subdir`` as ``str`` paths,
    plus ``progress_pct`` when HF totals exist.
    """
    reg = load_registry(registry_path.resolve(), drives_path.resolve())
    d1 = reg.drives.get("d1")
    if not d1:
        raise ValueError("no d1 in drives.yaml")
    if not d1.mount_point.is_dir():
        raise FileNotFoundError(
            f"D1 mount not present: {d1.mount_point} (run on archive host)"
        )

    narrow_ids = load_narrow_ids(narrow_registry_path) if narrow_registry_path else set()

    d1_models = [m for m in reg.models if m.drive == "d1"]
    d1_models.sort(key=lambda m: m.id)

    complete_n = 0
    incomplete_rows: list[dict[str, Any]] = []

    for m in d1_models:
        org, name = m.hf_repo.split("/", 1)
        repo_base = d1.mount_point / m.content_subdir / org / name
        tmp_subdir = d1.mount_point / ".tmp" / m.id.replace("/", "_")
        done_rev = best_complete_rev(repo_base)
        if done_rev is not None:
            complete_n += 1
            continue

        row: dict[str, Any] = {
            "id": m.id,
            "hf_repo": m.hf_repo,
            "tier": m.tier,
            "in_narrow": m.id in narrow_ids,
            "repo_base": str(repo_base),
            "tmp_subdir": str(tmp_subdir),
            "content_subdir": m.content_subdir,
            "error": None,
            "remaining": None,
            "total_hf": None,
            "files_done_sidecar": None,
            "resolved_commit": None,
            "progress_pct": None,
        }

        try:
            file_infos = resolve_model_archive_files(m, api)
        except (GatedRepoError, RepositoryNotFoundError, OSError, ValueError) as e:
            row["error"] = str(e)[:800]
            incomplete_rows.append(row)
            continue
        except Exception as e:  # noqa: BLE001
            row["error"] = f"{type(e).__name__}: {e}"[:800]
            incomplete_rows.append(row)
            continue

        if not file_infos:
            row["error"] = "no files after registry filters"
            incomplete_rows.append(row)
            continue

        commit_sha = file_infos[0]["commit_sha"]
        dest_dir = repo_base / commit_sha
        rem, tot, done_n = estimate_remaining_download_bytes(
            file_infos=file_infos,
            dest_dir=dest_dir,
            tmp_subdir=tmp_subdir,
            repo_base=repo_base,
        )
        row["remaining"] = rem
        row["total_hf"] = tot
        row["files_done_sidecar"] = done_n
        row["resolved_commit"] = commit_sha[:12]
        row["progress_pct"] = progress_pct(rem, tot)
        incomplete_rows.append(row)

    return d1, complete_n, incomplete_rows, narrow_ids


def remove_models_from_yaml_registry(path: Path, remove_ids: set[str]) -> tuple[int, int]:
    """
    Drop any ``models[]`` entry whose ``id`` is in *remove_ids*.
    Returns ``(before_count, after_count)``. Atomic write via ``.tmp`` + replace.

    **Note:** PyYAML round-trip drops comments and may reorder keys — a ``.bak`` copy
    of the original file is written beside *path* first.
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    models = list(data.get("models") or [])
    before = len(models)
    data["models"] = [m for m in models if m.get("id") not in remove_ids]
    after = len(data["models"])
    if after == before:
        return before, after
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp.replace(path)
    return before, after


def strip_models_from_run_state(state_path: Path, remove_ids: set[str]) -> bool:
    """Remove ``models.<id>`` keys from run_state.json. Returns True if file was written."""
    if not state_path.is_file():
        return False
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    models = data.get("models")
    if not isinstance(models, dict):
        return False
    changed = False
    for mid in list(remove_ids):
        if mid in models:
            del models[mid]
            changed = True
    if not changed:
        return False
    tmp = state_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(state_path)
    return True
