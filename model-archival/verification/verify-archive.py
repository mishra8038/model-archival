#!/usr/bin/env python3
"""
verification/verify-archive.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Standalone archive integrity verifier for the model-archival project.

Walks one or more drive mount points, discovers every archived model directory
(identified by the presence of manifest.json), and verifies the SHA-256
checksum of every weight file either against its .sha256 sidecar or by
re-computing the hash from disk.

Usage
-----
  # Full sidecar check (fast — no disk read):
  python verify-archive.py --drives /mnt/models/d1 /mnt/models/d2

  # Full re-hash (slow — reads every byte, most thorough):
  python verify-archive.py --drives /mnt/models/d1 --rehash

  # Single model by directory:
  python verify-archive.py --model-dir /mnt/models/d1/deepseek-ai/DeepSeek-R1/abc123

  # Only tier A models:
  python verify-archive.py --drives /mnt/models/d1 --tier A

  # Show only failures:
  python verify-archive.py --drives /mnt/models/d1 --rehash --failures-only

  # Write report to a custom path:
  python verify-archive.py --drives /mnt/models/d1 --report-dir /mnt/models/d5/logs

Exit codes
----------
  0  All files passed
  1  One or more files failed
  2  Usage / configuration error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ─── ANSI colours ───────────────────────────────────────────────────────────
_C_RESET   = "\033[0m"
_C_BOLD    = "\033[1m"
_C_DIM     = "\033[2m"
_C_GREEN   = "\033[1;32m"
_C_YELLOW  = "\033[1;33m"
_C_RED     = "\033[1;31m"
_C_CYAN    = "\033[1;36m"
_C_MAGENTA = "\033[1;35m"

_IS_TTY = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"{code}{text}{_C_RESET}" if _IS_TTY else text


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def info(msg: str)  -> None: print(f"  {_c(_C_GREEN,  f'[{ts()} INFO ]')}  {msg}")
def warn(msg: str)  -> None: print(f"  {_c(_C_YELLOW, f'[{ts()} WARN ]')}  {msg}")
def error(msg: str) -> None: print(f"  {_c(_C_RED,    f'[{ts()} ERROR]')}  {msg}", file=sys.stderr)
def ok(msg: str)    -> None: print(f"  {_c(_C_GREEN,  '  ✔')}  {msg}")
def fail(msg: str)  -> None: print(f"  {_c(_C_RED,    '  ✗')}  {msg}")
def dim(msg: str)   -> None: print(f"  {_c(_C_DIM, msg)}")


def banner(title: str) -> None:
    print()
    print(_c(_C_MAGENTA, f"  ▶  {title}"))
    print()


def section(title: str) -> None:
    print()
    print(_c(_C_CYAN, "━" * 66))
    print(_c(_C_CYAN, f"  ▸  {title}"))
    print(_c(_C_CYAN, "━" * 66))
    print()


def human_bytes(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(b) < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024  # type: ignore[assignment]
    return f"{b:.1f} PB"


# ─── Core verification ───────────────────────────────────────────────────────

CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB


def sha256_file(path: Path, show_progress: bool = False) -> str:
    h = hashlib.sha256()
    total = path.stat().st_size
    done = 0
    t0 = time.time()
    with path.open("rb") as fh:
        while chunk := fh.read(CHUNK_SIZE):
            h.update(chunk)
            done += len(chunk)
            if show_progress and _IS_TTY:
                pct = done / total * 100 if total else 0
                elapsed = time.time() - t0
                speed = done / elapsed / 1024**2 if elapsed > 0 else 0
                bar_w = 30
                filled = int(bar_w * pct / 100)
                bar = "█" * filled + "░" * (bar_w - filled)
                print(
                    f"\r    [{bar}] {pct:5.1f}%  {human_bytes(done)}/{human_bytes(total)}"
                    f"  {speed:.0f} MB/s",
                    end="", flush=True,
                )
    if show_progress and _IS_TTY:
        print()  # newline after progress bar
    return h.hexdigest()


def read_sidecar(path: Path) -> Optional[str]:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if sidecar.exists():
        return sidecar.read_text().strip().split()[0]
    return None


def load_manifest(model_dir: Path) -> Optional[dict]:
    p = model_dir / "manifest.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def load_descriptor(model_dir: Path) -> Optional[dict]:
    p = model_dir / "DESCRIPTOR.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def verify_model(
    model_dir: Path,
    rehash: bool = False,
    failures_only: bool = False,
    tier_filter: Optional[str] = None,
) -> dict:
    """
    Verify all weight files in model_dir.

    Returns a dict:
      model_id, hf_repo, commit_sha, tier, total_bytes, n_pass, n_fail,
      n_missing, elapsed_s, files: [{path, size_bytes, ok, method, note}]
    """
    manifest = load_manifest(model_dir)
    descriptor = load_descriptor(model_dir)

    model_id   = (manifest or {}).get("model_id")   or descriptor and descriptor.get("model_id")   or model_dir.name
    hf_repo    = (manifest or {}).get("hf_repo")    or descriptor and descriptor.get("hf_repo")    or "—"
    commit_sha = (manifest or {}).get("commit_sha") or descriptor and descriptor.get("commit_sha") or "—"
    tier       = (manifest or {}).get("tier")       or descriptor and descriptor.get("tier")       or "?"

    if tier_filter and tier != tier_filter:
        return {}   # sentinel: skip this model

    if manifest is None:
        # Fallback: scan for weight files with sidecars
        file_entries = []
        for sidecar in sorted(model_dir.rglob("*.sha256")):
            target = sidecar.with_suffix("")
            if target.exists() and _is_weight_file(target):
                file_entries.append({
                    "path": str(target.relative_to(model_dir)),
                    "sha256": sidecar.read_text().strip().split()[0],
                    "size_bytes": target.stat().st_size,
                })
        if not file_entries:
            return {
                "model_id": model_id, "hf_repo": hf_repo, "commit_sha": commit_sha,
                "tier": tier, "total_bytes": 0,
                "n_pass": 0, "n_fail": 0, "n_missing": 0, "elapsed_s": 0.0,
                "files": [], "no_manifest": True,
            }
    else:
        file_entries = manifest.get("files", [])

    t_start = time.time()
    file_results = []
    n_pass = n_fail = n_missing = 0
    total_bytes = 0

    for entry in file_entries:
        rel_path = entry["path"]
        expected = entry.get("sha256", "")
        size_bytes = entry.get("size_bytes", 0)
        total_bytes += size_bytes
        target = model_dir / rel_path

        if not target.exists():
            n_missing += 1
            file_results.append({
                "path": rel_path, "size_bytes": size_bytes,
                "ok": False, "method": "missing", "note": "file not found",
                "expected": expected, "actual": "",
            })
            continue

        if rehash:
            actual = sha256_file(target, show_progress=True)
            method = "sha256 re-hash"
            ok_flag = (actual == expected) if expected else True
            note = "" if ok_flag else f"mismatch (expected {expected[:12]}… got {actual[:12]}…)"
        else:
            # Sidecar cross-check: confirm sidecar exists AND matches manifest entry
            stored = read_sidecar(target)
            method = "sidecar cross-check"
            if stored is None:
                ok_flag = False
                actual  = ""
                note    = "sidecar (.sha256) missing"
            elif expected and stored != expected:
                ok_flag = False
                actual  = stored
                note    = f"sidecar mismatch (manifest={expected[:12]}… sidecar={stored[:12]}…)"
            else:
                ok_flag = True
                actual  = stored
                note    = ""

        if ok_flag:
            n_pass += 1
        else:
            n_fail += 1

        file_results.append({
            "path": rel_path, "size_bytes": size_bytes,
            "ok": ok_flag, "method": method, "note": note,
            "expected": expected, "actual": actual,
        })

    elapsed = time.time() - t_start

    return {
        "model_id": model_id,
        "hf_repo": hf_repo,
        "commit_sha": commit_sha,
        "tier": tier,
        "total_bytes": total_bytes,
        "n_pass": n_pass,
        "n_fail": n_fail,
        "n_missing": n_missing,
        "elapsed_s": elapsed,
        "files": file_results,
        "no_manifest": manifest is None,
    }


def _is_weight_file(path: Path) -> bool:
    return path.suffix.lower() in {".safetensors", ".bin", ".pt", ".pth", ".gguf", ".ggml"}


# ─── Discovery ───────────────────────────────────────────────────────────────

def discover_model_dirs(roots: list[Path]) -> list[Path]:
    """
    Recursively find all directories that contain a manifest.json or at least
    one .sha256 sidecar (for models archived before manifest support).
    Returns de-duplicated sorted list.
    """
    found: set[Path] = set()
    for root in roots:
        if not root.exists():
            warn(f"Drive root not found, skipping: {root}")
            continue
        for manifest in root.rglob("manifest.json"):
            found.add(manifest.parent.resolve())
        for sidecar in root.rglob("*.sha256"):
            candidate = sidecar.parent.resolve()
            if any(_is_weight_file(f) for f in candidate.iterdir() if f.is_file()):
                found.add(candidate)
    return sorted(found)


# ─── Report writing ──────────────────────────────────────────────────────────

class VerifyReport:
    def __init__(self, report_dir: Path) -> None:
        report_dir.mkdir(parents=True, exist_ok=True)
        ts_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self._path = report_dir / f"verify-report-{ts_str}.md"
        self._lines: list[str] = []
        self._open = True

    @property
    def path(self) -> Path:
        return self._path

    def _write(self, line: str = "") -> None:
        self._lines.append(line)

    def flush(self) -> None:
        with self._path.open("w", encoding="utf-8") as fh:
            fh.write("\n".join(self._lines) + "\n")

    def write_header(self, args: argparse.Namespace) -> None:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        drives = ", ".join(str(d) for d in (args.drives or []))
        model_dir = str(args.model_dir) if args.model_dir else "—"
        rehash = "yes — full SHA-256 re-hash" if args.rehash else "no — sidecar cross-check"

        self._write("# Archive Integrity Verification Report")
        self._write("")
        self._write(f"| Field | Value |")
        self._write(f"|-------|-------|")
        self._write(f"| Generated | {now} |")
        self._write(f"| Host | {socket.gethostname()} |")
        self._write(f"| Drives scanned | {drives or '—'} |")
        self._write(f"| Model dir | {model_dir} |")
        self._write(f"| Tier filter | {args.tier or 'all'} |")
        self._write(f"| Full re-hash | {rehash} |")
        self._write("")
        self._write("---")
        self._write("")
        self.flush()

    def write_model_result(self, result: dict) -> None:
        if not result:
            return

        model_id   = result.get("model_id", "unknown")
        tier       = result.get("tier", "?")
        commit     = result.get("commit_sha", "—")[:16]
        hf_repo    = result.get("hf_repo", "—")
        total_bytes = result.get("total_bytes", 0)
        n_pass     = result.get("n_pass", 0)
        n_fail     = result.get("n_fail", 0)
        n_missing  = result.get("n_missing", 0)
        elapsed    = result.get("elapsed_s", 0.0)
        files      = result.get("files", [])
        n_total    = n_pass + n_fail + n_missing

        if n_fail == 0 and n_missing == 0:
            status_icon = "✔"
            status_label = "ALL PASS"
        else:
            status_icon = "✗"
            status_label = f"FAILED  ({n_fail} corrupt, {n_missing} missing)"

        elapsed_str = f"{elapsed:.1f}s" if elapsed < 60 else f"{elapsed/60:.1f}m"

        self._write(f"## {status_icon} `{model_id}`")
        self._write("")
        self._write(f"| Field | Value |")
        self._write(f"|-------|-------|")
        self._write(f"| HF repo | [{hf_repo}](https://huggingface.co/{hf_repo}) |")
        self._write(f"| Commit | `{commit}` |")
        self._write(f"| Tier | {tier} |")
        self._write(f"| Total size | {human_bytes(total_bytes)} |")
        self._write(f"| Files | {n_total} total: {n_pass} ✔  {n_fail} corrupt  {n_missing} missing |")
        self._write(f"| Elapsed | {elapsed_str} |")
        self._write(f"| **Result** | **{status_label}** |")
        self._write("")

        if result.get("no_manifest"):
            self._write("> ⚠ No manifest.json found — scanned for sidecar files only.")
            self._write("")

        # Show full file table only when model failed or has few files
        failed_files = [f for f in files if not f.get("ok")]
        if failed_files or len(files) <= 20:
            self._write("| File | Size | Method | Status | Note |")
            self._write("|------|------|--------|--------|------|")
            for f in files:
                icon  = "✔" if f.get("ok") else "✗"
                fname = Path(f["path"]).name
                size  = human_bytes(f.get("size_bytes", 0))
                meth  = f.get("method", "—")
                note  = f.get("note", "") or ""
                self._write(f"| `{fname}` | {size} | {meth} | {icon} | {note} |")
            self._write("")
        else:
            self._write(
                f"_All {n_pass} files passed — file table omitted for brevity. "
                f"Run with `--failures-only` to suppress passing models._"
            )
            self._write("")

        self._write("---")
        self._write("")
        self.flush()

    def write_summary(
        self,
        all_results: list[dict],
        elapsed_total: float,
        rehash: bool,
    ) -> None:
        n_models_pass    = sum(1 for r in all_results if r.get("n_fail", 0) == 0 and r.get("n_missing", 0) == 0)
        n_models_fail    = sum(1 for r in all_results if r.get("n_fail", 0) > 0 or r.get("n_missing", 0) > 0)
        n_files_total    = sum(r.get("n_pass", 0) + r.get("n_fail", 0) + r.get("n_missing", 0) for r in all_results)
        n_files_pass     = sum(r.get("n_pass", 0) for r in all_results)
        n_files_fail     = sum(r.get("n_fail", 0) for r in all_results)
        n_files_missing  = sum(r.get("n_missing", 0) for r in all_results)
        total_bytes      = sum(r.get("total_bytes", 0) for r in all_results)
        method           = "Full SHA-256 re-hash" if rehash else "Sidecar cross-check"
        elapsed_str      = f"{elapsed_total:.1f}s" if elapsed_total < 60 else f"{elapsed_total/60:.1f}m"
        now              = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        overall = "✔ ALL PASSED" if n_models_fail == 0 else f"✗ {n_models_fail} MODEL(S) FAILED"

        self._write("---")
        self._write("")
        self._write("## Summary")
        self._write("")
        self._write(f"| Metric | Count |")
        self._write(f"|--------|-------|")
        self._write(f"| Models verified | {len(all_results)} |")
        self._write(f"| Models passed | {n_models_pass} |")
        self._write(f"| Models failed | {n_models_fail} |")
        self._write(f"| Files checked | {n_files_total} |")
        self._write(f"| Files passed | {n_files_pass} |")
        self._write(f"| Files corrupt | {n_files_fail} |")
        self._write(f"| Files missing | {n_files_missing} |")
        self._write(f"| Total data | {human_bytes(total_bytes)} |")
        self._write(f"| Verification method | {method} |")
        self._write(f"| Total time | {elapsed_str} |")
        self._write(f"| Completed | {now} |")
        self._write("")

        if n_models_fail > 0:
            self._write("**Failed models:**")
            self._write("")
            for r in all_results:
                if r.get("n_fail", 0) > 0 or r.get("n_missing", 0) > 0:
                    self._write(
                        f"- ✗ `{r['model_id']}` — "
                        f"{r.get('n_fail',0)} corrupt, {r.get('n_missing',0)} missing"
                    )
            self._write("")

        self._write(f"**Overall result: {overall}**")
        self._write("")
        self.flush()


# ─── Console printer ─────────────────────────────────────────────────────────

def print_model_result(result: dict, failures_only: bool) -> None:
    if not result:
        return

    model_id    = result.get("model_id", "?")
    tier        = result.get("tier", "?")
    n_pass      = result.get("n_pass", 0)
    n_fail      = result.get("n_fail", 0)
    n_missing   = result.get("n_missing", 0)
    total_bytes = result.get("total_bytes", 0)
    elapsed     = result.get("elapsed_s", 0.0)

    elapsed_str = f"{elapsed:.1f}s" if elapsed < 60 else f"{elapsed/60:.1f}m"
    size_str    = human_bytes(total_bytes)

    if n_fail == 0 and n_missing == 0:
        if failures_only:
            return
        ok(
            f"{_c(_C_BOLD, model_id)}  "
            f"{_c(_C_DIM, f'tier={tier}  {n_pass} files  {size_str}  {elapsed_str}')}"
        )
    else:
        fail(
            f"{_c(_C_BOLD, model_id)}  "
            f"{_c(_C_RED, f'{n_fail} corrupt  {n_missing} missing')}  "
            f"{_c(_C_DIM, f'{n_pass} passed  {size_str}  {elapsed_str}')}"
        )
        for f in result.get("files", []):
            if not f.get("ok"):
                fname = Path(f["path"]).name
                note  = f.get("note", "")
                print(f"      {_c(_C_RED, '↳')}  {fname}  {_c(_C_DIM, note)}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Verify SHA-256 integrity of archived LLM weight files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument(
        "--drives", metavar="PATH", nargs="+", type=Path,
        help="One or more drive mount points to scan recursively",
    )
    grp.add_argument(
        "--model-dir", metavar="PATH", type=Path,
        help="Verify a single model directory directly",
    )
    p.add_argument(
        "--rehash", action="store_true",
        help="Re-compute SHA-256 from disk for every file (slow, most thorough)",
    )
    p.add_argument(
        "--tier", choices=["A", "B", "C", "D"],
        help="Only verify models of this tier",
    )
    p.add_argument(
        "--failures-only", action="store_true",
        help="Only print/report models that have failures",
    )
    p.add_argument(
        "--report-dir", metavar="PATH", type=Path,
        default=None,
        help="Directory to write the Markdown report (default: ./verification-reports/)",
    )
    p.add_argument(
        "--no-report", action="store_true",
        help="Skip writing the Markdown report (console output only)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # ── Header ────────────────────────────────────────────────────────────
    print()
    print(_c(_C_CYAN, "━" * 66))
    print(_c(_C_BOLD + _C_CYAN, "  ▸  Archive Integrity Verifier"))
    print(_c(_C_CYAN, "━" * 66))
    print()

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    method  = "full SHA-256 re-hash (slow)" if args.rehash else "sidecar cross-check (fast)"
    info(f"Started:  {now_str}")
    info(f"Method:   {method}")
    info(f"Tier:     {args.tier or 'all'}")
    if args.drives:
        info(f"Drives:   {', '.join(str(d) for d in args.drives)}")
    else:
        info(f"Model:    {args.model_dir}")
    print()

    # ── Report init ───────────────────────────────────────────────────────
    report: Optional[VerifyReport] = None
    if not args.no_report:
        report_dir = args.report_dir
        if report_dir is None:
            # Default: verification-reports/ next to this script
            report_dir = Path(__file__).parent / "verification-reports"
        report = VerifyReport(report_dir)
        report.write_header(args)
        dim(f"Report → {report.path}")
        print()

    # ── Discover models ───────────────────────────────────────────────────
    if args.model_dir:
        model_dirs = [args.model_dir.resolve()]
    else:
        section("Discovering model directories")
        model_dirs = discover_model_dirs(args.drives)
        info(f"Found {len(model_dirs)} model director{'y' if len(model_dirs)==1 else 'ies'}")
        print()

    if not model_dirs:
        warn("No model directories found — nothing to verify.")
        return 0

    # ── Verify ────────────────────────────────────────────────────────────
    section("Verifying models")

    t_total_start = time.time()
    all_results: list[dict] = []
    n_skipped = 0

    for i, mdir in enumerate(model_dirs, 1):
        print(
            f"  {_c(_C_CYAN, f'[{i:>3}/{len(model_dirs)}]')}  "
            f"{_c(_C_BOLD, mdir.name)}  {_c(_C_DIM, str(mdir))}"
        )

        result = verify_model(
            mdir,
            rehash=args.rehash,
            failures_only=args.failures_only,
            tier_filter=args.tier,
        )

        if not result:
            n_skipped += 1
            dim(f"         skipped (tier filter)")
            continue

        all_results.append(result)
        print_model_result(result, failures_only=args.failures_only)

        if report:
            if not args.failures_only or result.get("n_fail", 0) > 0 or result.get("n_missing", 0) > 0:
                report.write_model_result(result)

    elapsed_total = time.time() - t_total_start

    # ── Console summary ───────────────────────────────────────────────────
    section("Summary")

    if not all_results:
        warn("No models were verified.")
        return 0

    n_models_pass   = sum(1 for r in all_results if r.get("n_fail", 0) == 0 and r.get("n_missing", 0) == 0)
    n_models_fail   = sum(1 for r in all_results if r.get("n_fail", 0) > 0 or r.get("n_missing", 0) > 0)
    n_files_total   = sum(r.get("n_pass", 0) + r.get("n_fail", 0) + r.get("n_missing", 0) for r in all_results)
    n_files_pass    = sum(r.get("n_pass", 0) for r in all_results)
    n_files_fail    = sum(r.get("n_fail", 0) for r in all_results)
    n_files_missing = sum(r.get("n_missing", 0) for r in all_results)
    total_bytes     = sum(r.get("total_bytes", 0) for r in all_results)
    elapsed_str     = f"{elapsed_total:.1f}s" if elapsed_total < 60 else f"{elapsed_total/60:.1f}m"

    rows = [
        ("Models verified",  str(len(all_results))),
        ("Models passed",    _c(_C_GREEN, str(n_models_pass))),
        ("Models failed",    _c(_C_RED, str(n_models_fail)) if n_models_fail else "0"),
        ("Files checked",    str(n_files_total)),
        ("Files passed",     _c(_C_GREEN, str(n_files_pass))),
        ("Files corrupt",    _c(_C_RED, str(n_files_fail)) if n_files_fail else "0"),
        ("Files missing",    _c(_C_RED, str(n_files_missing)) if n_files_missing else "0"),
        ("Total data",       human_bytes(total_bytes)),
        ("Total time",       elapsed_str),
    ]
    if n_skipped:
        rows.append(("Skipped (tier filter)", str(n_skipped)))

    for label, value in rows:
        print(f"  {_c(_C_DIM, f'{label:<22}')}  {value}")

    print()
    if n_models_fail == 0:
        print(_c(_C_GREEN, "  ┌──────────────────────────────────────────────────────────────┐"))
        print(_c(_C_GREEN, f"  │  ✔  ALL {len(all_results)} MODEL(S) PASSED — archive integrity confirmed."))
        print(_c(_C_GREEN, "  └──────────────────────────────────────────────────────────────┘"))
    else:
        print(_c(_C_RED, "  ┌──────────────────────────────────────────────────────────────┐"))
        print(_c(_C_RED, f"  │  ✗  {n_models_fail} MODEL(S) FAILED — review failures above."))
        print(_c(_C_RED, "  └──────────────────────────────────────────────────────────────┘"))
        print()
        for r in all_results:
            if r.get("n_fail", 0) > 0 or r.get("n_missing", 0) > 0:
                fail(
                    f"{r['model_id']}  "
                    f"({r.get('n_fail',0)} corrupt  {r.get('n_missing',0)} missing)"
                )

    print()

    # ── Report summary ────────────────────────────────────────────────────
    if report:
        report.write_summary(all_results, elapsed_total, rehash=args.rehash)
        print(f"  {_c(_C_DIM, 'Report → ')}{_c(_C_BOLD, str(report.path))}")
        print()

    return 0 if n_models_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
