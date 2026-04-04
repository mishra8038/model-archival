#!/usr/bin/env python3
"""
Build a human-readable map: Ollama model:tag -> archival disk(s) and path(s).

Reads docs/data/ollama-vm-models-inventory.yaml (from update_ollama_vm_inventory.py).
Writes docs/OLLAMA-ARCHIVAL-MODEL-MAP.md

Run after inventory refresh (e.g. end of ollama-hosting/scripts/ollama-sync.sh).
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = REPO_ROOT / "docs" / "data" / "ollama-vm-models-inventory.yaml"
DEFAULT_OUT = REPO_ROOT / "docs" / "OLLAMA-ARCHIVAL-MODEL-MAP.md"


def main() -> None:
    if yaml is None:
        print("PyYAML required", file=sys.stderr)
        sys.exit(1)
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="in_path", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out", dest="out_path", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

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

    lines.extend(
        [
            "",
            "## Machine-readable source",
            "",
            f"Canonical data: [`docs/data/ollama-vm-models-inventory.yaml`](data/ollama-vm-models-inventory.yaml). "
            f"Rotation log: [`docs/data/ollama-sync-rotation.state`](data/ollama-sync-rotation.state).",
            "",
        ]
    )

    args.out_path.parent.mkdir(parents=True, exist_ok=True)
    args.out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.out_path} ({len(by_desc)} descriptors)")


if __name__ == "__main__":
    main()
