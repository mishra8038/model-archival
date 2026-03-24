#!/usr/bin/env python3
"""
Verify a model revision directory before GDrive upload (pristine check).

Uses the same logic as the archiver: manifest.json file list + SHA-256, or
*.sha256 sidecars if no manifest. Exits non-zero if any file fails or is missing.

Usage:
  python3 verify_local_model_dir.py /mnt/models/d3/quantized/org/repo/REV

  ARCHIVER_SRC=/path/to/model-archival/src python3 verify_local_model_dir.py /path/to/rev
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _archiver_src() -> Path:
  env = os.environ.get("ARCHIVER_SRC")
  if env:
    return Path(env).resolve()
  # repo root / model-archival/src (gdrive-archival -> model-archival -> model-archival/src)
  here = Path(__file__).resolve().parent
  return (here.parent / "local" / "src").resolve()


def main() -> int:
  parser = argparse.ArgumentParser(description="SHA-256 verify model dir before cloud upload.")
  parser.add_argument(
    "model_dir",
    type=Path,
    help="Local path to the model revision directory (contains manifest.json or weight sidecars)",
  )
  args = parser.parse_args()
  d = args.model_dir.resolve()
  if not d.is_dir():
    print(f"error: not a directory: {d}", file=sys.stderr)
    return 2

  src = _archiver_src()
  if not (src / "archiver" / "verifier.py").is_file():
    print(
      f"error: archiver source not found at {src} "
      "(set ARCHIVER_SRC to model-archival/src on the archive host)",
      file=sys.stderr,
    )
    return 2

  if str(src) not in sys.path:
    sys.path.insert(0, str(src))
  from archiver.verifier import verify_model_dir

  results = verify_model_dir(d)
  if not results:
    print(f"error: nothing to verify under {d} (no manifest.json and no *.sha256 sidecars)", file=sys.stderr)
    return 3

  failed = [r for r in results if not r.get("ok", False)]
  ok_n = len(results) - len(failed)
  print(f"verified {ok_n}/{len(results)} file(s) under {d}")
  for r in results:
    status = "OK" if r.get("ok") else "FAIL"
    print(f"  [{status}] {r.get('path', '?')}")
    if not r.get("ok"):
      print(f"        expected {r.get('expected', '')[:16]}… actual {r.get('actual', '')[:16]}…")

  if failed:
    print("verification failed — do not upload until fixed", file=sys.stderr)
    return 1
  print("pristine — safe to upload")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
