#!/usr/bin/env python3
"""
Evaluate registry models assigned to D1: manifest completeness, narrow-registry coverage,
and approximate remaining HF download bytes (same file/sidecar rules as the downloader).

Run on the archive host where ``/mnt/models/d1`` is mounted::

  cd model-archival
  export HF_TOKEN=$(tr -d '\n' < ~/.hf_token)   # recommended for gated repos
  uv run python scripts/evaluate_d1_incomplete.py

Optional::

  uv run python scripts/evaluate_d1_incomplete.py --out-md reports/D1-INCOMPLETE-EVAL.md
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

# repo root: model-archival/ (parent of scripts/)
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_SRC = _REPO_ROOT / "src"
if _SRC.is_dir():
    sys.path.insert(0, str(_SRC))

from huggingface_hub import HfApi  # noqa: E402

from archiver.d1_disk_eval import gather_d1_incomplete_rows  # noqa: E402


def _fmt_gib(n: int) -> str:
    return f"{n / (1024**3):.2f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="D1 registry models: incomplete + download estimate")
    ap.add_argument(
        "--registry",
        type=Path,
        default=_REPO_ROOT / "config" / "registry.yaml",
        help="Main registry (drive: d1 rows are evaluated)",
    )
    ap.add_argument(
        "--drives",
        type=Path,
        default=_REPO_ROOT / "config" / "drives.yaml",
        help="drives.yaml",
    )
    ap.add_argument(
        "--narrow-registry",
        type=Path,
        default=_REPO_ROOT / "config" / "registry-d1-manifest-incomplete.yaml",
        help="Focused run list (ids that the narrow archiver run would queue)",
    )
    ap.add_argument(
        "--out-md",
        type=Path,
        default=None,
        help="Write the same report to this path (atomic .tmp + replace)",
    )
    args = ap.parse_args()

    try:
        token = os.environ.get("HF_TOKEN")
        api = HfApi(token=token)
        narrow_path = args.narrow_registry.resolve() if args.narrow_registry.is_file() else None
        if not args.narrow_registry.is_file():
            print(f"warning: narrow registry missing: {args.narrow_registry}", file=sys.stderr)

        d1, complete_n, incomplete_rows, narrow_ids = gather_d1_incomplete_rows(
            registry_path=args.registry.resolve(),
            drives_path=args.drives.resolve(),
            narrow_registry_path=narrow_path,
            api=api,
        )
    except (ValueError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    d1_models = [m for m in load_registry_yaml_d1_ids(args.registry.resolve())]
    # recount for summary table
    d1_id_count = len(d1_models)
    d1_ids = set(d1_models)
    narrow_orphan = sorted(narrow_ids - d1_ids)

    lines: list[str] = []
    lines += [
        "# D1 evaluation — registry `drive: d1` models",
        "",
        f"- Main registry: `{args.registry}`",
        f"- D1 mount: `{d1.mount_point}`",
        f"- Narrow list: `{args.narrow_registry}` ({len(narrow_ids)} ids)",
        f"- HF_TOKEN: {'set' if token else '**not set** (gated repos may fail to resolve)'}",
        "",
        "## Summary",
        "",
    ]

    in_narrow_incomplete = [r for r in incomplete_rows if r["in_narrow"] and r["remaining"] is not None]
    not_narrow_incomplete = [r for r in incomplete_rows if not r["in_narrow"] and r["remaining"] is not None]
    narrow_rem = sum(r["remaining"] or 0 for r in in_narrow_incomplete)
    other_rem = sum(r["remaining"] or 0 for r in not_narrow_incomplete)
    errors = [r for r in incomplete_rows if r["error"]]
    narrow_with_error = [r for r in incomplete_rows if r["in_narrow"] and r["error"]]
    # unique ids for "<60% or HF error" line (aligns with d1_prune_low_progress defaults)
    low_progress_ids = {
        r["id"]
        for r in incomplete_rows
        if (r.get("progress_pct") is not None and r["progress_pct"] < 60.0)
        or (r.get("error") is not None)
    }

    lines += [
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| D1 models in main registry | {d1_id_count} |",
        f"| Manifest-complete on D1 (any revision dir) | {complete_n} |",
        f"| Incomplete (no complete manifest) | {len(incomplete_rows)} |",
        f"| Incomplete + in narrow + **HF estimate OK** | {len(in_narrow_incomplete)} |",
        f"| Incomplete + in narrow + **HF resolve error** | {len(narrow_with_error)} |",
        f"| Incomplete + **not** in narrow + estimate OK | {len(not_narrow_incomplete)} |",
        f"| Approx. remaining download (narrow ∩ incomplete, estimated rows) | {_fmt_gib(narrow_rem)} GiB |",
        f"| Approx. remaining download (incomplete **not** in narrow) | {_fmt_gib(other_rem)} GiB |",
        f"| Rows with HF resolve errors (any) | {len(errors)} |",
        f"| **Prune hint:** `<60%` downloaded **or** HF error (see ``d1_prune_low_progress.py``) | **{len(low_progress_ids)}** ids |",
        "",
        "**Narrow run coverage:** Models in the narrow file that are already manifest-complete are "
        "not listed below; the archiver will skip them quickly. Rows with **HF resolve error** are "
        "still incomplete on disk but need token/access or repo fix before any bytes move.",
        "",
        "**Interpretation:** The narrow archiver run (`-r registry-d1-manifest-incomplete.yaml`) will "
        "only process models **listed in that file**. Incomplete D1 models **not** in the narrow list "
        "stay unfinished until you add them or run the full registry.",
        "",
        "Estimates use HF file sizes minus bytes found under the revision dir, any sibling revision, "
        "and `d1/.tmp/<slug>/`. XET partials in the HF hub cache are not counted — a few repos may "
        "download less than shown.",
        "",
    ]

    if narrow_orphan:
        lines += [
            "## Narrow registry ids **not** `drive: d1` in main registry",
            "",
            "These will **not** be in the D1 evaluation table (narrow list is wider than D1 or stale):",
            "",
        ]
        for x in narrow_orphan[:80]:
            lines.append(f"- `{x}`")
        if len(narrow_orphan) > 80:
            lines.append(f"- … +{len(narrow_orphan) - 80} more")
        lines.append("")

    lines += [
        "## Incomplete models (detail)",
        "",
        "| Model | Tier | Narrow? | Progress % | Remaining (GiB) | HF total (GiB) | Sidecar-done | Commit | Error |",
        "|-------|------|---------|-------------:|-----------------:|---------------:|-------------:|--------|-------|",
    ]

    for r in sorted(incomplete_rows, key=lambda x: (-(x["remaining"] or 0), x["id"])):
        rem_s = _fmt_gib(r["remaining"]) if r["remaining"] is not None else "—"
        tot_s = _fmt_gib(r["total_hf"]) if r["total_hf"] is not None else "—"
        sd = str(r["files_done_sidecar"]) if r["files_done_sidecar"] is not None else "—"
        cm = r["resolved_commit"] or "—"
        err = (r["error"] or "—").replace("|", "\\|")
        if len(err) > 80:
            err = err[:77] + "..."
        nar = "yes" if r["in_narrow"] else "no"
        p = r.get("progress_pct")
        p_s = f"{p:.1f}" if p is not None else "—"
        lines.append(
            f"| `{r['id']}` | {r['tier']} | {nar} | {p_s} | {rem_s} | {tot_s} | {sd} | `{cm}` | {err} |"
        )

    lines += ["", "## Complete on D1 (skipped above)", "", f"Count: **{complete_n}** (at least one revision passes manifest + sidecar check).", ""]

    text = "\n".join(lines) + "\n"
    print(text, end="")

    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        tmp = args.out_md.with_suffix(args.out_md.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(args.out_md)
        print(f"Wrote {args.out_md}", file=sys.stderr)

    return 0


def load_registry_yaml_d1_ids(registry_path: Path) -> list[str]:
    data = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    return [m["id"] for m in data.get("models", []) if m.get("drive") == "d1" and m.get("id")]


if __name__ == "__main__":
    raise SystemExit(main())
