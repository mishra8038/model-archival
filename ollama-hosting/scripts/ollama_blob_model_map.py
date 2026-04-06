#!/usr/bin/env python3
"""
Build a table of which on-disk blob files belong to which Ollama library tag.

Ollama stores:
  models/manifests/registry.ollama.ai/library/<model>/<tag>  → JSON manifest
  models/blobs/sha256-<hex>                                   → layer/config payload
  models/blobs/sha256-<hex>-partial*                         → in-flight download

Each manifest references a config digest and one or more layer digests. This script
joins manifest → digest → blob path (if present).

Usage:
  ./scripts/ollama_blob_model_map.py ~/.ollama
  ./scripts/ollama_blob_model_map.py /mnt/models/d5/supermicro --format csv > blobs.csv
  ./scripts/ollama_blob_model_map.py /path --format json

Shared blobs (same digest used by multiple tags) appear once per tag row.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Iterator


def _digests_ordered(obj: dict[str, Any]) -> list[tuple[str, str, int]]:
    """Return (role, digest, index) in manifest order: config first, then layers."""
    out: list[tuple[str, str, int]] = []
    idx = 0
    cfg = obj.get("config")
    if isinstance(cfg, dict) and cfg.get("digest"):
        out.append(("config", str(cfg["digest"]), idx))
        idx += 1
    for layer in obj.get("layers") or []:
        if isinstance(layer, dict) and layer.get("digest"):
            out.append(("layer", str(layer["digest"]), idx))
            idx += 1
    return out


def _resolve_blob(blobs: Path, digest: str) -> tuple[str | None, int | None, bool]:
    """Return (relative name under blobs/, size, is_partial)."""
    if not digest or not isinstance(digest, str):
        return None, None, False
    hexpart = digest.split(":", 1)[-1] if ":" in digest else digest
    exact = blobs / ("sha256-" + hexpart)
    if exact.is_file():
        return exact.name, exact.stat().st_size, False
    matches = sorted(blobs.glob("sha256-" + hexpart + "*"))
    files = [p for p in matches if p.is_file()]
    if not files:
        return None, None, False
    p = files[0]
    partial = "partial" in p.name.lower()
    return p.name, p.stat().st_size, partial


def iter_rows(ollama_home: Path) -> Iterator[dict[str, Any]]:
    root = ollama_home.resolve()
    lib = root / "models" / "manifests" / "registry.ollama.ai" / "library"
    blobs = root / "models" / "blobs"
    if not lib.is_dir():
        return
    for mf in sorted(lib.rglob("*")):
        if not mf.is_file():
            continue
        try:
            rel = mf.relative_to(lib)
        except ValueError:
            continue
        parts = rel.parts
        if len(parts) < 2:
            continue
        model = parts[0]
        tag = "/".join(parts[1:])
        descriptor = f"{model}:{tag}"
        try:
            obj = json.loads(mf.read_text(encoding="utf-8", errors="replace"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(obj, dict):
            continue
        for role, digest, ord_idx in _digests_ordered(obj):
            name, size, is_partial = _resolve_blob(blobs, digest) if blobs.is_dir() else (None, None, False)
            yield {
                "model_tag": descriptor,
                "role": role,
                "layer_order": ord_idx,
                "digest": digest,
                "blob_file": name or "",
                "size_bytes": size if size is not None else "",
                "blob_present": bool(name),
                "is_partial_file": is_partial,
            }


def main() -> None:
    ap = argparse.ArgumentParser(description="Map Ollama library tags to blob files.")
    ap.add_argument(
        "ollama_home",
        type=Path,
        help="Ollama data root (directory containing models/manifests and models/blobs)",
    )
    ap.add_argument("--format", choices=("csv", "json", "tsv"), default="csv")
    ap.add_argument(
        "--out",
        type=Path,
        help="Write to file instead of stdout",
    )
    args = ap.parse_args()
    home = args.ollama_home
    if not home.is_dir():
        print(f"error: not a directory: {home}", file=sys.stderr)
        sys.exit(2)

    rows = list(iter_rows(home))
    out_fp = open(args.out, "w", encoding="utf-8", newline="") if args.out else sys.stdout
    try:
        if args.format == "json":
            json.dump(rows, out_fp, indent=2)
            out_fp.write("\n")
        elif args.format == "csv":
            w = csv.DictWriter(
                out_fp,
                fieldnames=[
                    "model_tag",
                    "role",
                    "layer_order",
                    "digest",
                    "blob_file",
                    "size_bytes",
                    "blob_present",
                    "is_partial_file",
                ],
            )
            w.writeheader()
            w.writerows(rows)
        else:
            w = csv.DictWriter(
                out_fp,
                fieldnames=[
                    "model_tag",
                    "role",
                    "layer_order",
                    "digest",
                    "blob_file",
                    "size_bytes",
                    "blob_present",
                    "is_partial_file",
                ],
                delimiter="\t",
            )
            w.writeheader()
            w.writerows(rows)
    finally:
        if args.out:
            out_fp.close()

    if rows:
        print(f"# {len(rows)} row(s) from {home}", file=sys.stderr)
    else:
        print(f"# no library manifests under {home}/models/manifests/.../library", file=sys.stderr)


if __name__ == "__main__":
    main()
