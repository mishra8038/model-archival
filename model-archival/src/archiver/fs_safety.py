"""
Filesystem safety helpers.

Policy: never delete model data (anything under /mnt/models/d{1,2,3}/ and similar drive
mounts). When the downloader needs to "remove" a file (e.g. corrupt shard), we quarantine
it by renaming into a drive-local .quarantine directory.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from pathlib import Path


def _drive_root_for(path: Path) -> Path | None:
    p = path.resolve()
    parts = p.parts
    # Common layout: /mnt/models/d1/...
    if len(parts) >= 4 and parts[0] == "/" and parts[1] == "mnt" and parts[2] == "models":
        return Path("/", "mnt", "models", parts[3])
    return None


def _is_model_data_path(path: Path) -> bool:
    """
    Return True if the path is considered "model data" and must never be deleted.

    We treat anything on model drives (d1/d2/d3) as model data, including .tmp partials.
    """
    root = _drive_root_for(path)
    if root is None:
        return False
    return root.name in {"d1", "d2", "d3"}


def _completed_model_root_for(path: Path) -> Path | None:
    """
    If *path* is inside a completed model directory, return that model directory.

    Heuristic: a completed model directory contains a manifest.json at its root.
    """
    p = path.resolve()
    drive_root = _drive_root_for(p)
    if drive_root is None:
        return None

    cur = p if p.is_dir() else p.parent
    # Walk upwards until the drive root.
    while True:
        manifest = cur / "manifest.json"
        if manifest.exists():
            return cur
        if cur == drive_root:
            return None
        parent = cur.parent
        if parent == cur:
            return None
        cur = parent


def assert_not_completed_model_delete(path: Path) -> None:
    """
    Refuse to delete anything inside a completed model directory unless explicitly allowed.
    """
    if os.environ.get("ARCHIVER_ALLOW_MODEL_DELETE") == "1":
        return
    root = _completed_model_root_for(path)
    if root is not None:
        raise RuntimeError(
            f"Refusing to delete completed model data under {root}. "
            "Set ARCHIVER_ALLOW_MODEL_DELETE=1 to override (manual/human decision)."
        )


def quarantine_path(path: Path, reason: str) -> Path:
    """
    Move *path* aside by renaming it into <drive>/.quarantine/<timestamp>/... and return
    the new path. This is atomic within the same filesystem and avoids deleting bytes.
    """
    p = path
    if not p.exists() and not p.is_symlink():
        return p

    root = _drive_root_for(p)
    if root is None:
        # Outside model drives: just rename alongside (still no delete).
        root = p.parent

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    token = secrets.token_hex(4)
    quarantine_root = root / ".quarantine" / ts
    quarantine_root.mkdir(parents=True, exist_ok=True)

    # Preserve relative path under the drive root when possible.
    try:
        rel = p.resolve().relative_to(root)
        dest = quarantine_root / rel
    except Exception:
        dest = quarantine_root / p.name

    # Make the destination unique if needed.
    if dest.exists() or dest.is_symlink():
        dest = dest.with_name(dest.name + f".{token}")
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Include reason in a sidecar for later inspection.
    try:
        sidecar = dest.with_suffix(dest.suffix + ".quarantine-reason.txt")
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        sidecar.write_text(reason + "\n", encoding="utf-8")
    except Exception:
        pass

    os.rename(str(p), str(dest))
    return dest


def safe_remove(path: Path, reason: str) -> None:
    """
    Remove a file/path safely.

    - If the path is within a completed model directory (manifest.json present), refuse
      unless ARCHIVER_ALLOW_MODEL_DELETE=1 is set.
    - Otherwise quarantine by rename (never delete bytes).
    """
    if not (path.exists() or path.is_symlink()):
        return
    assert_not_completed_model_delete(path)
    quarantine_path(path, reason=reason)

