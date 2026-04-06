#!/usr/bin/env python3
"""
Maintain OLLAMA_MODEL_REGISTRY.json — single place for queue, pull state, archive hints.

Stdlib only. Lives in ~/z/dev/ollama/registry/ (or pass --registry / --queue / --history).

  init                  Build registry from TARGET_QUEUE_ORDERED.txt + TARGET_PULL_HISTORY.csv
  merge-pull-history    Update models[*].pull from latest CSV rows per tag
  merge-manifest PATH   Update models[*].archive from ollama-archival-global-manifest.yaml
  export-queue          Write TARGET_QUEUE_ORDERED.txt from registry.queue
  status                Print markdown summary to stdout
  next-pending          First queue tag that still needs ollama pull (skips archive-only; see --re-pull-archived)
  list-pending          Tags that still need pull, one per line (--group to filter)
  sync-pull-from-archive  Mark queue tags complete when on_canonical_disk is set (optional CSV append)
  should-pull TAG       Print yes | no-complete | no-archived (for scripts)
  list-group GROUP      Tags in queue order with models[tag].group == GROUP
  apply-default-groups  Set models[*].group from built-in rules (--force overwrites)
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def default_group_for_tag(tag: str) -> str:
    """
    Classification label for target queue entries. Quantization (q4_K_M, q8_0, etc.) stays in the tag string.

    Groups:
      uncensored    Dolphin / abliterated / uncensored community names (all quants in queue).
      coding        Code models (DeepSeek Coder, Qwen2.5-Coder, StarCoder2).
      reasoning     DeepSeek-R1 family, QwQ.
      general       Gemma 3/4 instruct, small Llama instruct, Llama 3.2 3B.
      moe_instruct  Censored MoE instruct (e.g. Mixtral 8x7B instruct).
      instruct_70b  Dense ~70B class instruct (Llama 3.x 70B, Qwen2.5 72B, Nemotron 70B).
      qwen3         Qwen3 library line (tags starting with qwen3:, not qwen3.5).
      embedding     bge-m3, nomic-embed-text, mxbai-embed-large, snowflake-arctic-embed,
                    bge-large, embeddinggemma, granite-embedding, qwen3-embedding.
      vlm           Qwen2.5-VL.
      specialist    Frontier / multimodal Qwen3.5, Mathstral, Phi-4, Mistral Small 3.2, default bucket.
    """
    t = tag.lower()
    if (
        "abliterated" in t
        or "uncensored" in t
        or "neuraldaredevil" in t
        or t.startswith("dolphin-")
    ):
        return "uncensored"
    if (
        t.startswith("bge-m3")
        or t.startswith("bge-large")
        or t.startswith("nomic-embed")
        or t.startswith("mxbai-embed")
        or t.startswith("snowflake-arctic-embed")
        or t.startswith("embeddinggemma")
        or t.startswith("granite-embedding")
        or t.startswith("qwen3-embedding")
    ):
        return "embedding"
    if "qwen2.5vl" in tag or "qwen2.5-vl" in t:
        return "vlm"
    if (
        t.startswith("deepseek-coder")
        or t.startswith("qwen2.5-coder")
        or t.startswith("starcoder2")
    ):
        return "coding"
    if t.startswith("deepseek-r1") or t.startswith("qwq:"):
        return "reasoning"
    if t.startswith("qwen3.5:"):
        return "specialist"
    if t.startswith("qwen3:"):
        return "qwen3"
    if (
        t.startswith("llama3.3:70b")
        or t.startswith("llama3.1:70b")
        or t.startswith("qwen2.5:72b")
        or t.startswith("nemotron:70b")
    ):
        return "instruct_70b"
    if t.startswith("mixtral:8x7b"):
        return "moe_instruct"
    if t.startswith("gemma") or t.startswith("llama3.1:8b") or t.startswith("llama3.2:"):
        return "general"
    if t.startswith("mathstral") or t.startswith("phi4:") or t.startswith("mistral-small"):
        return "specialist"
    return "specialist"


def _root() -> Path:
    return Path(__file__).resolve().parent


def _default_paths() -> dict[str, Path]:
    r = _root()
    return {
        "registry": r / "OLLAMA_MODEL_REGISTRY.json",
        "queue": r / "TARGET_QUEUE_ORDERED.txt",
        "history": r / "TARGET_PULL_HISTORY.csv",
    }


def _empty_model_entry() -> dict[str, Any]:
    return {
        "group": None,
        "approx_size_gb": None,
        "pull": {
            "status": "pending",
            "last_completed_utc": None,
            "last_failed_utc": None,
            "history_note": None,
        },
        "archive": {
            "on_canonical_disk": None,
            "canonical_root": None,
            "supermicro_cleared": None,
            "size_human": None,
            "replica_disks": [],
        },
        "notes": "",
    }


def _new_model_entry(tag: str) -> dict[str, Any]:
    entry = _empty_model_entry()
    entry["group"] = default_group_for_tag(tag)
    return entry


def _parse_queue_file(path: Path) -> list[str]:
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def _parse_pull_csv(path: Path) -> dict[str, dict[str, Any]]:
    """Latest row per ollama_tag (file order wins for duplicates)."""
    if not path.is_file():
        return {}
    by_tag: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tag = (row.get("ollama_tag") or "").strip()
            if not tag:
                continue
            by_tag[tag] = {
                "iso_utc": (row.get("iso_utc") or "").strip(),
                "approx_size_gb": (row.get("approx_size_gb") or "").strip(),
                "status": (row.get("status") or "").strip(),
                "notes": (row.get("notes") or "").strip(),
            }
    return by_tag


def _parse_global_manifest(path: Path) -> dict[str, dict[str, Any]]:
    """
    Parse ollama-archival-global-manifest.yaml without PyYAML.
    Expects list items with ollama_descriptor, canonical_disk, canonical_root, etc.
    """
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"(?m)^- ollama_descriptor:\s*", text)
    out: dict[str, dict[str, Any]] = {}
    for block in blocks[1:]:
        lines = block.splitlines()
        if not lines:
            continue
        first = lines[0].strip()
        tag = first.strip("'\"")
        data: dict[str, Any] = {"ollama_descriptor": tag}
        for line in lines[1:]:
            m = re.match(r"^\s+([a-zA-Z0-9_]+):\s*(.*)$", line)
            if not m:
                continue
            key, val = m.group(1), m.group(2).strip()
            if val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            elif val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            if key in ("replica_disks", "replica_roots"):
                continue
            data[key] = val
        desc = data.get("ollama_descriptor")
        if desc:
            out[str(desc)] = data
    return out


def cmd_init(args: argparse.Namespace) -> None:
    paths = _default_paths()
    reg_path = Path(args.registry) if args.registry else paths["registry"]
    q_path = Path(args.queue) if args.queue else paths["queue"]
    h_path = Path(args.history) if args.history else paths["history"]

    queue = _parse_queue_file(q_path)
    csv_by_tag = _parse_pull_csv(h_path)
    models: dict[str, Any] = {}
    for tag in queue:
        entry = _new_model_entry(tag)
        if tag in csv_by_tag:
            row = csv_by_tag[tag]
            st = row["status"].lower()
            if st == "completed":
                entry["pull"]["status"] = "complete"
                entry["pull"]["last_completed_utc"] = row["iso_utc"] or None
            elif st == "failed":
                entry["pull"]["status"] = "failed"
                entry["pull"]["last_failed_utc"] = row["iso_utc"] or None
            if row.get("approx_size_gb"):
                try:
                    entry["approx_size_gb"] = float(row["approx_size_gb"])
                except ValueError:
                    entry["approx_size_gb"] = None
            if row.get("notes"):
                entry["pull"]["history_note"] = row["notes"]
        models[tag] = entry

    doc = {
        "schema_version": 2,
        "updated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "queue": queue,
        "models": models,
        "links": {
            "ollama_sync_script": "ollama-hosting/scripts/ollama-sync.sh",
            "archival_manifest": "ollama-hosting/docs/data/ollama-archival-global-manifest.yaml",
            "archival_model_map": "ollama-hosting/docs/OLLAMA-ARCHIVAL-MODEL-MAP.md",
            "workflow_doc": "ollama-hosting/docs/OLLAMA-ARCHIVE-WORKFLOW.md",
            "registry_dir": "ollama-hosting/registry",
        },
    }
    reg_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"wrote {reg_path} ({len(queue)} tags)", file=sys.stderr)


def _load_registry(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_registry(path: Path, doc: dict[str, Any]) -> None:
    doc["updated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")


def cmd_merge_pull_history(args: argparse.Namespace) -> None:
    paths = _default_paths()
    reg_path = Path(args.registry) if args.registry else paths["registry"]
    h_path = Path(args.history) if args.history else paths["history"]
    doc = _load_registry(reg_path)
    csv_by_tag = _parse_pull_csv(h_path)
    models = doc.setdefault("models", {})
    for tag, row in csv_by_tag.items():
        entry = models.setdefault(tag, _new_model_entry(tag))
        if not entry.get("group"):
            entry["group"] = default_group_for_tag(tag)
        pull = entry.setdefault("pull", {})
        st = row["status"].lower()
        if st == "completed":
            pull["status"] = "complete"
            pull["last_completed_utc"] = row["iso_utc"] or pull.get("last_completed_utc")
        elif st == "failed":
            pull["status"] = "failed"
            pull["last_failed_utc"] = row["iso_utc"] or pull.get("last_failed_utc")
        if row.get("approx_size_gb"):
            try:
                entry["approx_size_gb"] = float(row["approx_size_gb"])
            except ValueError:
                pass
        if row.get("notes"):
            pull["history_note"] = row["notes"]
    _save_registry(reg_path, doc)
    print(f"merged pull history into {reg_path}", file=sys.stderr)


def cmd_merge_manifest(args: argparse.Namespace) -> None:
    paths = _default_paths()
    reg_path = Path(args.registry) if args.registry else paths["registry"]
    man_path = Path(args.manifest)
    if not man_path.is_file():
        print(f"error: manifest not found: {man_path}", file=sys.stderr)
        sys.exit(1)
    doc = _load_registry(reg_path)
    by_tag = _parse_global_manifest(man_path)
    models = doc.setdefault("models", {})
    for tag, meta in by_tag.items():
        entry = models.setdefault(tag, _new_model_entry(tag))
        if not entry.get("group"):
            entry["group"] = default_group_for_tag(tag)
        arch = entry.setdefault("archive", {})
        arch["on_canonical_disk"] = meta.get("canonical_disk")
        arch["canonical_root"] = meta.get("canonical_root")
        arch["size_human"] = meta.get("size_human")
        cleared = (meta.get("supermicro_cleared") or "").lower()
        arch["supermicro_cleared"] = cleared in ("yes", "true", "1")
    _save_registry(reg_path, doc)
    print(f"merged manifest ({len(by_tag)} descriptors) into {reg_path}", file=sys.stderr)


def cmd_export_queue(args: argparse.Namespace) -> None:
    paths = _default_paths()
    reg_path = Path(args.registry) if args.registry else paths["registry"]
    out_path = Path(args.out) if args.out else paths["queue"]
    doc = _load_registry(reg_path)
    queue = doc.get("queue") or []
    header = (
        "# Generated from OLLAMA_MODEL_REGISTRY.json — edit the registry and re-run:\n"
        "#   cd ~/z/dev/ollama/registry && python3 ollama_registry_tool.py export-queue\n"
    )
    body = "\n".join(queue) + "\n"
    out_path.write_text(header + "\n" + body, encoding="utf-8")
    print(f"wrote {out_path} ({len(queue)} lines)", file=sys.stderr)


def _pull_status_for_tag(doc: dict[str, Any], tag: str) -> str:
    models = doc.get("models") or {}
    entry = models.get(tag) or _empty_model_entry()
    pull = entry.get("pull") or {}
    return (pull.get("status") or "pending").lower()


def _archived_on_vm(doc: dict[str, Any], tag: str) -> bool:
    """True if merge-manifest recorded this descriptor on a canonical archival disk."""
    models = doc.get("models") or {}
    entry = models.get(tag) or {}
    arch = entry.get("archive") or {}
    disk = arch.get("on_canonical_disk")
    if disk is None:
        return False
    if isinstance(disk, str):
        s = disk.strip()
        return bool(s) and s != "—"
    return bool(disk)


def _pull_complete(doc: dict[str, Any], tag: str) -> bool:
    return _pull_status_for_tag(doc, tag) == "complete"


def _needs_ollama_pull(doc: dict[str, Any], tag: str, *, re_pull_archived: bool) -> bool:
    """False => skip ollama pull (already marked complete, or weights exist on archival VM)."""
    if _pull_complete(doc, tag):
        return False
    if not re_pull_archived and _archived_on_vm(doc, tag):
        return False
    return True


def _group_for_tag(doc: dict[str, Any], tag: str) -> str:
    models = doc.get("models") or {}
    entry = models.get(tag) or {}
    g = entry.get("group")
    if g:
        return str(g)
    return default_group_for_tag(tag)


def cmd_apply_default_groups(args: argparse.Namespace) -> None:
    paths = _default_paths()
    reg_path = Path(args.registry) if args.registry else paths["registry"]
    doc = _load_registry(reg_path)
    if int(doc.get("schema_version") or 1) < 2:
        doc["schema_version"] = 2
    models = doc.setdefault("models", {})
    all_tags = set(doc.get("queue") or []) | set(models.keys())
    n = 0
    for tag in all_tags:
        entry = models.setdefault(tag, _new_model_entry(tag))
        if args.force or not entry.get("group"):
            entry["group"] = default_group_for_tag(tag)
            n += 1
    _save_registry(reg_path, doc)
    print(f"apply-default-groups: touched {n} tag(s) → {reg_path}", file=sys.stderr)


def cmd_next_pending(args: argparse.Namespace) -> None:
    paths = _default_paths()
    reg_path = Path(args.registry) if args.registry else paths["registry"]
    doc = _load_registry(reg_path)
    queue: list[str] = doc.get("queue") or []
    want_g = (getattr(args, "group", None) or "").strip() or None
    re_pa = bool(getattr(args, "re_pull_archived", False))
    for tag in queue:
        if want_g and _group_for_tag(doc, tag) != want_g:
            continue
        if _needs_ollama_pull(doc, tag, re_pull_archived=re_pa):
            print(tag, end="")
            return
    # stdout empty = nothing pending


def cmd_list_pending(args: argparse.Namespace) -> None:
    paths = _default_paths()
    reg_path = Path(args.registry) if args.registry else paths["registry"]
    doc = _load_registry(reg_path)
    queue: list[str] = doc.get("queue") or []
    want_g = (getattr(args, "group", None) or "").strip() or None
    re_pa = bool(getattr(args, "re_pull_archived", False))
    pending: list[str] = []
    for t in queue:
        if want_g and _group_for_tag(doc, t) != want_g:
            continue
        if _needs_ollama_pull(doc, t, re_pull_archived=re_pa):
            pending.append(t)
    print("\n".join(pending))


def cmd_list_group(args: argparse.Namespace) -> None:
    paths = _default_paths()
    reg_path = Path(args.registry) if args.registry else paths["registry"]
    doc = _load_registry(reg_path)
    want = args.group_name.strip()
    queue: list[str] = doc.get("queue") or []
    for tag in queue:
        if _group_for_tag(doc, tag) == want:
            print(tag)


def cmd_sync_pull_from_archive(args: argparse.Namespace) -> None:
    """Mark pull complete for queued tags that appear on archival VM (on_canonical_disk)."""
    paths = _default_paths()
    reg_path = Path(args.registry) if args.registry else paths["registry"]
    h_path = Path(args.history) if getattr(args, "history", None) else paths["history"]
    doc = _load_registry(reg_path)
    queue: list[str] = doc.get("queue") or []
    models = doc.setdefault("models", {})
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    n = 0
    csv_rows: list[tuple[str, str, str, str, str]] = []
    for tag in queue:
        if not _archived_on_vm(doc, tag):
            continue
        if _pull_complete(doc, tag):
            continue
        entry = models.setdefault(tag, _new_model_entry(tag))
        pull = entry.setdefault("pull", {})
        pull["status"] = "complete"
        pull["last_completed_utc"] = now
        prev = (pull.get("history_note") or "").strip()
        note = "sync-pull-from-archive-vm"
        pull["history_note"] = f"{prev}; {note}".strip("; ") if prev else note
        gb = entry.get("approx_size_gb")
        size_s = str(gb) if isinstance(gb, (int, float)) else "?"
        csv_rows.append((now, tag, size_s, "completed", note))
        n += 1
    if n:
        _save_registry(reg_path, doc)
        if h_path.parent.is_dir():
            new_file = not h_path.is_file()
            with h_path.open("a", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                if new_file:
                    w.writerow(["iso_utc", "ollama_tag", "approx_size_gb", "status", "notes"])
                w.writerows(csv_rows)
    print(f"sync-pull-from-archive: marked {n} tag(s) complete (archived on VM)", file=sys.stderr)


def cmd_should_pull(args: argparse.Namespace) -> None:
    paths = _default_paths()
    reg_path = Path(args.registry) if args.registry else paths["registry"]
    doc = _load_registry(reg_path)
    tag = args.tag.strip()
    re_pa = bool(getattr(args, "re_pull_archived", False))
    if _pull_complete(doc, tag):
        print("no-complete", end="")
        return
    if not re_pa and _archived_on_vm(doc, tag):
        print("no-archived", end="")
        return
    print("yes", end="")


def cmd_status(args: argparse.Namespace) -> None:
    paths = _default_paths()
    reg_path = Path(args.registry) if args.registry else paths["registry"]
    doc = _load_registry(reg_path)
    queue: list[str] = doc.get("queue") or []
    models: dict[str, Any] = doc.get("models") or {}
    print("| # | Tag | Group | Pull | Archive disk | Supermicro cleared |")
    print("|---|-----|-------|------|--------------|--------------------|")
    for i, tag in enumerate(queue, 1):
        m = models.get(tag, _empty_model_entry())
        pull = m.get("pull") or {}
        arch = m.get("archive") or {}
        ps = pull.get("status") or "?"
        disk = arch.get("on_canonical_disk") or "—"
        cl = arch.get("supermicro_cleared")
        cl_s = "—" if cl is None else ("yes" if cl else "no")
        grp = _group_for_tag(doc, tag)
        print(f"| {i} | `{tag}` | {grp} | {ps} | {disk} | {cl_s} |")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", help="Path to OLLAMA_MODEL_REGISTRY.json")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Create registry from queue file + CSV")
    p_init.add_argument("--queue", help="TARGET_QUEUE_ORDERED.txt")
    p_init.add_argument("--history", help="TARGET_PULL_HISTORY.csv")
    p_init.set_defaults(func=cmd_init)

    p_mph = sub.add_parser("merge-pull-history", help="Fold CSV into registry models")
    p_mph.add_argument("--history", help="TARGET_PULL_HISTORY.csv")
    p_mph.set_defaults(func=cmd_merge_pull_history)

    p_mm = sub.add_parser("merge-manifest", help="Fold archival global manifest YAML")
    p_mm.add_argument("manifest", type=str, help="Path to ollama-archival-global-manifest.yaml")
    p_mm.set_defaults(func=cmd_merge_manifest)

    p_eq = sub.add_parser("export-queue", help="Write queue file from registry")
    p_eq.add_argument("--out", help="Output path (default TARGET_QUEUE_ORDERED.txt)")
    p_eq.set_defaults(func=cmd_export_queue)

    p_st = sub.add_parser("status", help="Markdown table to stdout")
    p_st.set_defaults(func=cmd_status)

    p_np = sub.add_parser(
        "next-pending",
        help="First tag that still needs ollama pull (skips tags only on archival VM)",
    )
    p_np.add_argument("--group", help="Only consider tags in this classification (e.g. uncensored)")
    p_np.add_argument(
        "--re-pull-archived",
        action="store_true",
        help="Ignore archival VM presence; only CSV/registry pull status matters",
    )
    p_np.set_defaults(func=cmd_next_pending)

    p_lp = sub.add_parser("list-pending", help="Tags that still need ollama pull, one per line")
    p_lp.add_argument("--group", help="Only tags in this classification")
    p_lp.add_argument(
        "--re-pull-archived",
        action="store_true",
        help="Include tags that are on archival VM but not marked pull complete",
    )
    p_lp.set_defaults(func=cmd_list_pending)

    p_sfa = sub.add_parser(
        "sync-pull-from-archive",
        help="Set pull.complete for queued tags with on_canonical_disk; append CSV rows",
    )
    p_sfa.add_argument("--history", help="TARGET_PULL_HISTORY.csv (default beside registry)")
    p_sfa.set_defaults(func=cmd_sync_pull_from_archive)

    p_sp = sub.add_parser(
        "should-pull",
        help="Print yes | no-complete | no-archived (stdout only; for shell skips)",
    )
    p_sp.add_argument("tag", type=str, help="Ollama descriptor")
    p_sp.add_argument(
        "--re-pull-archived",
        action="store_true",
        help="Treat archived-on-VM as still needing pull if not complete",
    )
    p_sp.set_defaults(func=cmd_should_pull)

    p_lg = sub.add_parser("list-group", help="List queued tags in a classification (queue order)")
    p_lg.add_argument("group_name", help="e.g. uncensored, coding, reasoning")
    p_lg.set_defaults(func=cmd_list_group)

    p_adg = sub.add_parser(
        "apply-default-groups",
        help="Set models[*].group from default_group_for_tag()",
    )
    p_adg.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing non-empty group values",
    )
    p_adg.set_defaults(func=cmd_apply_default_groups)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
