#!/usr/bin/env python3
"""
Run on the archival VM (arguments = Ollama archive roots), or via:

  cat scripts/ollama_archive_vm_maintain.py | ssh user@vm python3 - root1 root2 ...

Removes (unless --keep-ollama-partials):
  - Ollama incomplete blob shards (*partial* under models/blobs/)
  - Empty or leftover .rsync-partial directories from interrupted rsync

With --keep-ollama-partials: Ollama in-flight shard files are left intact so another host
can resume pulls after mirroring ~/.ollama (see docs/OLLAMA-RESUME-ON-ARCHIVE-VM.md).

Integrity check (read-only): reports manifests under library/ that reference missing blob files.
Does not delete manifests or complete blobs.
"""
from __future__ import annotations

import argparse
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


def maintain_root(root: Path, *, keep_ollama_partials: bool) -> None:
    root = root.resolve()
    blobs = root / "models" / "blobs"
    removed_partials = 0
    if blobs.is_dir():
        if keep_ollama_partials:
            print(f"{root}: keeping Ollama *partial* blob shards (--keep-ollama-partials)")
        else:
            for f in list(blobs.iterdir()):
                if not f.is_file():
                    continue
                if "partial" in f.name.lower():
                    try:
                        f.unlink()
                        removed_partials += 1
                    except OSError as e:
                        print(f"{root}: warn: could not remove partial {f.name}: {e}", file=sys.stderr)
            print(f"{root}: removed {removed_partials} Ollama *partial* blob file(s)")

    # rsync --partial-dir leftovers (under this archive root only); not used by Ollama resume
    for d in sorted(root.rglob(".rsync-partial"), key=lambda p: len(p.parts), reverse=True):
        if not d.is_dir():
            continue
        try:
            shutil.rmtree(d, ignore_errors=True)
        except OSError as e:
            print(f"{root}: warn: could not rmtree {d}: {e}", file=sys.stderr)
    print(f"{root}: pruned .rsync-partial dirs")

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
    ap = argparse.ArgumentParser(description="Clean partial Ollama blobs + rsync debris; integrity check.")
    ap.add_argument(
        "--keep-ollama-partials",
        action="store_true",
        help="Do not delete models/blobs/*partial* (use after rsync mirroring for resume on this tree).",
    )
    ap.add_argument("roots", nargs="*", type=Path, help="Ollama data roots (each contains models/)")
    args = ap.parse_args()
    roots = [r for r in args.roots if str(r).strip()]
    if not roots:
        ap.print_help()
        sys.exit(2)
    for r in roots:
        if not r.is_dir():
            print(f"{r}: skip (not a directory)", file=sys.stderr)
            continue
        maintain_root(r, keep_ollama_partials=args.keep_ollama_partials)


if __name__ == "__main__":
    main()
