#!/usr/bin/env python3
"""
Run on the archival VM (arguments = Ollama archive roots), or via:

  cat scripts/ollama_archive_vm_maintain.py | ssh user@vm python3 - root1 root2 ...

Removes:
  - Ollama incomplete blob shards (*partial* under models/blobs/)
  - Empty or leftover .rsync-partial directories from interrupted rsync

Integrity check (read-only): reports manifests under library/ that reference missing blob files.
Does not delete manifests or complete blobs.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


def _digest_paths(blobs: Path, digest: str) -> list[Path]:
    if not digest or not isinstance(digest, str):
        return []
    hexpart = digest.split(":", 1)[-1] if ":" in digest else digest
    p = blobs / ("sha256-" + hexpart)
    if p.is_file():
        return [p]
    found = list(blobs.glob("sha256-" + hexpart + "*"))
    return [x for x in found if x.is_file()]


def _digests_from_manifest(obj: dict) -> list[str]:
    out: list[str] = []
    cfg = obj.get("config")
    if isinstance(cfg, dict) and cfg.get("digest"):
        out.append(str(cfg["digest"]))
    for layer in obj.get("layers") or []:
        if isinstance(layer, dict) and layer.get("digest"):
            out.append(str(layer["digest"]))
    return out


def maintain_root(root: Path) -> None:
    root = root.resolve()
    blobs = root / "models" / "blobs"
    removed_partials = 0
    if blobs.is_dir():
        for f in list(blobs.iterdir()):
            if not f.is_file():
                continue
            if "partial" in f.name.lower():
                try:
                    f.unlink()
                    removed_partials += 1
                except OSError as e:
                    print(f"{root}: warn: could not remove partial {f.name}: {e}", file=sys.stderr)

    # rsync --partial-dir leftovers (under this archive root only)
    for d in sorted(root.rglob(".rsync-partial"), key=lambda p: len(p.parts), reverse=True):
        if not d.is_dir():
            continue
        try:
            shutil.rmtree(d, ignore_errors=True)
        except OSError as e:
            print(f"{root}: warn: could not rmtree {d}: {e}", file=sys.stderr)

    print(f"{root}: removed {removed_partials} Ollama *partial* blob file(s); pruned .rsync-partial dirs")

    lib = root / "models" / "manifests" / "registry.ollama.ai" / "library"
    if not lib.is_dir() or not blobs.is_dir():
        return

    broken: list[str] = []
    for mf in lib.rglob("*"):
        if not mf.is_file():
            continue
        try:
            obj = json.loads(mf.read_text(encoding="utf-8", errors="replace"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(obj, dict):
            continue
        rel = mf.relative_to(lib)
        desc = "/".join(rel.parts)
        for d in _digests_from_manifest(obj):
            if not _digest_paths(blobs, d):
                broken.append(desc)
                break

    if broken:
        n = len(broken)
        sample = broken[:5]
        more = f" (+{n - len(sample)} more)" if n > len(sample) else ""
        print(
            f"{root}: INTEGRITY WARNING — {n} manifest(s) reference missing blob(s); "
            f"examples: {sample}{more}. Re-sync those tags from a complete supermicro cache."
        )
    else:
        print(f"{root}: integrity OK (all scanned manifests have blob files on disk)")


def main() -> None:
    roots = [Path(a) for a in sys.argv[1:] if a.strip()]
    if not roots:
        print("usage: ollama_archive_vm_maintain.py ARCHIVE_ROOT [ARCHIVE_ROOT ...]", file=sys.stderr)
        sys.exit(2)
    for r in roots:
        if not r.is_dir():
            print(f"{r}: skip (not a directory)", file=sys.stderr)
            continue
        maintain_root(r)


if __name__ == "__main__":
    main()
