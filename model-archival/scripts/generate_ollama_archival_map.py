#!/usr/bin/env python3
"""
Build a human-readable map: Ollama model:tag -> archival disk(s) and path(s).

Reads docs/data/ollama-vm-models-inventory.yaml (from update_ollama_vm_inventory.py).
Writes docs/OLLAMA-ARCHIVAL-MODEL-MAP.md

Also writes docs/data/ollama-archival-global-manifest.yaml — one entry per model:tag with a
chosen canonical_disk (deduplicated view; replica_disks lists additional full copies).

Run after inventory refresh (e.g. end of ollama-hosting/scripts/ollama-sync.sh).
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = REPO_ROOT / "docs" / "data" / "ollama-vm-models-inventory.yaml"
DEFAULT_OUT = REPO_ROOT / "docs" / "OLLAMA-ARCHIVAL-MODEL-MAP.md"
DEFAULT_GLOBAL = REPO_ROOT / "docs" / "data" / "ollama-archival-global-manifest.yaml"


def _pick_canonical(rows: list[dict], preference: list[str]) -> tuple[dict, list[dict]]:
    """Choose one row as canonical by disk_label order in preference; rest are replicas."""
    by_lab = {str(m.get("disk_label", "")): m for m in rows}
    for lab in preference:
        if lab in by_lab:
            canon = by_lab[lab]
            reps = [m for m in rows if m is not canon]
            return canon, reps
    return rows[0], rows[1:]


def main() -> None:
    if yaml is None:
        print("PyYAML required", file=sys.stderr)
        sys.exit(1)
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="in_path", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out", dest="out_path", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--global-out",
        dest="global_out",
        type=Path,
        default=DEFAULT_GLOBAL,
        help="Deduplicated YAML manifest (one model:tag per row)",
    )
    ap.add_argument(
        "--canonical-preference",
        default="d5,d2,d3,d1",
        help="Comma-separated disk_label order when picking canonical copy (default: d5 first)",
    )
    args = ap.parse_args()
    pref = [x.strip() for x in args.canonical_preference.split(",") if x.strip()]

    if not args.in_path.is_file():
        print(f"skip: no inventory at {args.in_path}", file=sys.stderr)
        args.out_path.write_text(
            "# Ollama archival model map\n\n"
            "_No inventory yet._ Run `ollama-sync.sh` (or "
            "`uv run python scripts/update_ollama_vm_inventory.py --ssh ...`).\n",
            encoding="utf-8",
        )
        return

    doc = yaml.safe_load(args.in_path.read_text(encoding="utf-8")) or {}
    models = doc.get("models") or []
    updated = doc.get("updated_at_utc", "?")
    roots = doc.get("roots_scanned") or []
    vm = doc.get("ssh_host_vm", "")

    by_desc: dict[str, list[dict]] = defaultdict(list)
    for m in models:
        d = m.get("ollama_descriptor")
        if d:
            by_desc[str(d)].append(m)

    lines = [
        "# Ollama archival model map",
        "",
        f"_Generated from inventory snapshot **{updated}**._",
        "",
        "**Supermicro retention (after VM sync):** keep **Gemma 4** (MoE + dense + edge) and "
        "**Qwen Coder** only; see `ollama-hosting/scripts/ollama-supermicro-prune-plan.sh` and "
        "`ollama-hosting/docs/OLLAMA-CACHE-POLICY.md`. Other tags should exist on the archival VM below before "
        "you `ollama rm` them on the Supermicro.",
        "",
        f"**VM scan host:** `{vm or '—'}`",
        "",
        "## Roots scanned for inventory",
        "",
    ]
    for r in roots:
        lines.append(f"- **{r.get('disk_label', '?')}** → `{r.get('root_abs', '')}`")
    lines.extend(["", "## Model → disk(s)", "", "| Ollama `model:tag` | Disk | Archive root | ~Size | `supermicro_cleared` |", "|---|---:|---|---:|---|"])

    for desc in sorted(by_desc.keys(), key=str.lower):
        rows = by_desc[desc]
        for i, m in enumerate(rows):
            lab = m.get("disk_label", "")
            root = m.get("root_abs", "")
            sz = m.get("size_human", "")
            cl = m.get("supermicro_cleared", "unknown")
            name_cell = desc if i == 0 else "*(same tag)*"
            lines.append(f"| {name_cell} | {lab} | `{root}` | {sz} | {cl} |")

    # --- Deduplicated canonical section (one row per model:tag) ---
    lines.extend(["", "## Canonical location (deduplicated)", "", "One row per `model:tag`. **Canonical** is the preferred disk copy; **Replicas** are additional full mirrors on other disks.", "", "| Ollama `model:tag` | Canonical disk | Archive root | Replicas | ~Size | `supermicro_cleared` |", "|---|---:|---|---|---:|---|"])
    global_models: list[dict] = []
    for desc in sorted(by_desc.keys(), key=str.lower):
        rows = by_desc[desc]
        canon, reps = _pick_canonical(rows, pref)
        c_lab = canon.get("disk_label", "")
        c_root = canon.get("root_abs", "")
        sz = canon.get("size_human", "")
        cl = canon.get("supermicro_cleared", "unknown")
        rep_parts = [f"{m.get('disk_label', '')} `{m.get('root_abs', '')}`" for m in reps]
        rep_str = "; ".join(rep_parts) if rep_parts else "—"
        lines.append(f"| {desc} | {c_lab} | `{c_root}` | {rep_str} | {sz} | {cl} |")
        global_models.append(
            {
                "ollama_descriptor": desc,
                "canonical_disk": c_lab,
                "canonical_root": c_root,
                "replica_disks": [m.get("disk_label", "") for m in reps],
                "replica_roots": [m.get("root_abs", "") for m in reps],
                "size_bytes": canon.get("size_bytes"),
                "size_human": sz,
                "supermicro_cleared": cl,
            }
        )

    lines.extend(
        [
            "",
            "## Machine-readable source",
            "",
            f"- Full scan (one row per model × disk): [`docs/data/ollama-vm-models-inventory.yaml`](data/ollama-vm-models-inventory.yaml).",
            f"- **Deduplicated global manifest** (one row per model): [`docs/data/ollama-archival-global-manifest.yaml`](data/ollama-archival-global-manifest.yaml).",
            f"- Rotation log: [`docs/data/ollama-sync-rotation.state`](data/ollama-sync-rotation.state).",
            "",
        ]
    )

    args.out_path.parent.mkdir(parents=True, exist_ok=True)
    args.out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.out_path} ({len(by_desc)} descriptors)")

    global_doc = {
        "schema_version": 1,
        "updated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "canonical_preference": pref,
        "note": (
            "canonical_disk is chosen from the first label in canonical_preference that has a copy; "
            "replica_* lists other archival roots that also hold this model."
        ),
        "ssh_host_vm": vm,
        "models": global_models,
    }
    args.global_out.parent.mkdir(parents=True, exist_ok=True)
    args.global_out.write_text(
        yaml.safe_dump(global_doc, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"Wrote {args.global_out} ({len(global_models)} canonical descriptors)")


if __name__ == "__main__":
    main()
