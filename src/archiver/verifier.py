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

def write_descriptor(
    model_id: str,
    hf_repo: str,
    commit_sha: str,
    tier: str,
    licence: str,
    requires_auth: bool,
    notes: Optional[str],
    files: list[dict],  # [{"path": str, "sha256": str, "size_bytes": int}]
    dest_dir: Path,
) -> None:
    """
    Write two human/machine-readable descriptor files into dest_dir:

      DESCRIPTOR.json  — structured JSON, all fields, machine-parseable
      DESCRIPTOR.md    — plain Markdown, for quick inspection with cat/less

    These are separate from manifest.json (which is a pure integrity artifact).
    The descriptor answers: what is this, where did it come from, when was it
    archived, how big is it, what licence applies.
    """
    total_bytes = sum(f["size_bytes"] for f in files)
    archived_at = datetime.now(timezone.utc).isoformat()

    # ----- TIER labels -----
    tier_labels = {
        "A": "Tier A — Major model, raw BF16 full-precision",
        "B": "Tier B — Code-specialist model, raw BF16 full-precision",
        "C": "Tier C — Quantized GGUF",
        "D": "Tier D — Uncensored / abliterated variant",
    }

    # ----- JSON descriptor -----
    descriptor = {
        "descriptor_version": "1.0",
        "model_id": model_id,
        "hf_repo": hf_repo,
        "hf_url": f"https://huggingface.co/{hf_repo}",
        "commit_sha": commit_sha,
        "hf_commit_url": f"https://huggingface.co/{hf_repo}/tree/{commit_sha}",
        "tier": tier,
        "tier_description": tier_labels.get(tier, tier),
        "licence": licence,
        "requires_auth": requires_auth,
        "notes": notes or "",
        "archived_at": archived_at,
        "file_count": len(files),
        "total_size_bytes": total_bytes,
        "total_size_human": _human_bytes(total_bytes),
        "integrity": {
            "method": "SHA-256",
            "manifest": "manifest.json",
            "sidecars": "each weight file has a <filename>.sha256 sidecar",
            "verify_cmd": f"archiver verify {model_id}",
        },
        "files_summary": [
            {"path": f["path"], "size": _human_bytes(f["size_bytes"])}
            for f in files
        ],
    }

    json_path = dest_dir / "DESCRIPTOR.json"
    tmp_j = json_path.with_suffix(".json.tmp")
    tmp_j.write_text(json.dumps(descriptor, indent=2))
    tmp_j.replace(json_path)

    # ----- Markdown descriptor -----
    size_h = _human_bytes(total_bytes)
    auth_note = "Yes — HuggingFace token required" if requires_auth else "No — publicly available"
    file_lines = "\n".join(
        f"| `{f['path']}` | {_human_bytes(f['size_bytes'])} |"
        for f in files
    )

    md = f"""# {model_id}

## Identity

| Field | Value |
|-------|-------|
| Model ID | `{model_id}` |
| HuggingFace repo | [{hf_repo}](https://huggingface.co/{hf_repo}) |
| Pinned commit | [`{commit_sha[:12]}…`]({f"https://huggingface.co/{hf_repo}/tree/{commit_sha}"}) |
| Tier | {tier_labels.get(tier, tier)} |
| Licence | {licence} |
| Token-gated | {auth_note} |

## Archive Metadata

| Field | Value |
|-------|-------|
| Archived at | {archived_at} |
| Total size | {size_h} |
| File count | {len(files)} |
| Integrity | SHA-256 per file (see `manifest.json` and `.sha256` sidecars) |

{"## Notes" + chr(10) + chr(10) + notes + chr(10) if notes else ""}
## Verification

```bash
# Quick check (sidecar existence only — fast):
archiver status {model_id}

# Full re-hash of every file (slow — reads all data from disk):
archiver verify {model_id}

# Manual single-file check:
sha256sum -c <filename>.sha256
```

## Files

| File | Size |
|------|------|
{file_lines}
"""

    md_path = dest_dir / "DESCRIPTOR.md"
    tmp_m = md_path.with_suffix(".md.tmp")
    tmp_m.write_text(md)
    tmp_m.replace(md_path)

    log.debug("Wrote DESCRIPTOR.json + DESCRIPTOR.md for %s", model_id)


def _human_bytes(n: int) -> str:
    """Return a human-readable byte count string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} PB"


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
