"""SHA-256 verification and manifest management."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB read chunks


def sha256_file(path: Path, progress_cb=None) -> str:
    """Compute SHA-256 of a file. Optionally call progress_cb(bytes_done, total)."""
    h = hashlib.sha256()
    total = path.stat().st_size
    done = 0
    with path.open("rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            h.update(chunk)
            done += len(chunk)
            if progress_cb:
                progress_cb(done, total)
    return h.hexdigest()


def read_sidecar(path: Path) -> Optional[str]:
    """Read the .sha256 sidecar file next to *path*. Returns hex string or None."""
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if sidecar.exists():
        return sidecar.read_text().strip().split()[0]
    return None


def write_sidecar(path: Path, digest: str) -> None:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    sidecar.write_text(f"{digest}  {path.name}\n")


def verify_file(path: Path, expected: Optional[str] = None, progress_cb=None) -> tuple[bool, str]:
    """
    Verify a file's integrity.
    Returns (ok, actual_digest).
    If expected is None, checks against sidecar only.
    """
    if not path.exists():
        return False, ""
    actual = sha256_file(path, progress_cb)
    if expected:
        return actual == expected, actual
    stored = read_sidecar(path)
    if stored:
        return actual == stored, actual
    # No reference — nothing to compare against; return True but note absence
    return True, actual


# ------------------------------------------------------------------
# Manifest
# ------------------------------------------------------------------

def write_manifest(
    model_id: str,
    hf_repo: str,
    commit_sha: str,
    tier: str,
    files: list[dict],  # [{"path": str, "sha256": str, "size_bytes": int}]
    dest_dir: Path,
) -> dict:
    manifest = {
        "model_id": model_id,
        "hf_repo": hf_repo,
        "commit_sha": commit_sha,
        "tier": tier,
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
        "total_size_bytes": sum(f["size_bytes"] for f in files),
        "file_count": len(files),
    }
    manifest_path = dest_dir / "manifest.json"
    tmp = manifest_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2))
    tmp.replace(manifest_path)
    log.debug("Wrote manifest for %s (%d files)", model_id, len(files))
    return manifest


def load_manifest(dest_dir: Path) -> Optional[dict]:
    p = dest_dir / "manifest.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


# ------------------------------------------------------------------
# Global checksum index
# ------------------------------------------------------------------

def append_global_index(index_path: Path, manifest: dict) -> None:
    """Append a single JSON-L record to the global checksum index."""
    index_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_id": manifest["model_id"],
        "hf_repo": manifest["hf_repo"],
        "commit_sha": manifest["commit_sha"],
        "tier": manifest["tier"],
        "files": manifest["files"],
        "total_size_bytes": manifest["total_size_bytes"],
    }
    with index_path.open("a") as f:
        f.write(json.dumps(record) + "\n")


def verify_model_dir(dest_dir: Path) -> list[dict]:
    """
    Verify all files in dest_dir against their .sha256 sidecars.
    Returns list of {path, ok, expected, actual}.
    """
    manifest = load_manifest(dest_dir)
    if manifest is None:
        log.warning("No manifest.json in %s — scanning for sidecars", dest_dir)
        results = []
        for sidecar in sorted(dest_dir.glob("*.sha256")):
            target = sidecar.with_suffix("")
            if not target.exists():
                continue
            stored = sidecar.read_text().strip().split()[0]
            ok, actual = verify_file(target, stored)
            results.append({"path": str(target), "ok": ok, "expected": stored, "actual": actual})
        return results

    results = []
    for entry in manifest["files"]:
        target = dest_dir / entry["path"]
        ok, actual = verify_file(target, entry["sha256"])
        results.append({
            "path": entry["path"],
            "ok": ok,
            "expected": entry["sha256"],
            "actual": actual,
            "size_bytes": entry.get("size_bytes", 0),
        })
    return results
