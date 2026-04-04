#!/usr/bin/env python3
"""
Scan Ollama cache roots on a VM (or locally), compute per-model:tag disk size from
manifests + blob files, and write docs/data/ollama-vm-models-inventory.yaml.

Run after each ollama-sync (or periodically):
  cd ollama-hosting && uv run python scripts/update_ollama_vm_inventory.py --ssh x@192.168.8.65

Optional: infer supermicro_cleared by scanning supermicro's ~/.ollama cache:
  uv run python scripts/update_ollama_vm_inventory.py --ssh x@192.168.8.65 \\
    --supermicro-ssh x@supermicro --infer-supermicro-cleared

Preserves existing supermicro_cleared (yes/no/unknown) unless --infer-supermicro-cleared.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "docs" / "data" / "ollama-vm-models-inventory.yaml"

# Remote scanner: stdlib only. Prints one JSON object per line (NDJSON).
_REMOTE_SCANNER = r"""
import json, sys
from pathlib import Path

def human_bytes(n):
    n = float(n)
    for u in ("B", "KiB", "MiB", "GiB", "TiB"):
        if n < 1024.0 or u == "TiB":
            if u == "B":
                return f"{int(n)} B"
            return f"{n:.2f} {u}"
        n /= 1024.0

def digests_from_manifest(obj):
    out = []
    cfg = obj.get("config")
    if isinstance(cfg, dict) and cfg.get("digest"):
        out.append(cfg["digest"])
    for layer in obj.get("layers") or []:
        if isinstance(layer, dict) and layer.get("digest"):
            out.append(layer["digest"])
    return out

def blob_size(blobs_dir, digest):
    if not digest or not isinstance(digest, str):
        return 0
    hexpart = digest.split(":", 1)[-1] if ":" in digest else digest
    p = blobs_dir / ("sha256-" + hexpart)
    if p.is_file():
        return p.stat().st_size
    found = list(blobs_dir.glob("sha256-" + hexpart + "*"))
    if found and found[0].is_file():
        return found[0].stat().st_size
    return 0

def scan_root(root, disk_label):
    root = Path(root).resolve()
    lib = root / "models" / "manifests" / "registry.ollama.ai" / "library"
    blobs = root / "models" / "blobs"
    if not lib.is_dir():
        return []
    rows = []
    for mf in lib.rglob("*"):
        if not mf.is_file():
            continue
        try:
            rel = mf.relative_to(lib)
        except ValueError:
            continue
        parts = rel.parts
        if len(parts) < 2:
            continue
        model = parts[0]
        tag = "/".join(parts[1:])
        try:
            obj = json.loads(mf.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        total = 0
        for d in digests_from_manifest(obj):
            total += blob_size(blobs, d)
        desc = f"{model}:{tag}"
        rows.append({
            "disk_label": disk_label,
            "root_abs": str(root),
            "manifest_relpath": str(rel).replace("\\", "/"),
            "ollama_descriptor": desc,
            "size_bytes": total,
        })
    return rows

def main():
    specs = json.loads(sys.stdin.read())
    all_rows = []
    for item in specs:
        root = item["root"]
        label = item["label"]
        p = Path(root)
        if not p.is_dir():
            continue
        all_rows.extend(scan_root(root, label))
    for r in all_rows:
        r["size_human"] = human_bytes(r["size_bytes"])
        print(json.dumps(r))

if __name__ == "__main__":
    main()
"""


def _run_remote_scanner(ssh: str, roots: list[tuple[str, str]]) -> list[dict[str, Any]]:
    specs_json = json.dumps([{"root": r, "label": l} for r, l in roots])
    b64 = base64.b64encode(specs_json.encode()).decode("ascii")
    body = _REMOTE_SCANNER
    body = body.replace(
        "def main():\n    specs = json.loads(sys.stdin.read())\n    all_rows = []\n    for item in specs:",
        "def main():\n    import base64\n    specs = json.loads(base64.b64decode('"
        + b64
        + "').decode())\n    all_rows = []\n    for item in specs:",
        1,
    )
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", ssh, "python3", "-c", body],
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
        capture_output=True,
        timeout=600,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr.decode(errors="replace"))
        raise SystemExit(proc.returncode or 1)
    rows = []
    for line in proc.stdout.decode().splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _run_local_scan(roots: list[tuple[str, str]]) -> list[dict[str, Any]]:
    specs_json = json.dumps([{"root": r, "label": l} for r, l in roots])
    b64 = base64.b64encode(specs_json.encode()).decode("ascii")
    body = _REMOTE_SCANNER.replace(
        "def main():\n    specs = json.loads(sys.stdin.read())\n    all_rows = []\n    for item in specs:",
        "def main():\n    import base64\n    specs = json.loads(base64.b64decode('"
        + b64
        + "').decode())\n    all_rows = []\n    for item in specs:",
        1,
    )
    proc = subprocess.run(
        [sys.executable, "-c", body],
        capture_output=True,
        timeout=600,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr.decode(errors="replace"))
        raise SystemExit(proc.returncode or 1)
    rows = []
    for line in proc.stdout.decode().splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _descriptors_on_host(ssh: str, ollama_home: str) -> set[str]:
    """Return set of model:tag from manifests under ollama_home/models/manifests/.../library."""
    script = r"""
import sys
from pathlib import Path
root = Path(sys.argv[1]).expanduser() / "models" / "manifests" / "registry.ollama.ai" / "library"
if not root.is_dir():
    sys.exit(0)
for mf in root.rglob("*"):
    if not mf.is_file():
        continue
    rel = mf.relative_to(root)
    parts = rel.parts
    if len(parts) < 2:
        continue
    model, tag = parts[0], "/".join(parts[1:])
    print(f"{model}:{tag}")
"""
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", ssh, "python3", "-c", script, ollama_home],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr or "")
        return set()
    return {ln.strip() for ln in proc.stdout.splitlines() if ln.strip()}


def _merge_rows(
    new_rows: list[dict[str, Any]],
    existing: dict[str, Any],
    infer_cleared: set[str] | None,
) -> dict[str, Any]:
    old_models = existing.get("models") or []
    by_key: dict[str, dict[str, Any]] = {}
    for m in old_models:
        k = (m.get("ollama_descriptor"), m.get("disk_label"))
        if k[0]:
            by_key[str(k)] = dict(m)

    out_models: list[dict[str, Any]] = []
    for r in sorted(new_rows, key=lambda x: (x["disk_label"], x["ollama_descriptor"])):
        key = str((r["ollama_descriptor"], r["disk_label"]))
        prev = by_key.get(key, {})
        cleared = prev.get("supermicro_cleared", "unknown")
        if infer_cleared is not None:
            desc = r["ollama_descriptor"]
            cleared = "no" if desc in infer_cleared else "yes"
        out_models.append(
            {
                "ollama_descriptor": r["ollama_descriptor"],
                "disk_label": r["disk_label"],
                "root_abs": r["root_abs"],
                "manifest_relpath": r["manifest_relpath"],
                "size_bytes": r["size_bytes"],
                "size_human": r["size_human"],
                "supermicro_cleared": cleared,
            }
        )
    return {"models": out_models}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ssh", help="user@host for VM (remote scan)")
    ap.add_argument(
        "--root",
        action="append",
        default=[],
        metavar="LABEL=PATH",
        help="Disk label and root, e.g. d5=/mnt/models/d5/supermicro (repeatable)",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--supermicro-ssh",
        metavar="user@host",
        help="SSH to supermicro for --infer-supermicro-cleared",
    )
    ap.add_argument(
        "--supermicro-ollama-home",
        default="~/.ollama",
        help="Ollama dir on supermicro (default ~/.ollama)",
    )
    ap.add_argument(
        "--infer-supermicro-cleared",
        action="store_true",
        help="Set supermicro_cleared yes/no from supermicro manifest list vs VM descriptors",
    )
    args = ap.parse_args()

    if yaml is None:
        print("PyYAML required: uv sync", file=sys.stderr)
        sys.exit(1)

    default_roots: list[tuple[str, str]] = [
        ("d5", "/mnt/models/d5/supermicro"),
        ("d2", "/mnt/models/d2/supermicro"),
        ("d3", "/mnt/models/d3/supermicro"),
        ("d1", "/mnt/models/d1/supermicro"),
    ]
    roots: list[tuple[str, str]] = []
    if args.root:
        for spec in args.root:
            if "=" not in spec:
                ap.error(f"Bad --root {spec!r}, want LABEL=PATH")
            lab, path = spec.split("=", 1)
            roots.append((lab.strip(), path.strip()))
    else:
        roots = default_roots

    if args.ssh:
        rows = _run_remote_scanner(args.ssh, roots)
    else:
        rows = _run_local_scan(roots)

    existing: dict[str, Any] = {}
    if args.out.exists():
        existing = yaml.safe_load(args.out.read_text()) or {}

    infer_set: set[str] | None = None
    if args.infer_supermicro_cleared:
        if not args.supermicro_ssh:
            ap.error("--infer-supermicro-cleared requires --supermicro-ssh")
        home = args.supermicro_ollama_home
        infer_set = _descriptors_on_host(args.supermicro_ssh, home)

    doc = {
        "schema_version": 1,
        "updated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ssh_host_vm": args.ssh or existing.get("ssh_host_vm"),
        "roots_scanned": [{"disk_label": l, "root_abs": r} for l, r in roots],
        "size_note": (
            "size_bytes is the sum of blob files referenced by this manifest; shared blobs are "
            "counted again for each tag, so row sums overestimate total disk under models/blobs."
        ),
        **_merge_rows(rows, existing, infer_set),
    }
    if args.infer_supermicro_cleared:
        doc["supermicro_inventory_ssh"] = args.supermicro_ssh
        doc["supermicro_cleared_note"] = (
            "supermicro_cleared inferred: no = still on supermicro cache; yes = not listed on supermicro (cleared or never there)."
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        yaml.safe_dump(
            doc,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {args.out} ({len(doc['models'])} models)")


if __name__ == "__main__":
    main()
