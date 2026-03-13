from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List


DEFAULT_CHUNK_SIZE_MB = 8
DEFAULT_MIN_SIZE_MB = 32


@dataclass
class ChunkHashManifest:
    version: int
    file_name: str
    file_size: int
    chunk_size: int
    sha256_full: str
    chunks: List[str]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @staticmethod
    def from_json(data: str) -> "ChunkHashManifest":
        obj = json.loads(data)
        return ChunkHashManifest(
            version=obj["version"],
            file_name=obj["file_name"],
            file_size=obj["file_size"],
            chunk_size=obj["chunk_size"],
            sha256_full=obj["sha256_full"],
            chunks=list(obj["chunks"]),
        )


def _chunk_hash_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".sha256chunks.json")


def iter_files(root: Path, min_size_bytes: int) -> Iterable[Path]:
    if root.is_file():
        if root.stat().st_size >= min_size_bytes:
            yield root
        return
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            p = Path(dirpath) / name
            try:
                size = p.stat().st_size
            except FileNotFoundError:
                continue
            if size >= min_size_bytes:
                yield p


def compute_chunk_hashes(path: Path, chunk_size: int) -> ChunkHashManifest:
    h_full = hashlib.sha256()
    chunks: List[str] = []
    total = 0
    with path.open("rb") as f:
        while True:
            buf = f.read(chunk_size)
            if not buf:
                break
            total += len(buf)
            h_full.update(buf)
            h_chunk = hashlib.sha256()
            h_chunk.update(buf)
            chunks.append(h_chunk.hexdigest())
    return ChunkHashManifest(
        version=1,
        file_name=path.name,
        file_size=total,
        chunk_size=chunk_size,
        sha256_full=h_full.hexdigest(),
        chunks=chunks,
    )


def write_manifest(path: Path, manifest: ChunkHashManifest) -> None:
    out = _chunk_hash_path(path)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(manifest.to_json())
    tmp.replace(out)


def load_manifest(path: Path) -> ChunkHashManifest:
    mpath = _chunk_hash_path(path)
    return ChunkHashManifest.from_json(mpath.read_text())


def verify_file(path: Path) -> bool:
    manifest = load_manifest(path)
    if manifest.file_size != path.stat().st_size:
        return False
    recomputed = compute_chunk_hashes(path, manifest.chunk_size)
    if recomputed.sha256_full != manifest.sha256_full:
        return False
    if recomputed.chunks != manifest.chunks:
        return False
    return True


def cmd_hash(args: argparse.Namespace) -> None:
    root = Path(args.path).resolve()
    chunk_size = args.chunk_size_mb * 1024 * 1024
    min_size = args.min_size_mb * 1024 * 1024
    files = list(iter_files(root, min_size))
    for p in files:
        manifest = compute_chunk_hashes(p, chunk_size)
        write_manifest(p, manifest)
        print(f"hashed {p} ({manifest.file_size} bytes, {len(manifest.chunks)} chunks)")


def cmd_verify(args: argparse.Namespace) -> None:
    root = Path(args.path).resolve()
    min_size = args.min_size_mb * 1024 * 1024
    files = list(iter_files(root, min_size))
    any_failed = False
    for p in files:
        mpath = _chunk_hash_path(p)
        if not mpath.exists():
            print(f"SKIP no manifest for {p}")
            continue
        ok = verify_file(p)
        status = "OK" if ok else "FAIL"
        print(f"{status} {p}")
        if not ok:
            any_failed = True
    if any_failed:
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Chunked SHA-256 hashing for large model files."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_hash = sub.add_parser("hash", help="Generate chunked hashes for files.")
    p_hash.add_argument(
        "path",
        help="File or directory to process.",
    )
    p_hash.add_argument(
        "--chunk-size-mb",
        type=int,
        default=DEFAULT_CHUNK_SIZE_MB,
        help=f"Chunk size in MiB (default {DEFAULT_CHUNK_SIZE_MB}).",
    )
    p_hash.add_argument(
        "--min-size-mb",
        type=int,
        default=DEFAULT_MIN_SIZE_MB,
        help=f"Minimum file size in MiB to include (default {DEFAULT_MIN_SIZE_MB}).",
    )
    p_hash.set_defaults(func=cmd_hash)

    p_verify = sub.add_parser("verify", help="Verify files against chunk manifests.")
    p_verify.add_argument(
        "path",
        help="File or directory to verify.",
    )
    p_verify.add_argument(
        "--min-size-mb",
        type=int,
        default=DEFAULT_MIN_SIZE_MB,
        help=f"Minimum file size in MiB to include (default {DEFAULT_MIN_SIZE_MB}).",
    )
    p_verify.set_defaults(func=cmd_verify)

    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

