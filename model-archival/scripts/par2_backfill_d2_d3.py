#!/usr/bin/env python3
"""
Create PAR2 parity sets per model revision on D1/D2/D3 (optional D1), stopping when free
space is insufficient. Optionally run verification/verify-archive.py on each tree first.

Writes Markdown + JSON reports under model-archival/reports/.

Requires: par2 (par2cmdline) on PATH.

Examples (archive VM):
  # D2+D3 only (legacy default)
  python3 scripts/par2_backfill_d2_d3.py --dry-run

  # All three data drives + verify (sidecar check) then PAR2
  python3 scripts/par2_backfill_d2_d3.py --all-d123 --verify-before-par2

  # Same with full byte re-hash before PAR2 (very slow)
  python3 scripts/par2_backfill_d2_d3.py --all-d123 --verify-before-par2 --verify-rehash
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

HEX = set("0123456789abcdef")


def is_sha40(name: str) -> bool:
    n = name.lower()
    return len(n) == 40 and all(c in HEX for c in n)


def is_revision_name(name: str) -> bool:
    return name == "main" or is_sha40(name)


def drive_label(path: Path) -> str:
    s = str(path.resolve())
    if "/d1/" in s or s.rstrip("/").endswith("/d1"):
        return "d1"
    if "/d2/" in s or s.rstrip("/").endswith("/d2"):
        return "d2"
    if "/d3/" in s or s.rstrip("/").endswith("/d3"):
        return "d3"
    return "other"


def mount_for_path(path: Path, mounts: list[Path]) -> Path | None:
    try:
        rp = path.resolve()
    except OSError:
        return None
    for m in mounts:
        try:
            mr = m.resolve()
        except OSError:
            continue
        try:
            rp.relative_to(mr)
            return mr
        except ValueError:
            continue
    return None


def iter_weight_files(root: Path, min_bytes: int) -> Iterator[Path]:
    for dirpath, _dirnames, filenames in os.walk(root):
        if "/.parity/" in dirpath.replace("\\", "/") + "/":
            continue
        for name in filenames:
            if name.endswith(".aria2"):
                continue
            p = Path(dirpath) / name
            try:
                st = p.stat()
            except OSError:
                continue
            if st.st_size >= min_bytes:
                yield p


def payload_bytes_and_files(root: Path, min_bytes: int) -> tuple[int, list[Path]]:
    files = list(iter_weight_files(root, min_bytes))
    total = sum(p.stat().st_size for p in files)
    return total, files


def estimate_parity_need(payload_bytes: int, redundancy_pct: int, fudge: float) -> int:
    return int(payload_bytes * (redundancy_pct / 100.0) * fudge) + 64 * 1024 * 1024


def iter_standard_revisions(mount: Path, subs: tuple[str, ...]) -> Iterator[Path]:
    for sub in subs:
        base = mount / sub
        if not base.is_dir():
            continue
        try:
            orgs = list(base.iterdir())
        except OSError:
            continue
        for org in orgs:
            if not org.is_dir() or org.name.startswith("."):
                continue
            try:
                repos = list(org.iterdir())
            except OSError:
                continue
            for repo in repos:
                if not repo.is_dir():
                    continue
                try:
                    revs = list(repo.iterdir())
                except OSError:
                    continue
                for rev in revs:
                    if not rev.is_dir() or rev.is_symlink():
                        continue
                    if not is_revision_name(rev.name):
                        continue
                    yield rev


def iter_specialist_revisions(mount: Path) -> Iterator[Path]:
    spec = mount / "specialist"
    if not spec.is_dir():
        return
    for root, _dirs, files in os.walk(spec):
        if "manifest.json" not in files:
            continue
        p = Path(root)
        if not is_revision_name(p.name):
            continue
        yield p


def discover_revisions(mounts: list[Path]) -> list[Path]:
    subs = ("raw", "quantized", "uncensored")
    seen: set[Path] = set()
    out: list[Path] = []
    for mount in mounts:
        if not mount.is_dir():
            continue
        for rev in iter_standard_revisions(mount, subs):
            k = rev.resolve()
            if k in seen:
                continue
            seen.add(k)
            out.append(rev)
        for rev in iter_specialist_revisions(mount):
            k = rev.resolve()
            if k in seen:
                continue
            seen.add(k)
            out.append(rev)
    return out


def parity_main_file(rev_dir: Path) -> Path:
    return rev_dir / ".parity" / f"{rev_dir.name}.par2"


def find_par2() -> str | None:
    exe = shutil.which("par2")
    if exe:
        return exe
    local = Path.home() / ".local/bin/par2"
    if local.is_file() and os.access(local, os.X_OK):
        return str(local)
    return None


def run_verify(rev_dir: Path, verify_py: Path, *, rehash: bool) -> tuple[int, str]:
    cmd = [sys.executable, str(verify_py), "--model-dir", str(rev_dir.resolve())]
    if rehash:
        cmd.append("--rehash")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        tail = ((r.stderr or "") + (r.stdout or ""))[-2500:]
        return r.returncode, tail
    except OSError as e:
        return 127, str(e)


def run_par2_create(
    rev_dir: Path,
    files: list[Path],
    redundancy_pct: int,
    par2_exe: str,
) -> tuple[int, str]:
    if not files:
        return 1, "no files"
    rev_dir = rev_dir.resolve()
    parity_dir = rev_dir / ".parity"
    parity_dir.mkdir(parents=True, exist_ok=True)
    rel_parts: list[str] = []
    for p in files:
        pr = p.resolve()
        try:
            rel_parts.append(str(pr.relative_to(rev_dir)))
        except ValueError:
            return 1, f"file outside rev_dir: {p}"
    base_rel = f".parity/{rev_dir.name}"
    cmd = [
        par2_exe,
        "c",
        f"-B{rev_dir}",
        f"-r{redundancy_pct}",
        base_rel,
        *rel_parts,
    ]
    try:
        r = subprocess.run(
            cmd,
            cwd=str(rev_dir),
            check=False,
            capture_output=True,
            text=True,
            timeout=86400,
        )
        err = (r.stderr or "") + (r.stdout or "")
        if r.returncode != 0:
            return r.returncode, err[-4000:] if err else "par2 failed"
        return 0, ""
    except OSError as e:
        return 1, str(e)


@dataclass
class Row:
    path: str
    drive: str
    revision: str
    payload_bytes: int
    n_files: int
    status: str
    parity_bytes: int = 0
    estimate_bytes: int = 0
    free_before: int = 0
    free_after: int = 0
    detail: str = ""
    verify_rc: int | None = None


@dataclass
class RunReport:
    started_utc: str
    mounts: list[str]
    d1_root: str | None
    d2_root: str
    d3_root: str
    redundancy_pct: int
    min_size_mb: int
    reserve_bytes: int
    fudge: float
    dry_run: bool
    verify_before_par2: bool
    verify_rehash: bool
    rows: list[dict] = field(default_factory=list)
    abandoned_d1: bool = False
    abandoned_d2: bool = False
    abandoned_d3: bool = False
    notes: list[str] = field(default_factory=list)


def format_gib(b: int) -> str:
    return f"{b / (1024**3):.2f}"


def write_markdown(path: Path, rep: RunReport, created: list[Row], title: str) -> None:
    from collections import Counter

    lines = [
        f"# {title} — {rep.started_utc}",
        "",
        f"- **Mounts scanned:** {', '.join(f'`{m}`' for m in rep.mounts)}",
        f"- **D1 root:** `{rep.d1_root or '—'}`",
        f"- **D2 root:** `{rep.d2_root}`",
        f"- **D3 root:** `{rep.d3_root}`",
        f"- **Verify before PAR2:** {rep.verify_before_par2}"
        + (" (full `--rehash`)" if rep.verify_rehash else " (sidecar / manifest)"),
        f"- **Redundancy:** {rep.redundancy_pct}%",
        f"- **Min file size:** {rep.min_size_mb} MiB",
        f"- **Reserve (per drive):** {format_gib(rep.reserve_bytes)} GiB",
        f"- **Estimate fudge:** {rep.fudge}",
        f"- **Dry run:** {rep.dry_run}",
        f"- **Abandoned (insufficient space / par2 error):** d1={rep.abandoned_d1} d2={rep.abandoned_d2} d3={rep.abandoned_d3}",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|--------|------:|",
    ]
    c = Counter(r["status"] for r in rep.rows)
    for k, v in sorted(c.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| {k} | {v} |")
    lines.extend(["", "## PAR2 created (redundancy on disk)", ""])
    if not created:
        lines.append("*None.*")
    else:
        lines.append("| Path | Drive | Payload (GiB) | Parity dir (approx GiB) |")
        lines.append("|------|-------|----------------:|--------------------------:|")
        for r in created:
            lines.append(
                f"| `{r.path}` | {r.drive} | {format_gib(r.payload_bytes)} | "
                f"{format_gib(r.parity_bytes)} |"
            )
    lines.extend(["", "## All rows", ""])
    lines.append("| Status | Drive | Verify rc | Payload GiB | Path | Detail |")
    lines.append("|--------|------:|----------:|-------------:|------|--------|")
    for r in rep.rows:
        p = r if isinstance(r, dict) else asdict(r)
        vrc = p.get("verify_rc")
        vrs = "—" if vrc is None else str(vrc)
        lines.append(
            f"| {p['status']} | {p['drive']} | {vrs} | {format_gib(p['payload_bytes'])} | "
            f"`{p['path']}` | {p.get('detail', '')[:100]} |"
        )
    if rep.notes:
        lines.extend(["", "## Notes", ""])
        for n in rep.notes:
            lines.append(f"- {n}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="PAR2 backfill per revision on D1/D2/D3 (D1 optional)."
    )
    ap.add_argument("--d1", type=Path, default=None, help="D1 root (enables D1 scan).")
    ap.add_argument(
        "--all-d123",
        action="store_true",
        help="Scan /mnt/models/d1 plus default D2/D3 (same as --d1 /mnt/models/d1).",
    )
    ap.add_argument("--d2", type=Path, default=Path("/mnt/models/d2"))
    ap.add_argument("--d3", type=Path, default=Path("/mnt/models/d3"))
    ap.add_argument("--redundancy-pct", type=int, default=5, help="par2 -r (default 5)")
    ap.add_argument("--min-size-mb", type=int, default=32)
    ap.add_argument(
        "--reserve-gib",
        type=float,
        default=2.0,
        help="Minimum free space to leave on each drive (GiB binary).",
    )
    ap.add_argument("--fudge", type=float, default=1.2)
    ap.add_argument(
        "--sort",
        choices=("smallest-first", "largest-first"),
        default="smallest-first",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--verify-before-par2",
        action="store_true",
        help="Run verification/verify-archive.py on each revision before par2 (skipped in --dry-run).",
    )
    ap.add_argument(
        "--verify-rehash",
        action="store_true",
        help="With --verify-before-par2, pass --rehash to verify-archive.py (reads every byte).",
    )
    ap.add_argument("--report-dir", type=Path, default=None)
    ap.add_argument("--max-models", type=int, default=0, help="0 = no limit")
    args = ap.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    verify_py = repo_root / "verification" / "verify-archive.py"
    report_dir = args.report_dir or (script_dir.parent / "reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    d1_path: Path | None = None
    if args.all_d123:
        d1_path = Path("/mnt/models/d1")
    if args.d1 is not None:
        d1_path = args.d1

    mounts: list[Path] = []
    if d1_path is not None:
        mounts.append(d1_path)
    mounts.extend([args.d2, args.d3])
    mounts = [m for m in mounts if m.is_dir()]

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    has_d1 = d1_path is not None and d1_path.is_dir()
    stem = f"PAR2-D1-D2-D3-RUN-{ts}" if has_d1 else f"PAR2-D2-D3-RUN-{ts}"
    title = "PAR2 backfill D1+D2+D3" if has_d1 else "PAR2 backfill D2/D3"

    par2_exe = find_par2()
    if par2_exe is None and not args.dry_run:
        print(
            "ERROR: par2 not found (install par2cmdline or set PATH to include ~/.local/bin).",
            file=sys.stderr,
        )
        return 127

    if args.verify_before_par2 and not args.dry_run and not verify_py.is_file():
        print(f"ERROR: verify script missing: {verify_py}", file=sys.stderr)
        return 2

    min_bytes = args.min_size_mb * 1024 * 1024
    reserve = int(args.reserve_gib * (1024**3))

    revs = discover_revisions(mounts)
    scored: list[tuple[int, Path]] = []
    for rev in revs:
        pb, _fl = payload_bytes_and_files(rev, min_bytes)
        if pb == 0:
            continue
        scored.append((pb, rev))
    scored.sort(key=lambda x: x[0], reverse=(args.sort == "largest-first"))

    rep = RunReport(
        started_utc=ts,
        mounts=[str(m) for m in mounts],
        d1_root=str(d1_path) if d1_path and d1_path.is_dir() else None,
        d2_root=str(args.d2),
        d3_root=str(args.d3),
        redundancy_pct=args.redundancy_pct,
        min_size_mb=args.min_size_mb,
        reserve_bytes=reserve,
        fudge=args.fudge,
        dry_run=args.dry_run,
        verify_before_par2=args.verify_before_par2,
        verify_rehash=args.verify_rehash,
    )

    abandoned = {"d1": False, "d2": False, "d3": False}
    created_rows: list[Row] = []
    done = 0

    for payload_bytes, rev in scored:
        if args.max_models and done >= args.max_models:
            rep.notes.append(f"Stopped after --max-models={args.max_models}")
            break

        mount = mount_for_path(rev, mounts)
        drv = drive_label(rev)
        if mount is None or drv not in ("d1", "d2", "d3"):
            row = Row(
                path=str(rev),
                drive=drv,
                revision=rev.name,
                payload_bytes=payload_bytes,
                n_files=0,
                status="skipped_unknown_mount",
            )
            rep.rows.append(asdict(row))
            continue

        if abandoned[drv]:
            row = Row(
                path=str(rev),
                drive=drv,
                revision=rev.name,
                payload_bytes=payload_bytes,
                n_files=0,
                status="skipped_drive_abandoned",
            )
            rep.rows.append(asdict(row))
            continue

        free = shutil.disk_usage(mount).free
        est = estimate_parity_need(payload_bytes, args.redundancy_pct, args.fudge)
        if parity_main_file(rev).exists():
            pdir = rev / ".parity"
            try:
                pbytes = sum(f.stat().st_size for f in pdir.rglob("*") if f.is_file())
            except OSError:
                pbytes = 0
            row = Row(
                path=str(rev),
                drive=drv,
                revision=rev.name,
                payload_bytes=payload_bytes,
                n_files=0,
                status="skipped_already_has_par2",
                parity_bytes=pbytes,
                estimate_bytes=est,
                free_before=free,
            )
            rep.rows.append(asdict(row))
            continue

        if free < est + reserve:
            row = Row(
                path=str(rev),
                drive=drv,
                revision=rev.name,
                payload_bytes=payload_bytes,
                n_files=0,
                status="skipped_insufficient_space",
                estimate_bytes=est,
                free_before=free,
                detail=f"need~{est}+reserve",
            )
            rep.rows.append(asdict(row))
            continue

        _pb, files = payload_bytes_and_files(rev, min_bytes)
        n_files = len(files)
        verify_rc: int | None = None

        if args.dry_run:
            drun_detail = ""
            if args.verify_before_par2:
                drun_detail = "Would run verify-archive.py then par2."
            row = Row(
                path=str(rev),
                drive=drv,
                revision=rev.name,
                payload_bytes=payload_bytes,
                n_files=n_files,
                status="dry_run_would_create",
                estimate_bytes=est,
                free_before=free,
                detail=drun_detail,
            )
            rep.rows.append(asdict(row))
            done += 1
            continue

        if args.verify_before_par2:
            print(f"Verify: {drv} {rev} ({n_files} files)", flush=True)
            verify_rc, vtail = run_verify(rev, verify_py, rehash=args.verify_rehash)
            if verify_rc != 0:
                row = Row(
                    path=str(rev),
                    drive=drv,
                    revision=rev.name,
                    payload_bytes=payload_bytes,
                    n_files=n_files,
                    status="verify_failed_skipped_par2",
                    verify_rc=verify_rc,
                    estimate_bytes=est,
                    free_before=free,
                    detail=vtail[:500],
                )
                rep.rows.append(asdict(row))
                continue

        free_before = shutil.disk_usage(mount).free
        assert par2_exe is not None
        print(
            f"PAR2 create: {drv} {rev} ({n_files} files, ~{format_gib(payload_bytes)} GiB)",
            flush=True,
        )
        rc, detail = run_par2_create(rev, files, args.redundancy_pct, par2_exe)
        free_after = shutil.disk_usage(mount).free

        if rc != 0:
            try:
                shutil.rmtree(rev / ".parity", ignore_errors=True)
            except OSError:
                pass
            row = Row(
                path=str(rev),
                drive=drv,
                revision=rev.name,
                payload_bytes=payload_bytes,
                n_files=n_files,
                status="error_par2_failed",
                verify_rc=verify_rc,
                estimate_bytes=est,
                free_before=free_before,
                free_after=free_after,
                detail=detail[:500],
            )
            rep.rows.append(asdict(row))
            rep.notes.append(f"Drive {drv}: par2 failed `{rev}` rc={rc}; abandoning {drv}.")
            abandoned[drv] = True
            continue

        pdir = rev / ".parity"
        try:
            parity_bytes = sum(f.stat().st_size for f in pdir.rglob("*") if f.is_file())
        except OSError:
            parity_bytes = 0

        row = Row(
            path=str(rev),
            drive=drv,
            revision=rev.name,
            payload_bytes=payload_bytes,
            n_files=n_files,
            status="created",
            verify_rc=verify_rc,
            parity_bytes=parity_bytes,
            estimate_bytes=est,
            free_before=free_before,
            free_after=free_after,
        )
        rep.rows.append(asdict(row))
        created_rows.append(row)
        done += 1

        if free_after < reserve:
            rep.notes.append(
                f"Drive {drv}: free {free_after} < reserve {reserve} after `{rev}`; abandoning {drv}."
            )
            abandoned[drv] = True

    rep.abandoned_d1 = abandoned["d1"]
    rep.abandoned_d2 = abandoned["d2"]
    rep.abandoned_d3 = abandoned["d3"]

    json_path = report_dir / f"{stem}.json"
    md_path = report_dir / f"{stem}.md"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(asdict(rep), f, indent=2)

    write_markdown(md_path, rep, created_rows, title)
    print(f"Wrote {md_path}", flush=True)
    print(f"Wrote {json_path}", flush=True)

    latest_md = report_dir / "PAR2-BACKFILL-LATEST.md"
    latest_md.write_text(
        f"# PAR2 backfill — latest run\n\n"
        f"- **UTC:** {ts}\n"
        f"- **Markdown:** [{md_path.name}]({md_path.name})\n"
        f"- **JSON:** [{json_path.name}]({json_path.name})\n",
        encoding="utf-8",
    )

    errs = sum(
        1
        for r in rep.rows
        if r["status"] in ("error_par2_failed", "verify_failed_skipped_par2")
    )
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
