from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, List


DEFAULT_MIN_SIZE_MB = 32
DEFAULT_REDUNDANCY_PCT = 10


def iter_target_files(root: Path, min_size_bytes: int) -> Iterable[Path]:
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


def _par2_exe() -> str:
    w = shutil.which("par2")
    if w:
        return w
    local = Path.home() / ".local/bin/par2"
    if local.is_file() and os.access(local, os.X_OK):
        return str(local)
    raise SystemExit(
        "par2 binary not found in PATH or ~/.local/bin. Install par2cmdline (e.g. pacman -S par2cmdline)."
    )


def ensure_par2_available() -> str:
    return _par2_exe()


def build_parity(
    model_path: Path,
    parity_root: Path | None,
    redundancy_pct: int,
    min_size_bytes: int,
) -> None:
    par2_exe = ensure_par2_available()
    model_path = model_path.resolve()
    files = list(iter_target_files(model_path, min_size_bytes))
    if not files:
        print(f"No files above threshold under {model_path}")
        return

    if parity_root is None:
        parity_dir = model_path / ".parity"
    else:
        if model_path.is_absolute():
            rel = model_path.relative_to(model_path.anchor)
        else:
            rel = model_path
        parity_dir = parity_root / rel

    parity_dir.mkdir(parents=True, exist_ok=True)
    base_name = model_path.name
    parity_out = (parity_dir / base_name).resolve()
    rel_inputs = [str(p.resolve().relative_to(model_path)) for p in files]
    cmd: List[str] = [
        par2_exe,
        "c",
        f"-B{model_path}",
        f"-r{redundancy_pct}",
        str(parity_out),
        *rel_inputs,
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=str(model_path))


def verify_parity(model_path: Path, parity_root: Path | None) -> int:
    par2_exe = ensure_par2_available()
    if parity_root is None:
        parity_dir = model_path / ".parity"
    else:
        if model_path.is_absolute():
            rel = model_path.relative_to(model_path.anchor)
        else:
            rel = model_path
        parity_dir = parity_root / rel

    if not parity_dir.exists():
        print(f"No parity directory at {parity_dir}")
        return 1

    base_name = model_path.name
    main_par = parity_dir / f"{base_name}.par2"
    if not main_par.exists():
        print(f"No main parity file at {main_par}")
        return 1

    cmd = [par2_exe, "verify", str(main_par)]
    print(f"Running: {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=str(Path(model_path).resolve()))


def repair_from_parity(model_path: Path, parity_root: Path | None) -> int:
    par2_exe = ensure_par2_available()
    if parity_root is None:
        parity_dir = model_path / ".parity"
    else:
        if model_path.is_absolute():
            rel = model_path.relative_to(model_path.anchor)
        else:
            rel = model_path
        parity_dir = parity_root / rel

    if not parity_dir.exists():
        print(f"No parity directory at {parity_dir}")
        return 1

    base_name = model_path.name
    main_par = parity_dir / f"{base_name}.par2"
    if not main_par.exists():
        print(f"No main parity file at {main_par}")
        return 1

    cmd = [par2_exe, "repair", str(main_par)]
    print(f"Running: {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=str(Path(model_path).resolve()))


def cmd_create(args: argparse.Namespace) -> None:
    model_path = Path(args.model_path).resolve()
    parity_root = Path(args.parity_root).resolve() if args.parity_root else None
    min_size = args.min_size_mb * 1024 * 1024
    build_parity(
        model_path=model_path,
        parity_root=parity_root,
        redundancy_pct=args.redundancy_pct,
        min_size_bytes=min_size,
    )


def cmd_verify(args: argparse.Namespace) -> None:
    model_path = Path(args.model_path).resolve()
    parity_root = Path(args.parity_root).resolve() if args.parity_root else None
    rc = verify_parity(model_path, parity_root)
    raise SystemExit(rc)


def cmd_repair(args: argparse.Namespace) -> None:
    model_path = Path(args.model_path).resolve()
    parity_root = Path(args.parity_root).resolve() if args.parity_root else None
    rc = repair_from_parity(model_path, parity_root)
    raise SystemExit(rc)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PAR2 parity helper for model directories."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_create = sub.add_parser("create", help="Create PAR2 parity for a model directory.")
    p_create.add_argument(
        "model_path",
        help="Path to model directory or single file.",
    )
    p_create.add_argument(
        "--parity-root",
        help="Optional root directory under which parity trees are stored.",
    )
    p_create.add_argument(
        "--redundancy-pct",
        type=int,
        default=DEFAULT_REDUNDANCY_PCT,
        help=f"Redundancy percentage for par2 (default {DEFAULT_REDUNDANCY_PCT}).",
    )
    p_create.add_argument(
        "--min-size-mb",
        type=int,
        default=DEFAULT_MIN_SIZE_MB,
        help=f"Minimum file size in MiB to include (default {DEFAULT_MIN_SIZE_MB}).",
    )
    p_create.set_defaults(func=cmd_create)

    p_verify = sub.add_parser("verify", help="Verify an existing PAR2 set.")
    p_verify.add_argument(
        "model_path",
        help="Path to model directory or single file.",
    )
    p_verify.add_argument(
        "--parity-root",
        help="Optional root directory under which parity trees are stored.",
    )
    p_verify.set_defaults(func=cmd_verify)

    p_repair = sub.add_parser("repair", help="Repair using an existing PAR2 set.")
    p_repair.add_argument(
        "model_path",
        help="Path to model directory or single file.",
    )
    p_repair.add_argument(
        "--parity-root",
        help="Optional root directory under which parity trees are stored.",
    )
    p_repair.set_defaults(func=cmd_repair)

    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

