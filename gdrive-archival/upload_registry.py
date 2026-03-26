#!/usr/bin/env python3
"""
Upload trees defined in gdrive-registry.yaml → GDrive models/<relpath>/...

For each model revision directory (manifest.json or archiver layout), run local
SHA verify then rclone copy --checksum --transfers 1. No post-upload download
from GDrive.

If registry includes path ``d5`` with ``tree_upload_min_depth`` (default 3), each
sync unit (folder at least that many levels below ``d5/``, plus shallow top-level
branches that never reach that depth) is copied and logged as ``registry-tree``.
Set ``tree_upload_min_depth: 0`` on the ``d5`` root for a single full-tree
``registry-d5`` copy (legacy). Per-model ``registry-model`` uploads still run for
revision dirs; tree units skip paths excluded by ``d5_exclude`` / ``tree_upload_exclude``
and skip subtrees that contain a model revision dir.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml

# Logged to uploaded.log after each subtree rclone (relpath from models_mount).
TREE_UPLOAD_KIND = "registry-tree"

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
REGISTRY_PATH = SCRIPT_DIR / "gdrive-registry.yaml"
VERIFY_JSONL = SCRIPT_DIR / "logs" / "gdrive-preupload-verify-failures.jsonl"
VERIFY_MD = SCRIPT_DIR / "logs" / "gdrive-preupload-verify-report.md"
UPLOADED_LOG_PATH = SCRIPT_DIR / "logs" / "uploaded.log"
REGISTRY_UPLOAD_STATE_PATH = SCRIPT_DIR / "logs" / "registry-upload-state.json"
REGISTRY_UPLOAD_STATUS_MD = SCRIPT_DIR / "logs" / "GDRIVE-REGISTRY-UPLOAD-STATUS.md"
UPLOADED_MODELS_JSON = SCRIPT_DIR / "logs" / "registry-uploaded-models.json"
UPLOADED_MODELS_MD = SCRIPT_DIR / "logs" / "registry-uploaded-models.md"
STATE_VERSION = 1


def _state_now_iso() -> str:
  return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_yaml(path: Path) -> dict:
  with path.open("r") as f:
    return yaml.safe_load(f) or {}


def _tmp_in_path(p: Path) -> bool:
  return ".tmp" in p.parts


def discover_model_dirs(mount: Path, root_relpath: str) -> Set[Path]:
  """
  Model revision dirs: parent of manifest.json, excluding .tmp paths.
  Also org/repo/rev leaves under .../quantized and .../uncensored when rev has weights.
  """
  root = (mount / root_relpath).resolve()
  found: Set[Path] = set()
  if not root.is_dir():
    return found

  for mf in root.rglob("manifest.json"):
    if _tmp_in_path(mf):
      continue
    found.add(mf.parent.resolve())

  # Sidecar-only or missing manifest: standard archiver depth under quantized|uncensored
  parts = root_relpath.strip("/").split("/")
  if len(parts) >= 2 and parts[1] in ("quantized", "uncensored"):
    try:
      for org in sorted(root.iterdir()):
        if not org.is_dir() or org.name.startswith("."):
          continue
        if _tmp_in_path(org):
          continue
        for repo in sorted(org.iterdir()):
          if not repo.is_dir():
            continue
          for rev in sorted(repo.iterdir()):
            if not rev.is_dir() or _tmp_in_path(rev):
              continue
            if rev.resolve() in found:
              continue
            has_w = any(rev.glob("*.gguf")) or any(rev.glob("*.safetensors")) or any(rev.glob("*.bin"))
            if has_w:
              found.add(rev.resolve())
    except OSError:
      pass

  return found


def _under_discovery_exclude_relpaths(mount: Path, model_dir: Path, prefixes: List[str]) -> bool:
  if not prefixes:
    return False
  try:
    rel = model_dir.relative_to(mount).as_posix()
  except ValueError:
    return False
  for pref in prefixes:
    p = pref.strip().strip("/")
    if not p:
      continue
    if rel == p or rel.startswith(p + "/"):
      return True
  return False


def _matches_tree_exclude(rel_from_root: str, patterns: List[str]) -> bool:
  """True if *rel_from_root* (relative to registry root, posix) matches an exclude pattern."""
  r = rel_from_root.strip().strip("/")
  if not r:
    return False
  for pat in patterns:
    p = (pat or "").strip().strip("/")
    if not p:
      continue
    if p.endswith("/**"):
      base = p[:-3].rstrip("/")
      if r == base or r.startswith(base + "/"):
        return True
      continue
    if any(ch in p for ch in "*?["):
      if fnmatch.fnmatch(r, p):
        return True
      continue
    if r == p or r.startswith(p + "/"):
      return True
  return False


def _tree_exclude_patterns_for_root(reg: Dict, root_relpath: str) -> List[str]:
  """Patterns are relative to the registry root directory (e.g. d5/)."""
  extra: List[str] = []
  for x in reg.get("tree_upload_exclude") or []:
    s = str(x).strip()
    if s:
      extra.append(s)
  r = root_relpath.strip().strip("/")
  if r == "d5" or r.startswith("d5/"):
    base = list(reg.get("d5_exclude") or [".tmp/**", "raw/**"])
    for q in ("quantized/**", "uncensored/**"):
      if q not in base:
        base.append(q)
    return base + extra
  return extra


def _tree_unit_conflicts_with_models(unit_rel: str, model_rels: Set[str]) -> bool:
  """True if any model revision path lies under this tree unit (per-model upload owns it)."""
  for m in model_rels:
    if m == unit_rel or m.startswith(unit_rel + "/"):
      return True
  return False


def discover_tree_upload_units(
  mount: Path,
  root_relpath: str,
  min_depth: int,
  exclude_patterns: List[str],
  model_rels: Set[str],
) -> List[Path]:
  """
  Non-overlapping directories to rclone as one job each.

  * Every directory exactly *min_depth* components below *root_relpath* becomes a unit,
    unless excluded or conflicting with a model revision path.
  * For each immediate child of the registry root with no such unit inside it,
    the child directory itself becomes one unit (covers e.g. d5/logs/).
  """
  root = (mount / root_relpath).resolve()
  if not root.is_dir() or min_depth < 1:
    return []

  deep: List[Path] = []
  try:
    for p in root.rglob("*"):
      if not p.is_dir():
        continue
      if _tmp_in_path(p):
        continue
      try:
        rel_from_root = p.relative_to(root).as_posix()
      except ValueError:
        continue
      if _matches_tree_exclude(rel_from_root, exclude_patterns):
        continue
      if len(p.relative_to(root).parts) != min_depth:
        continue
      rel_mount = p.relative_to(mount).as_posix()
      if _tree_unit_conflicts_with_models(rel_mount, model_rels):
        continue
      deep.append(p)
  except OSError:
    return []

  deep = sorted(set(deep))

  shallow: List[Path] = []
  try:
    children = sorted(x for x in root.iterdir() if x.is_dir() and not x.name.startswith("."))
  except OSError:
    children = []
  for c in children:
    if _tmp_in_path(c):
      continue
    try:
      crelp = c.relative_to(root).as_posix()
    except ValueError:
      continue
    if _matches_tree_exclude(crelp, exclude_patterns):
      continue
    rel_mount = c.relative_to(mount).as_posix()
    if _tree_unit_conflicts_with_models(rel_mount, model_rels):
      continue
    has_deep = any(c in d.parents or d == c for d in deep)
    if not has_deep:
      shallow.append(c)

  return sorted(set(deep + shallow))


def _d5_root_entry(roots: List[dict]) -> Optional[dict]:
  for r in roots:
    p = (r.get("path") or "").strip().strip("/")
    if p == "d5":
      return r
  return None


def _tree_min_depth_for_root(entry: dict) -> int:
  """0 = use legacy single full-tree sync for d5 only when caller handles it."""
  raw = entry.get("tree_upload_min_depth")
  if raw is None:
    return 3
  try:
    return max(0, int(raw))
  except (TypeError, ValueError):
    return 3


def collect_all_model_dirs(mount: Path, roots: List[dict], reg: Optional[Dict] = None) -> List[Path]:
  combined: Set[Path] = set()
  for item in roots:
    rel = (item.get("path") or "").strip().strip("/")
    if not rel:
      continue
    combined |= discover_model_dirs(mount, rel)
  prefixes: List[str] = []
  if reg:
    for ent in reg.get("d5_discovery_exclude_relpaths") or []:
      s = str(ent).strip().strip("/")
      if s:
        prefixes.append(s)
  if prefixes:
    combined = {p for p in combined if not _under_discovery_exclude_relpaths(mount, p, prefixes)}
  return sorted(combined)


def _estimate_model_dir_size_bytes(model_dir: Path) -> int:
  """
  Estimate model directory size for queue ordering.
  Prefer manifest.json (size_bytes sum) when present; fallback to recursive stat.
  """
  mf = model_dir / "manifest.json"
  if mf.is_file():
    try:
      doc = json.loads(mf.read_text(encoding="utf-8"))
      files = doc.get("files") or []
      total = 0
      for ent in files:
        if isinstance(ent, dict):
          total += int(ent.get("size_bytes", 0) or 0)
      if total > 0:
        return total
    except (json.JSONDecodeError, OSError, ValueError, TypeError):
      pass

  total = 0
  try:
    for p in model_dir.rglob("*"):
      if not p.is_file():
        continue
      if p.suffix in (".sha256", ".json"):
        continue
      total += p.stat().st_size
  except OSError:
    return 1 << 62
  return total


def parse_upload_log_for_registry(log_path: Path) -> Tuple[Set[str], Optional[str]]:
  """
  From uploaded.log: relpaths logged as registry-model or registry-tree, and latest
  UTC timestamp among those lines.
  """
  uploaded: Set[str] = set()
  last_ts: Optional[str] = None
  if not log_path.is_file():
    return uploaded, last_ts
  for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
    parts = line.split("\t")
    if len(parts) < 4:
      continue
    ts, kind, ident = parts[0], parts[1], parts[2]
    if kind in ("registry-model", TREE_UPLOAD_KIND):
      uploaded.add(ident)
      if last_ts is None or ts > last_ts:
        last_ts = ts
  return uploaded, last_ts


def parse_upload_log_last_d5_sync(log_path: Path) -> Optional[str]:
  """Latest timestamp for kind registry-d5 (full d5 tree copy)."""
  last: Optional[str] = None
  if not log_path.is_file():
    return last
  for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
    parts = line.split("\t")
    if len(parts) < 4:
      continue
    ts, kind = parts[0], parts[1]
    if kind == "registry-d5":
      if last is None or ts > last:
        last = ts
  return last


def _save_registry_upload_state(data: dict) -> None:
  data = dict(data)
  data["version"] = STATE_VERSION
  data["completed_models"] = sorted({str(x) for x in data.get("completed_models", []) if x})
  data["updated_at"] = _state_now_iso()
  REGISTRY_UPLOAD_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
  tmp = REGISTRY_UPLOAD_STATE_PATH.with_suffix(".json.tmp")
  with tmp.open("w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, sort_keys=True)
    f.write("\n")
  tmp.replace(REGISTRY_UPLOAD_STATE_PATH)


def load_registry_upload_state() -> dict:
  """
  Persistent tracker: model relpaths that finished verify + rclone OK.
  Later runs skip them entirely (no rclone / remote comparison) unless --resync-all.
  On first use, seed from uploaded.log (registry-model / registry-tree / registry-d5).
  """
  data: dict = {
    "version": STATE_VERSION,
    "completed_models": [],
    "d5_complete": False,
    "d5_completed_at": None,
    "updated_at": _state_now_iso(),
  }
  if REGISTRY_UPLOAD_STATE_PATH.is_file():
    try:
      raw = json.loads(REGISTRY_UPLOAD_STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
      raw = {}
    if isinstance(raw.get("completed_models"), list):
      data["completed_models"] = sorted({str(x) for x in raw["completed_models"] if x})
    data["d5_complete"] = bool(raw.get("d5_complete"))
    data["d5_completed_at"] = raw.get("d5_completed_at")
    return data

  uploaded, _ = parse_upload_log_for_registry(UPLOADED_LOG_PATH)
  data["completed_models"] = sorted(uploaded)
  # Legacy monolithic d5 line does not list per-folder paths; keep d5_complete for gate compat.
  d5_ts = parse_upload_log_last_d5_sync(UPLOADED_LOG_PATH)
  if d5_ts:
    data["d5_complete"] = True
    data["d5_completed_at"] = d5_ts
  _save_registry_upload_state(data)
  return data


def mark_registry_model_complete(state: dict, rel_pos: str) -> None:
  models: Set[str] = set(state.get("completed_models") or [])
  models.add(rel_pos)
  state["completed_models"] = sorted(models)
  _save_registry_upload_state(state)


def mark_registry_d5_complete(state: dict) -> None:
  state["d5_complete"] = True
  state["d5_completed_at"] = _state_now_iso()
  _save_registry_upload_state(state)


def write_registry_upload_status(cfg: Dict, reg: Dict) -> Path:
  """
  Refresh logs/GDRIVE-REGISTRY-UPLOAD-STATUS.md from gdrive-registry discovery + uploaded.log.
  Atomic write (tmp + replace).
  """
  mount = Path(cfg.get("models_mount", "/mnt/models")).resolve()
  roots = reg.get("roots") or []
  model_dirs = collect_all_model_dirs(mount, roots, reg)
  discovered: Set[str] = set()
  for md in model_dirs:
    try:
      discovered.add(md.relative_to(mount).as_posix())
    except ValueError:
      pass

  uploaded, last_model_ts = parse_upload_log_for_registry(UPLOADED_LOG_PATH)
  last_d5_ts = parse_upload_log_last_d5_sync(UPLOADED_LOG_PATH)
  tracker_models: Set[str] = set()
  tracker_d5 = False
  if REGISTRY_UPLOAD_STATE_PATH.is_file():
    try:
      tr = json.loads(REGISTRY_UPLOAD_STATE_PATH.read_text(encoding="utf-8"))
      if isinstance(tr.get("completed_models"), list):
        tracker_models = {str(x) for x in tr["completed_models"] if x}
      tracker_d5 = bool(tr.get("d5_complete"))
    except (json.JSONDecodeError, OSError):
      pass

  pending = sorted(discovered - uploaded)
  orphans = sorted(uploaded - discovered)
  on_disk_uploaded = discovered & uploaded
  verify_jsonl_lines = 0
  if VERIFY_JSONL.is_file():
    verify_jsonl_lines = sum(1 for ln in VERIFY_JSONL.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip())

  has_d5 = any((r.get("path") or "").strip().strip("/") == "d5" for r in roots)
  now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

  lines: List[str] = [
    "# GDrive registry upload status\n",
    "\n",
    f"_Generated: {now} (UTC) — discovery under `models_mount` + [`logs/uploaded.log`](uploaded.log) "
    f"(`registry-model` / `{TREE_UPLOAD_KIND}` / `registry-d5`)._\n",
    "\n",
    "## Summary\n",
    "\n",
    "| Item | Value |\n",
    "|------|-------|\n",
    f"| `models_mount` | `{mount}` |\n",
    f"| Model revision dirs discovered | {len(discovered)} |\n",
    f"| Uploaded at least once (in log ∩ on disk) | {len(on_disk_uploaded)} |\n",
    f"| Pending (on disk, not in log) | {len(pending)} |\n",
    f"| In log but path missing locally | {len(orphans)} |\n",
  ]
  lines.append(f"| Newest `registry-model` log timestamp | {last_model_ts or '—'} |\n")
  if has_d5:
    lines.append(f"| Last `registry-d5` (full `d5/` tree) log timestamp | {last_d5_ts or '— (not logged yet)'} |\n")
  lines.append(
    f"| **Tracker** (`registry-upload-state.json`): models marked uploaded (skip rclone) | {len(tracker_models)} |\n"
  )
  if has_d5:
    lines.append(f"| **Tracker**: `d5/` full tree marked complete | {'yes' if tracker_d5 else 'no'} |\n")
  lines.extend(
    [
      f"| Pre-upload verify failure lines (`gdrive-preupload-verify-failures.jsonl`) | {verify_jsonl_lines} |\n",
      "\n",
      "**Regenerate:** `python3 backup.py upload-registry-status` — also refreshed automatically at the end of each `backup-registry` run.\n",
      "\n",
    ]
  )

  if pending:
    lines.append("## Pending (not yet in uploaded.log)\n\n")
    for p in pending:
      lines.append(f"- `{p}`\n")
    lines.append("\n")
  elif not discovered:
    lines.append("## Pending\n\n*No revision dirs discovered — check `models_mount` and `gdrive-registry.yaml` roots.*\n\n")
  else:
    lines.append("## Pending\n\n*None — every discovered revision dir has a `registry-model` log line.*\n\n")

  lines.append("## Uploaded model dirs (present on disk + in log)\n\n")
  for p in sorted(on_disk_uploaded):
    lines.append(f"- `{p}`\n")
  if not on_disk_uploaded:
    lines.append("*None.*\n")
  lines.append("\n")

  if orphans:
    lines.append("## Logged but missing on disk\n\n")
    for p in orphans:
      lines.append(f"- `{p}`\n")
    lines.append("\n")

  lines.append("## Related logs\n\n")
  lines.append(f"- Pre-upload checksum skips: [`gdrive-preupload-verify-report.md`](gdrive-preupload-verify-report.md)\n")

  REGISTRY_UPLOAD_STATUS_MD.parent.mkdir(parents=True, exist_ok=True)
  tmp = REGISTRY_UPLOAD_STATUS_MD.with_suffix(".md.tmp")
  tmp.write_text("".join(lines), encoding="utf-8")
  tmp.replace(REGISTRY_UPLOAD_STATUS_MD)
  return REGISTRY_UPLOAD_STATUS_MD


def write_uploaded_models_catalog(cfg: Dict, reg: Dict) -> Tuple[Path, Path]:
  """
  Definitive uploaded list for capacity planning/deletion decisions.
  Source of truth: registry-upload-state.json completed_models.
  Enriched with discovered size and latest uploaded.log timestamp when present.
  """
  mount = Path(cfg.get("models_mount", "/mnt/models")).resolve()
  state = load_registry_upload_state()
  completed: List[str] = sorted({str(x) for x in state.get("completed_models", []) if x})

  # Build latest timestamp index from uploaded.log
  ts_by_rel: Dict[str, str] = {}
  if UPLOADED_LOG_PATH.is_file():
    for line in UPLOADED_LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
      parts = line.split("\t")
      if len(parts) < 4:
        continue
      ts, kind, rel = parts[0], parts[1], parts[2]
      if kind not in ("registry-model", TREE_UPLOAD_KIND):
        continue
      prev = ts_by_rel.get(rel)
      if prev is None or ts > prev:
        ts_by_rel[rel] = ts

  records: List[dict] = []
  total_bytes = 0
  for rel in completed:
    p = mount / rel
    exists = p.is_dir()
    size_bytes = _estimate_model_dir_size_bytes(p) if exists else None
    if isinstance(size_bytes, int) and size_bytes < (1 << 61):
      total_bytes += size_bytes
    rec = {
      "model_relpath": rel,
      "source_path": str(p),
      "source_exists": exists,
      "estimated_size_bytes": size_bytes if isinstance(size_bytes, int) and size_bytes < (1 << 61) else None,
      "uploaded_at_latest_utc": ts_by_rel.get(rel),
      "remote_path": f"models/{rel}",
    }
    records.append(rec)

  payload = {
    "generated_at_utc": _state_now_iso(),
    "models_mount": str(mount),
    "count": len(records),
    "total_estimated_size_bytes": total_bytes,
    "total_estimated_size_gib": round(total_bytes / (1024 ** 3), 3),
    "d5_complete": bool(state.get("d5_complete")),
    "d5_completed_at": state.get("d5_completed_at"),
    "models": records,
  }

  UPLOADED_MODELS_JSON.parent.mkdir(parents=True, exist_ok=True)
  tmp_json = UPLOADED_MODELS_JSON.with_suffix(".json.tmp")
  with tmp_json.open("w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2, sort_keys=True)
    f.write("\n")
  tmp_json.replace(UPLOADED_MODELS_JSON)

  lines: List[str] = [
    "# Registry Uploaded Models (definitive list)\n\n",
    f"_Generated: {payload['generated_at_utc']} (UTC)_\n\n",
    "| Item | Value |\n",
    "|------|-------|\n",
    f"| `models_mount` | `{mount}` |\n",
    f"| Uploaded model dirs (`registry-upload-state.json`) | {len(records)} |\n",
    f"| Total estimated size | {payload['total_estimated_size_gib']} GiB |\n",
    f"| `d5_complete` | {'yes' if payload['d5_complete'] else 'no'} |\n",
    f"| `d5_completed_at` | {payload['d5_completed_at'] or '—'} |\n",
    "\n",
    "Use this file for deletion planning. It lists paths confirmed uploaded by the registry tracker.\n\n",
    "## Models\n\n",
    "| model relpath | uploaded_at_latest_utc | estimated_size_gib | source_exists |\n",
    "|---|---:|---:|---:|\n",
  ]
  for r in records:
    gib = (r["estimated_size_bytes"] or 0) / (1024 ** 3)
    lines.append(
      f"| `{r['model_relpath']}` | {r['uploaded_at_latest_utc'] or '—'} | {gib:.3f} | {'yes' if r['source_exists'] else 'no'} |\n"
    )

  tmp_md = UPLOADED_MODELS_MD.with_suffix(".md.tmp")
  tmp_md.write_text("".join(lines), encoding="utf-8")
  tmp_md.replace(UPLOADED_MODELS_MD)
  return (UPLOADED_MODELS_JSON, UPLOADED_MODELS_MD)


def print_registry_plan(cfg: Dict, reg: Dict) -> None:
  mount = Path(cfg.get("models_mount", "/mnt/models")).resolve()
  roots = reg.get("roots") or []
  print(f"models_mount: {mount}")
  print(f"roots ({len(roots)}):")
  for r in roots:
    print(f"  - {r.get('path')}")
  model_dirs = collect_all_model_dirs(mount, roots, reg)
  print(f"\nmodel revision dirs discovered: {len(model_dirs)}")
  for p in model_dirs:
    try:
      print(f"  {p.relative_to(mount).as_posix()}")
    except ValueError:
      print(f"  {p}")
  has_d5 = any((r.get("path") or "").strip().strip("/") == "d5" for r in roots)
  if has_d5:
    de = _d5_root_entry(roots)
    td = _tree_min_depth_for_root(de) if de else 0
    excl = _tree_exclude_patterns_for_root(reg, "d5") if de else []
    mrels: Set[str] = set()
    for md in model_dirs:
      try:
        mrels.add(md.relative_to(mount).as_posix())
      except ValueError:
        pass
    if td > 0:
      tus = discover_tree_upload_units(mount, "d5", td, excl, mrels)
      print(f"\nd5 tree upload units (min_depth={td}): {len(tus)}")
      for p in tus:
        try:
          print(f"  {p.relative_to(mount).as_posix()}")
        except ValueError:
          print(f"  {p}")
    else:
      print("\n(d5 in registry: legacy full d5/ copy first, then per-model uploads)")


def _ensure_verify_report_header() -> None:
  VERIFY_MD.parent.mkdir(parents=True, exist_ok=True)
  if not VERIFY_MD.exists() or VERIFY_MD.stat().st_size == 0:
    VERIFY_MD.write_text(
      "# GDrive pre-upload checksum failures\n\n"
      "Models listed here **were not uploaded** (local SHA-256 did not match manifest / sidecars).\n\n"
      "- **Machine-readable (append):** `gdrive-preupload-verify-failures.jsonl` — one JSON object per failed file.\n"
      "- **This file:** append-only human summary.\n\n"
      "---\n",
      encoding="utf-8",
    )


def _append_verify_failure_report(mount: Path, model_dir: Path, results: List[dict]) -> None:
  bad = [r for r in results if not r.get("ok")]
  if not bad:
    return
  _ensure_verify_report_header()
  ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
  rel = model_dir.relative_to(mount).as_posix()
  with VERIFY_JSONL.open("a", encoding="utf-8") as jf:
    for r in bad:
      rec = {
        "ts": ts,
        "model_relpath": rel,
        "file": r.get("path"),
        "expected_sha256": r.get("expected"),
        "actual_sha256": r.get("actual"),
      }
      jf.write(json.dumps(rec, ensure_ascii=False) + "\n")
  with VERIFY_MD.open("a", encoding="utf-8") as mf:
    mf.write(f"\n## {ts} — `{rel}`\n\n")
    mf.write("| file | expected SHA-256 (prefix) | actual (prefix) |\n")
    mf.write("|------|---------------------------|----------------|\n")
    for r in bad:
      fp = str(r.get("path", "")).replace("|", "\\|")
      ex = (r.get("expected") or "")[:24]
      ac = (r.get("actual") or "")[:24]
      mf.write(f"| `{fp}` | `{ex}…` | `{ac}…` |\n")
    mf.write("\n")


def _local_verify_or_skip(
  archiver_root: Path,
  mount: Path,
  model_dir: Path,
  *,
  no_verify: bool,
) -> Tuple[bool, str]:
  """
  Returns (should_upload, reason_if_skip).
  should_upload False => model skipped; failure recorded in logs/gdrive-preupload-verify-*.
  """
  if no_verify:
    return (True, "")

  # Resolve verifier source path robustly for VM layouts.
  src_candidates = [
    archiver_root / "src",
    SCRIPT_DIR.parent / "local" / "src",
    SCRIPT_DIR.parent / "model-archiver" / "src",
  ]
  src = next((p for p in src_candidates if (p / "archiver" / "verifier.py").is_file()), None)
  if src is None:
    print(
      "[skip] verifier not found (checked: "
      + ", ".join(str(p) for p in src_candidates)
      + ") — refusing upload without integrity check",
      file=sys.stderr,
    )
    return (False, "verifier_unavailable")
  if str(src) not in sys.path:
    sys.path.insert(0, str(src))
  try:
    from archiver.verifier import verify_model_dir
  except ImportError as e:
    print(f"[skip] cannot import verifier ({e}) — refusing upload without integrity check", file=sys.stderr)
    return (False, "verifier_import_failed")

  try:
    results = verify_model_dir(model_dir)
  except Exception as e:
    # Some manifests are malformed (e.g. missing "files"). Treat as verify failure,
    # log it, and continue with the next model instead of crashing the whole run.
    _ensure_verify_report_header()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rel = model_dir.relative_to(mount).as_posix()
    with VERIFY_JSONL.open("a", encoding="utf-8") as jf:
      rec = {
        "ts": ts,
        "model_relpath": rel,
        "file": "manifest.json",
        "expected_sha256": None,
        "actual_sha256": None,
        "error": f"verify_exception: {type(e).__name__}: {e}",
      }
      jf.write(json.dumps(rec, ensure_ascii=False) + "\n")
    with VERIFY_MD.open("a", encoding="utf-8") as mf:
      mf.write(f"\n## {ts} — `{rel}`\n\n")
      mf.write("| file | expected SHA-256 (prefix) | actual (prefix) |\n")
      mf.write("|------|---------------------------|----------------|\n")
      mf.write("| `manifest.json` | `n/a` | `n/a` |\n\n")
      mf.write(f"- verifier error: `{type(e).__name__}: {e}`\n\n")
    return (False, "verify_exception")
  if not results:
    return (True, "")
  if all(r.get("ok") for r in results):
    return (True, "")
  _append_verify_failure_report(mount, model_dir, results)
  return (False, "checksum_verify_failed")


def run_rclone_copy_dir(
  src: Path,
  remote_dst: str,
  transfers: int,
  checkers: int,
  bwlimit: Optional[str],
  excludes: Optional[List[str]],
  dry_run: bool,
) -> bool:
  cmd = [
    "rclone",
    "copy",
    str(src),
    remote_dst,
    "--checksum",
    "--transfers",
    str(transfers),
    "--checkers",
    str(checkers),
    "--retries",
    "10",
    "--low-level-retries",
    "20",
  ]
  for pat in excludes or []:
    cmd.extend(["--exclude", pat])
  if bwlimit:
    cmd.extend(["--bwlimit", bwlimit])
  if dry_run:
    cmd.append("--dry-run")
  print(f"[rclone] {' '.join(cmd)}")
  import subprocess

  return subprocess.run(cmd).returncode == 0


def run_rclone_check_dir(
  src: Path,
  remote_dst: str,
  transfers: int,
  checkers: int,
  bwlimit: Optional[str],
  excludes: Optional[List[str]],
  dry_run: bool,
) -> bool:
  """
  Compare local tree to remote using checksums (Drive: remote hash metadata).
  Does not download file bodies from Drive; still reads local files to hash.
  --one-way: every file under src must exist on remote with matching hash.
  """
  cmd = [
    "rclone",
    "check",
    str(src),
    remote_dst,
    "--checksum",
    "--one-way",
    "--transfers",
    str(transfers),
    "--checkers",
    str(checkers),
    "--retries",
    "10",
    "--low-level-retries",
    "20",
  ]
  for pat in excludes or []:
    cmd.extend(["--exclude", pat])
  if bwlimit:
    cmd.extend(["--bwlimit", bwlimit])
  if dry_run:
    cmd.append("--dry-run")
  print(f"[rclone-check] {' '.join(cmd)}")
  import subprocess

  return subprocess.run(cmd).returncode == 0


def _drive_upload_priority(mount: Path, model_dir: Path) -> int:
  """0 = under d5/ (upload first); 1 = other drives."""
  try:
    rel = model_dir.relative_to(mount).as_posix()
  except ValueError:
    return 1
  return 0 if rel == "d5" or rel.startswith("d5/") else 1


def run_registry_upload(
  cfg: Dict,
  reg: Dict,
  *,
  archiver_root: Path,
  dry_run: bool,
  limit: Optional[int],
  no_verify: bool,
  resync_all: bool = False,
  verify_remote: bool = False,
) -> int:
  mount = Path(cfg.get("models_mount", "/mnt/models")).resolve()
  if not mount.is_dir():
    print(f"error: models_mount not found or not a directory: {mount}", file=sys.stderr)
    return 2

  roots = reg.get("roots") or []
  if not roots:
    print("error: gdrive-registry.yaml has no roots", file=sys.stderr)
    return 2

  g = cfg.get("gdrive") or {}
  remote = g.get("remote", "").rstrip("/")
  base_path = (g.get("base_path") or "").strip().strip("/")
  remote_base = f"{remote}/{base_path}" if base_path else remote
  models_prefix = f"{remote_base.rstrip('/')}/models"

  transfers = int(g.get("transfers", 1))
  checkers = int(g.get("checkers", 1))
  bwlimit = g.get("bwlimit")

  sys.path.insert(0, str(SCRIPT_DIR))
  try:
    from backup import log_upload_success
  except ImportError as e:
    print(f"error: cannot import backup helpers: {e}", file=sys.stderr)
    return 2

  state = load_registry_upload_state()
  completed: Set[str] = set(state.get("completed_models") or [])

  rclone_failures = 0
  verify_skipped = 0
  tracker_skipped = 0
  remote_check_ok = 0
  remote_check_fail = 0

  has_d5_root = any((r.get("path") or "").strip().strip("/") == "d5" for r in roots)
  d5_entry = _d5_root_entry(roots)
  d5_tree_depth = _tree_min_depth_for_root(d5_entry) if d5_entry else 0

  model_dirs = collect_all_model_dirs(mount, roots, reg)
  model_rels: Set[str] = set()
  for md in model_dirs:
    try:
      model_rels.add(md.relative_to(mount).as_posix())
    except ValueError:
      pass

  print(f"models_mount={mount}")
  print(f"remote_models={models_prefix}")
  if has_d5_root:
    if d5_tree_depth > 0:
      print(
        f"(policy) `d5/`: upload subtree units (tree_upload_min_depth={d5_tree_depth}) logged as "
        f"`{TREE_UPLOAD_KIND}`, full `d5/` gate check, then per-model + other roots."
      )
    else:
      print(
        "(policy) Sync full `d5/` tree to Drive first (legacy), verify on Drive, then upload "
        "other registry roots (per-model `d5/` dirs under raw/quantized use `registry-model`)."
      )

  # d5/ first: granular tree units OR single monolithic copy when tree_upload_min_depth: 0
  d5_full_tree_verified = False
  if has_d5_root:
    d5_src = mount / "d5"
    d5_dst = f"{models_prefix}/d5"
    excludes = reg.get("d5_exclude") or [".tmp/**"]
    if not d5_src.is_dir():
      print(f"error: registry includes `path: d5` but not a directory: {d5_src}", file=sys.stderr)
      return 2

    if d5_tree_depth > 0:
      excl = _tree_exclude_patterns_for_root(reg, "d5")
      tree_units = discover_tree_upload_units(mount, "d5", d5_tree_depth, excl, model_rels)
      print(f"\n--- d5 granular: {len(tree_units)} subtree unit(s) (excludes + model-dir overlap applied) ---")
      unit_excludes = [".tmp/**"]
      for i, unit in enumerate(tree_units, 1):
        try:
          rel_pos = unit.relative_to(mount).as_posix()
        except ValueError:
          print(f"[skip] tree unit not under mount: {unit}")
          continue
        dst = f"{models_prefix}/{rel_pos}"
        print(f"\n[d5-tree {i}/{len(tree_units)}] {rel_pos}")

        if not resync_all and rel_pos in completed:
          if verify_remote:
            tag = "[dry-run] " if dry_run else ""
            ok_chk = run_rclone_check_dir(
              unit, dst, transfers, checkers, bwlimit, unit_excludes, dry_run
            )
            if ok_chk:
              print(f"{tag}[ok] remote check passed — tree unit skip: {rel_pos}")
              remote_check_ok += 1
              tracker_skipped += 1
              continue
            print(f"{tag}[warn] remote check failed — re-upload tree unit: {rel_pos}")
            remote_check_fail += 1
          else:
            tag = "[dry-run] " if dry_run else ""
            print(f"{tag}[skip] tracker: tree unit already logged — {rel_pos}")
            tracker_skipped += 1
            continue

        ok = run_rclone_copy_dir(
          unit, dst, transfers, checkers, bwlimit, unit_excludes, dry_run
        )
        if not ok:
          print(f"[fail] rclone tree unit: {rel_pos}")
          rclone_failures += 1
        elif not dry_run:
          log_upload_success(rel_pos, str(unit.resolve()), kind=TREE_UPLOAD_KIND)
          mark_registry_model_complete(state, rel_pos)
          completed.add(rel_pos)

      print("\n--- verify full d5/ on Drive before other registry roots ---")
      tag = "[dry-run] " if dry_run else ""
      ok_gate = run_rclone_check_dir(
        d5_src, d5_dst, transfers, checkers, bwlimit, excludes, dry_run
      )
      if not ok_gate:
        print(
          f"{tag}[abort] d5/ one-way checksum check failed — not uploading d1/d2/d3 registry paths",
          file=sys.stderr,
        )
        return 1
      d5_full_tree_verified = True
      print(f"{tag}[ok] d5/ tree verified on Drive — proceeding with remaining registry roots")
      if not dry_run:
        mark_registry_d5_complete(state)
    else:
      print(f"\n--- (1/2) full d5 tree → {d5_dst} (excludes: {excludes}) ---")
      if not resync_all and state.get("d5_complete"):
        if verify_remote:
          tag = "[dry-run] " if dry_run else ""
          ok_chk = run_rclone_check_dir(
            d5_src, d5_dst, transfers, checkers, bwlimit, excludes, dry_run
          )
          if ok_chk:
            print(f"{tag}[ok] remote check passed — d5/ tracker skip confirmed")
            remote_check_ok += 1
            tracker_skipped += 1
          else:
            print(f"{tag}[warn] remote check failed — re-syncing d5/")
            remote_check_fail += 1
            ok = run_rclone_copy_dir(
              d5_src, d5_dst, transfers, checkers, bwlimit, excludes, dry_run
            )
            if not ok:
              rclone_failures += 1
            elif not dry_run:
              log_upload_success("d5/", str(d5_src.resolve()), kind="registry-d5")
              mark_registry_d5_complete(state)
        else:
          tag = "[dry-run] " if dry_run else ""
          print(
            f"{tag}[skip] tracker: d5/ already marked complete — no rclone (gate still verifies below)"
          )
          tracker_skipped += 1
      else:
        ok = run_rclone_copy_dir(
          d5_src, d5_dst, transfers, checkers, bwlimit, excludes, dry_run
        )
        if not ok:
          rclone_failures += 1
        elif not dry_run:
          log_upload_success("d5/", str(d5_src.resolve()), kind="registry-d5")
          mark_registry_d5_complete(state)

      print("\n--- (2/2) verify d5/ on Drive before other registry roots ---")
      tag = "[dry-run] " if dry_run else ""
      ok_gate = run_rclone_check_dir(
        d5_src, d5_dst, transfers, checkers, bwlimit, excludes, dry_run
      )
      if not ok_gate:
        print(
          f"{tag}[abort] d5/ one-way checksum check failed — not uploading d1/d2/d3 registry paths",
          file=sys.stderr,
        )
        return 1
      d5_full_tree_verified = True
      print(f"{tag}[ok] d5/ tree verified on Drive — proceeding with remaining registry roots")

  model_dirs = sorted(
    model_dirs,
    key=lambda p: (
      _drive_upload_priority(mount, p),
      _estimate_model_dir_size_bytes(p),
      p.relative_to(mount).as_posix() if p.is_relative_to(mount) else str(p),
    ),
  )
  if limit is not None:
    model_dirs = model_dirs[:limit]

  print(f"model revision dirs to process: {len(model_dirs)}")
  if resync_all:
    print("resync-all: tracker ignored — every dir will verify + rclone (or dry-run)")
  else:
    print(
      f"tracker: {len(completed)} model dir(s) marked complete → skip rclone "
      f"(`{REGISTRY_UPLOAD_STATE_PATH.name}`); use --resync-all to force full re-upload"
    )
  if verify_remote:
    print(
      "verify-remote: tracker-skipped dirs will run `rclone check --checksum --one-way` "
      "(local read + remote metadata; no full Drive download); mismatch → re-upload"
    )
  if dry_run and not model_dirs:
    print("(dry-run: no model dirs found — check paths)")

  for i, md in enumerate(model_dirs, 1):
    try:
      rel = md.relative_to(mount)
    except ValueError:
      print(f"[skip] not under mount: {md}")
      continue
    rel_pos = rel.as_posix()
    dst = f"{models_prefix}/{rel_pos}"
    print(f"\n[{i}/{len(model_dirs)}] {rel_pos}")

    if not resync_all and rel_pos in completed:
      if verify_remote:
        tag = "[dry-run] " if dry_run else ""
        ok_chk = run_rclone_check_dir(md, dst, transfers, checkers, bwlimit, None, dry_run)
        if ok_chk:
          print(f"{tag}[ok] remote check passed — tracker skip confirmed: {rel_pos}")
          remote_check_ok += 1
          tracker_skipped += 1
          continue
        print(f"{tag}[warn] remote check failed — will verify locally and re-upload: {rel_pos}")
        remote_check_fail += 1
      else:
        tag = "[dry-run] " if dry_run else ""
        print(f"{tag}[skip] tracker: already uploaded — no rclone ({REGISTRY_UPLOAD_STATE_PATH.name})")
        tracker_skipped += 1
        continue

    ok_verify, _ = _local_verify_or_skip(archiver_root, mount, md, no_verify=no_verify)
    if not ok_verify:
      print(f"[skip] pre-upload checksum failed — not uploading (logged): {rel_pos}")
      verify_skipped += 1
      continue

    ok = run_rclone_copy_dir(md, dst, transfers, checkers, bwlimit, None, dry_run)
    if not ok:
      print(f"[fail] rclone: {rel_pos}")
      rclone_failures += 1
    elif not dry_run:
      log_upload_success(rel_pos, str(md), kind="registry-model")
      mark_registry_model_complete(state, rel_pos)
      completed.add(rel_pos)

  try:
    path = write_registry_upload_status(cfg, reg)
    print(f"[status] {path.relative_to(SCRIPT_DIR)}")
  except OSError as e:
    print(f"[warn] could not write registry upload status: {e}", file=sys.stderr)
  try:
    p_json, p_md = write_uploaded_models_catalog(cfg, reg)
    print(f"[uploaded-list] {p_json.relative_to(SCRIPT_DIR)}")
    print(f"[uploaded-list] {p_md.relative_to(SCRIPT_DIR)}")
  except OSError as e:
    print(f"[warn] could not write uploaded models catalog: {e}", file=sys.stderr)

  if verify_remote and (remote_check_ok or remote_check_fail):
    print(
      f"\n[summary] remote verify (`rclone check`): passed={remote_check_ok}, "
      f"mismatch→re-upload path={remote_check_fail}",
      file=sys.stderr,
    )
  if tracker_skipped:
    if verify_remote:
      print(
        f"\n[summary] {tracker_skipped} dir(s) left unchanged after remote check OK "
        f"(tracker + verify-remote). State: {REGISTRY_UPLOAD_STATE_PATH.name}",
        file=sys.stderr,
      )
    else:
      print(
        f"\n[summary] {tracker_skipped} skip(s) via local tracker (no rclone). "
        f"State: {REGISTRY_UPLOAD_STATE_PATH.name}",
        file=sys.stderr,
      )
  if verify_skipped:
    print(
      f"\n[summary] {verify_skipped} model dir(s) skipped (pre-upload checksum). "
      f"See {VERIFY_MD.name} and {VERIFY_JSONL.name}",
      file=sys.stderr,
    )
  if rclone_failures:
    print(f"\ndone with {rclone_failures} rclone failure(s)", file=sys.stderr)
    return 1
  print("\ndone")
  return 0


def main() -> int:
  parser = argparse.ArgumentParser(description="GDrive upload from gdrive-registry.yaml")
  parser.add_argument("--config", type=Path, default=CONFIG_PATH)
  parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
  parser.add_argument("--dry-run", action="store_true")
  parser.add_argument("--limit", type=int, default=None, help="Process only first N model dirs")
  parser.add_argument("--no-verify", action="store_true", help="Skip local SHA verify (not recommended)")
  parser.add_argument(
    "--resync-all",
    action="store_true",
    help="Ignore registry-upload-state.json; verify + rclone every model dir (and d5 if in registry).",
  )
  parser.add_argument(
    "--verify-remote",
    action="store_true",
    help="For tracker-skipped dirs, run rclone check (checksum, one-way) vs Drive before skipping.",
  )
  parser.add_argument(
    "--no-verify-remote",
    action="store_true",
    help="Disable remote check even if gdrive.registry_verify_remote is true in config.",
  )
  args = parser.parse_args()

  cfg = load_yaml(args.config)
  reg = load_yaml(args.registry)
  archiver_root = Path(cfg.get("archiver_root", SCRIPT_DIR.parent / "local")).resolve()
  g = cfg.get("gdrive") or {}
  want_remote = bool(args.verify_remote or g.get("registry_verify_remote") or cfg.get("registry_verify_remote"))
  verify_remote = want_remote and not args.no_verify_remote

  return run_registry_upload(
    cfg,
    reg,
    archiver_root=archiver_root,
    dry_run=args.dry_run,
    limit=args.limit,
    no_verify=args.no_verify,
    resync_all=args.resync_all,
    verify_remote=verify_remote,
  )


if __name__ == "__main__":
  raise SystemExit(main())
