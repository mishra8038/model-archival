#!/usr/bin/env python3
"""
Archival VM destination rotation + inventory scan roots for ollama-sync.sh.

- If ARCHIVAL_VM_DEST is not passed: pick the next site from the cycle (state file),
  emit bash exports for eval.
- If --dest is passed (fixed): use that path, do not advance rotation on success.

State: docs/data/ollama-sync-rotation.state (JSON).

Usage (from ollama-sync.sh):
  eval "$(python3 scripts/ollama_archival_rotation.py prepare --repo ROOT [--dest PATH])"
  # ... sync ...
  python3 scripts/ollama_archival_rotation.py advance-after-success --repo ROOT \\
    --used-dest "$ARCHIVAL_VM_DEST" --used-label "$OLLAMA_SYNC_DISK_LABEL" \\
    --advance "$OLLAMA_SYNC_ROTATION_ADVANCE"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path


def _default_cycle() -> list[tuple[str, str]]:
    return [
        ("d5", "/mnt/models/d5/supermicro"),
        ("d2", "/mnt/models/d2/supermicro"),
        ("d3", "/mnt/models/d3/supermicro"),
        ("d1", "/mnt/models/d1/supermicro"),
    ]


def _parse_cycle(raw: str | None) -> list[tuple[str, str]]:
    if not raw or not raw.strip():
        return _default_cycle()
    out: list[tuple[str, str]] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            lab, pth = part.split("=", 1)
            out.append((lab.strip(), pth.strip()))
        else:
            pth = part
            m = re.search(r"/mnt/models/(d[0-9]+)/", pth)
            lab = m.group(1) if m else Path(pth).name or "disk"
            out.append((lab, pth))
    return out if out else _default_cycle()


def _label_for_path(path: str, cycle: list[tuple[str, str]]) -> str:
    path = path.rstrip("/")
    for lab, root in cycle:
        if path == root.rstrip("/") or path.startswith(root.rstrip("/") + "/"):
            return lab
    m = re.search(r"/mnt/models/(d[0-9]+)/", path)
    return m.group(1) if m else "unknown"


def _shell_export(name: str, value: str) -> str:
    return f"export {name}={shlex.quote(value)}\n"


def cmd_prepare(repo: Path, dest: str | None, cycle_raw: str | None) -> None:
    cycle = _parse_cycle(cycle_raw or os.environ.get("ARCHIVAL_VM_SITE_CYCLE"))
    # One shlex.quote on the full argv tail (paths have no spaces).
    inv_flags = " ".join(f"--root {lab}={pth}" for lab, pth in cycle)
    sys.stdout.write(_shell_export("OLLAMA_VM_INVENTORY_ROOT_FLAGS", inv_flags))

    if dest:
        label = _label_for_path(dest, cycle)
        sys.stdout.write(_shell_export("ARCHIVAL_VM_DEST", dest))
        sys.stdout.write(_shell_export("OLLAMA_SYNC_DISK_LABEL", label))
        sys.stdout.write(_shell_export("OLLAMA_SYNC_ROTATION_ADVANCE", "0"))
        return

    state_path = repo / "docs" / "data" / "ollama-sync-rotation.state"
    data: dict = {}
    if state_path.is_file():
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    idx = int(data.get("next_index", 0)) % len(cycle)
    lab, pth = cycle[idx]
    sys.stdout.write(_shell_export("ARCHIVAL_VM_DEST", pth))
    sys.stdout.write(_shell_export("OLLAMA_SYNC_DISK_LABEL", lab))
    sys.stdout.write(_shell_export("OLLAMA_SYNC_ROTATION_ADVANCE", "1"))


def cmd_advance(
    repo: Path,
    used_dest: str,
    used_label: str,
    advance: str,
    cycle_raw: str | None,
) -> None:
    if advance not in ("1", "true", "yes"):
        return
    cycle = _parse_cycle(cycle_raw or os.environ.get("ARCHIVAL_VM_SITE_CYCLE"))
    state_path = repo / "docs" / "data" / "ollama-sync-rotation.state"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if state_path.is_file():
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    idx = int(data.get("next_index", 0)) % max(len(cycle), 1)
    # Confirm used dest matches cycle[idx] (sanity)
    _lab, expected = cycle[idx]
    if used_dest.rstrip("/") != expected.rstrip("/"):
        # Still advance — operator may have changed cycle file
        pass
    new_idx = (idx + 1) % len(cycle)
    hist = list(data.get("sync_history") or [])
    hist.append(
        {
            "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "disk_label": used_label,
            "root_abs": used_dest,
        }
    )
    data["schema_version"] = 1
    data["next_index"] = new_idx
    data["sync_history"] = hist[-200:]  # cap
    state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_prep = sub.add_parser("prepare", help="Emit bash exports for ollama-sync")
    p_prep.add_argument("--repo", type=Path, required=True)
    p_prep.add_argument("--dest", default=None, help="Fixed ARCHIVAL_VM_DEST (skip rotation pick)")
    p_prep.add_argument(
        "--cycle",
        default=None,
        help="Override cycle (comma-separated LABEL=PATH or paths under /mnt/models/)",
    )

    p_adv = sub.add_parser("advance-after-success", help="Bump rotation index after successful sync")
    p_adv.add_argument("--repo", type=Path, required=True)
    p_adv.add_argument("--used-dest", required=True)
    p_adv.add_argument("--used-label", default="")
    p_adv.add_argument("--advance", default="0", help="1 if this run used rotated dest")
    p_adv.add_argument("--cycle", default=None)

    args = ap.parse_args()
    if args.cmd == "prepare":
        cmd_prepare(args.repo, args.dest, args.cycle)
    else:
        cmd_advance(
            args.repo,
            args.used_dest,
            args.used_label or _label_for_path(args.used_dest, _parse_cycle(args.cycle)),
            args.advance,
            args.cycle,
        )


if __name__ == "__main__":
    main()
