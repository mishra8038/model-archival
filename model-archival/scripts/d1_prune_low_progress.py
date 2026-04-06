#!/usr/bin/env python3
"""
Identify incomplete D1 registry models with **< threshold %** of HF-tracked bytes on disk
(same rules as ``evaluate_d1_incomplete.py``), optionally remove their trees from D1 and drop
entries from registry YAMLs + ``run_state.json``.

Default is **dry-run** (no deletes, no YAML edits). Use ``--apply`` after reviewing output.

On the archive VM::

  cd model-archiver
  export HF_TOKEN=$(tr -d '\n' < ~/.hf_token)
  uv run python scripts/d1_prune_low_progress.py
  uv run python scripts/d1_prune_low_progress.py --apply
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

# repo root: parent of scripts/
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_SRC = _REPO_ROOT / "src"
if _SRC.is_dir():
    sys.path.insert(0, str(_SRC))

from huggingface_hub import HfApi  # noqa: E402

from archiver.d1_disk_eval import (  # noqa: E402
    gather_d1_incomplete_rows,
    remove_models_from_yaml_registry,
    strip_models_from_run_state,
)
from archiver.models import load_registry  # noqa: E402


def _fmt_gib(n: int) -> str:
    return f"{n / (1024**3):.2f}"


def should_prune_row(
    row: dict,
    *,
    threshold_pct: float,
    treat_hf_errors_as_zero_progress: bool,
) -> bool:
    pct = row.get("progress_pct")
    if pct is not None:
        return float(pct) < threshold_pct
    if treat_hf_errors_as_zero_progress and row.get("error"):
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Prune D1 models below download progress threshold (dry-run unless --apply)"
    )
    ap.add_argument(
        "--registry",
        type=Path,
        default=_REPO_ROOT / "config" / "registry.yaml",
    )
    ap.add_argument(
        "--drives",
        type=Path,
        default=_REPO_ROOT / "config" / "drives.yaml",
    )
    ap.add_argument(
        "--narrow-registry",
        type=Path,
        default=_REPO_ROOT / "config" / "registry-d1-manifest-incomplete.yaml",
    )
    ap.add_argument(
        "--threshold-pct",
        type=float,
        default=60.0,
        help="Prune incomplete models with strictly less than this %% of HF bytes on disk (default 60)",
    )
    ap.add_argument(
        "--no-treat-hf-errors-as-prune",
        action="store_true",
        help="Do not auto-prune rows where HF resolve failed (no progress_pct)",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Delete d1 repo trees + .tmp slugs; edit registry YAMLs + run_state (see --apply-disk-only)",
    )
    ap.add_argument(
        "--apply-disk-only",
        action="store_true",
        help="With --apply, only delete trees under d1 (no registry / run_state changes)",
    )
    ap.add_argument(
        "--skip-run-state",
        action="store_true",
        help="With --apply, do not edit run_state.json",
    )
    ap.add_argument(
        "--out-md",
        type=Path,
        default=None,
        help="Write Markdown report path",
    )
    args = ap.parse_args()

    token = os.environ.get("HF_TOKEN")
    api = HfApi(token=token)
    narrow = args.narrow_registry if args.narrow_registry.is_file() else None

    d1, complete_n, incomplete_rows, _narrow_ids = gather_d1_incomplete_rows(
        registry_path=args.registry.resolve(),
        drives_path=args.drives.resolve(),
        narrow_registry_path=narrow.resolve() if narrow else None,
        api=api,
    )

    treat_err = not args.no_treat_hf_errors_as_prune
    prune_rows = [
        r
        for r in incomplete_rows
        if should_prune_row(
            r,
            threshold_pct=args.threshold_pct,
            treat_hf_errors_as_zero_progress=treat_err,
        )
    ]
    prune_ids = {r["id"] for r in prune_rows}

    lines: list[str] = [
        "# D1 prune candidates — below progress threshold",
        "",
        f"- Threshold: **<{args.threshold_pct}%** downloaded (HF file set, sidecar-complete = done)",
        f"- HF resolve errors treated as prune: **{treat_err}**",
        f"- D1 models manifest-complete (skipped): **{complete_n}**",
        f"- Incomplete rows: **{len(incomplete_rows)}**",
        f"- **Prune candidates: {len(prune_rows)}**",
        f"- Mode: **{'APPLY (destructive)' if args.apply else 'dry-run'}**",
        "",
        "## Candidates",
        "",
        "| Model | Progress % | Remaining GiB | HF total GiB | HF error (truncated) |",
        "|-------|-----------:|---------------:|-------------:|----------------------|",
    ]
    for r in sorted(prune_rows, key=lambda x: (x.get("progress_pct") is not None, x.get("progress_pct") or 0, x["id"])):
        pct = r.get("progress_pct")
        pct_s = f"{pct:.1f}" if pct is not None else "—"
        rem = r.get("remaining")
        tot = r.get("total_hf")
        rem_s = _fmt_gib(rem) if rem is not None else "—"
        tot_s = _fmt_gib(tot) if tot is not None else "—"
        err = (r.get("error") or "—").replace("|", "\\|")[:60]
        lines.append(f"| `{r['id']}` | {pct_s} | {rem_s} | {tot_s} | {err} |")

    lines += [
        "",
        "## Disk paths (``rm -rf`` targets)",
        "",
    ]
    for r in sorted(prune_rows, key=lambda x: x["id"]):
        lines.append(f"- `{r['repo_base']}`")
        lines.append(f"- `{r['tmp_subdir']}` (if present)")
    lines.append("")

    text = "\n".join(lines) + "\n"
    print(text, end="")

    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        tmp = args.out_md.with_suffix(args.out_md.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(args.out_md)
        print(f"Wrote {args.out_md}", file=sys.stderr)

    if not args.apply:
        print(
            "\nDry-run only. Re-run with --apply (or --apply --apply-disk-only) after review.\n",
            file=sys.stderr,
        )
        return 0

    if args.apply_disk_only and not args.apply:
        print("error: --apply-disk-only requires --apply", file=sys.stderr)
        return 2

    # --apply
    for r in prune_rows:
        rb = Path(r["repo_base"])
        ts = Path(r["tmp_subdir"])
        if rb.is_dir():
            shutil.rmtree(rb)
            print(f"removed tree {rb}", file=sys.stderr)
        if ts.is_dir():
            shutil.rmtree(ts)
            print(f"removed tmp {ts}", file=sys.stderr)

    if args.apply_disk_only:
        print(
            "\n--apply-disk-only: left registry.yaml / narrow / run_state unchanged.\n",
            file=sys.stderr,
        )
        return 0

    reg_paths = [
        args.registry.resolve(),
        args.narrow_registry.resolve(),
    ]
    for rp in reg_paths:
        if not rp.is_file():
            continue
        before, after = remove_models_from_yaml_registry(rp, prune_ids)
        print(
            f"registry {rp}: models {before} -> {after} (see .bak if changed)",
            file=sys.stderr,
        )

    if not args.skip_run_state:
        reg = load_registry(args.registry.resolve(), args.drives.resolve())
        d3 = reg.drives.get("d3")
        if d3:
            st = d3.mount_point / "run_state.json"
            if strip_models_from_run_state(st, prune_ids):
                print(f"stripped ids from {st}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
