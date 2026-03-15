#!/usr/bin/env python3
import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml


CONFIG_PATH = Path(__file__).with_name("config.yaml")
STATE_PATH = Path(__file__).with_name("state.json")
TIER_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6}


@dataclass
class DriveConfig:
  name: str
  mount_point: str


@dataclass
class ModelEntry:
  model_id: str
  hf_repo: str
  drive: str
  tier: str = "A"
  commit_sha: Optional[str] = None


def load_yaml(path: Path):
  with path.open("r") as f:
    return yaml.safe_load(f)


def load_state() -> Dict:
  if not STATE_PATH.exists():
    return {"models": {}, "paths": {}}
  with STATE_PATH.open("r") as f:
    return json.load(f)


def save_state(state: Dict):
  tmp = STATE_PATH.with_suffix(".tmp")
  with tmp.open("w") as f:
    json.dump(state, f, indent=2, sort_keys=True)
  tmp.replace(STATE_PATH)


def load_drives(archiver_root: Path) -> Dict[str, DriveConfig]:
  cfg = load_yaml(archiver_root / "config" / "drives.yaml")
  drives: Dict[str, DriveConfig] = {}
  for name, d in cfg.items():
    mount = d.get("mount_point")
    if not mount:
      continue
    drives[name] = DriveConfig(name=name, mount_point=mount)
  return drives


def load_registry(archiver_root: Path) -> Dict[str, ModelEntry]:
  reg = load_yaml(archiver_root / "config" / "registry.yaml")
  out: Dict[str, ModelEntry] = {}
  for m in reg.get("models", []):
    mid = m.get("id")
    if not mid:
      continue
    out[mid] = ModelEntry(
      model_id=mid,
      hf_repo=m.get("hf_repo", mid),
      drive=m.get("drive"),
      tier=m.get("tier", "A"),
      commit_sha=m.get("commit_sha"),
    )
  return out


def _content_subdir(tier: str) -> str:
  if tier == "C":
    return "quantized"
  if tier == "D":
    return "uncensored"
  return "raw"


def resolve_model_path(entry: ModelEntry, drives: Dict[str, DriveConfig]) -> Optional[Path]:
  d = drives.get(entry.drive)
  if not d:
    return None
  subdir = _content_subdir(entry.tier)
  rev = entry.commit_sha or "main"
  org, name = entry.hf_repo.split("/", 1)
  return Path(d.mount_point) / subdir / org / name / rev


def load_archiver_run_state(path: Path) -> Dict:
  """Load archiver run_state.json (has status, total_bytes per model)."""
  if not path.exists():
    return {"models": {}}
  with path.open("r") as f:
    return json.load(f)


def is_gguf(entry: ModelEntry) -> bool:
  """True if this registry entry is a GGUF/quantized model."""
  if entry.tier == "C":
    return True
  if "GGUF" in entry.model_id or "gguf" in entry.hf_repo.lower():
    return True
  return False


def compute_upload_lists(
  cfg: Dict,
  archiver_root: Path,
  run_state_path: Path,
  drives_allow: List[str],
  max_total_gb: float,
  max_per_model_gb: float,
) -> Tuple[List[str], List[str]]:
  """
  Build gguf_ids and full_ids from registry + run_state that fit within budget.
  Only includes models on allowed drives, status complete, with known size <= max_per_model_gb.
  """
  registry = load_registry(archiver_root)
  run_state = load_archiver_run_state(run_state_path)
  models_state = run_state.get("models", {})

  max_total_bytes = int(max_total_gb * 1024**3)
  max_per_bytes = int(max_per_model_gb * 1024**3)

  # (model_id, size_bytes, is_gguf)
  candidates: List[Tuple[str, int, bool]] = []
  for mid, entry in registry.items():
    if entry.drive not in drives_allow:
      continue
    ms = models_state.get(mid, {})
    if ms.get("status") != "complete":
      continue
    total = ms.get("total_bytes") or 0
    if total <= 0 or total > max_per_bytes:
      continue
    candidates.append((mid, total, is_gguf(entry)))

  # Sort: tier (A first), then priority (1 first), then size ascending (smaller first)
  reg_raw = load_yaml(archiver_root / "config" / "registry.yaml")
  reg_models = reg_raw.get("models", [])

  def sort_key(item: Tuple[str, int, bool]) -> Tuple[int, int, int]:
    mid, size, _ = item
    entry = registry[mid]
    tier_rank = TIER_ORDER.get(entry.tier, 99)
    raw = next((m for m in reg_models if m.get("id") == mid), {})
    priority = raw.get("priority", 1)
    return (tier_rank, priority, size)

  candidates.sort(key=sort_key)

  gguf_ids: List[str] = []
  full_ids: List[str] = []
  total_bytes = 0
  for mid, size, is_g in candidates:
    if total_bytes + size > max_total_bytes:
      break
    total_bytes += size
    if is_g:
      gguf_ids.append(mid)
    else:
      full_ids.append(mid)

  return (gguf_ids, full_ids)


def get_model_ids_for_backup(cfg: Dict, archiver_root: Path, kind: str) -> List[str]:
  """Return list of model IDs to backup: from upload_selection or explicit model_ids_*."""
  sel = cfg.get("upload_selection")
  if sel:
    run_state_path = Path(sel.get("run_state_path", "/mnt/models/d5/run_state.json"))
    drives = sel.get("drives", ["d2", "d3"])
    max_total_gb = float(sel.get("max_total_gb", 3000))
    max_per_gb = float(sel.get("max_per_model_gb", 200))
    gguf_ids, full_ids = compute_upload_lists(
      cfg, archiver_root, run_state_path, drives, max_total_gb, max_per_gb
    )
    return gguf_ids if kind == "gguf" else full_ids
  key = "model_ids_gguf" if kind == "gguf" else "model_ids_full"
  return cfg.get(key, []) or []


def filter_downloaded(
  ids: List[str],
  registry: Dict[str, ModelEntry],
  drives: Dict[str, DriveConfig],
  run_state_path: Optional[Path] = None,
) -> List[str]:
  """
  Return only model IDs that are downloaded: path exists and, when run_state is
  available, status is complete. Skips in_progress, failed, and path-missing.
  """
  run_state = load_archiver_run_state(run_state_path) if run_state_path else {"models": {}}
  models_state = run_state.get("models", {})
  out: List[str] = []
  for mid in ids:
    entry = registry.get(mid)
    if not entry:
      continue
    src = resolve_model_path(entry, drives)
    if not src or not src.exists():
      continue
    if run_state_path and run_state_path.exists():
      if models_state.get(mid, {}).get("status") != "complete":
        continue
    out.append(mid)
  return out


def remote_path_has_files(remote_path: str) -> bool:
  """Return True if the remote path exists and contains at least one file (idempotent skip)."""
  cmd = ["rclone", "lsf", remote_path.rstrip("/"), "--max-depth", "1"]
  result = subprocess.run(cmd, capture_output=True, text=True)
  if result.returncode != 0:
    return False
  return bool(result.stdout.strip())


def run_rclone_copy(
  src: Path,
  remote_base: str,
  rel_dest: str,
  bwlimit: Optional[str] = None,
  transfers: int = 1,
  checkers: int = 1,
) -> bool:
  dst = f"{remote_base.rstrip('/')}/{rel_dest}"
  cmd = [
    "rclone",
    "copy",
    str(src),
    dst,
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
  if bwlimit:
    cmd.extend(["--bwlimit", bwlimit])
  print(f"[rclone] {' '.join(cmd)}")
  result = subprocess.run(cmd)
  return result.returncode == 0


def backup_models(cfg: Dict, archiver_root: Path, kind: str):
  drives = load_drives(archiver_root)
  registry = load_registry(archiver_root)
  state = load_state()

  remote = cfg["gdrive"]["remote"]
  base_path = cfg["gdrive"].get("base_path", "").strip()
  remote_base = f"{remote}/{base_path}" if base_path else remote

  planned: List[str] = get_model_ids_for_backup(cfg, archiver_root, kind)
  run_state_path = Path(
    cfg.get("upload_selection", {}).get("run_state_path", "/mnt/models/d5/run_state.json")
  )
  ids = filter_downloaded(planned, registry, drives, run_state_path)
  skipped = len(planned) - len(ids)
  if skipped:
    print(f"[skip] {skipped} model(s) not downloaded (path missing or not complete) — uploading {len(ids)}")
  if not ids:
    print("No downloaded models to upload for this set.")
    return

  for mid in ids:
    entry = registry.get(mid)
    if not entry:
      print(f"[skip] {mid}: not in registry.yaml")
      continue

    src = resolve_model_path(entry, drives)
    if not src or not src.exists():
      print(f"[skip] {mid}: path not found ({src})")
      continue

    st_models = state.setdefault("models", {})
    st_entry = st_models.get(mid, {})

    rel_dest = f"models/{mid.replace('/', '--')}"
    dst = f"{remote_base.rstrip('/')}/{rel_dest}"

    if st_entry.get("source_path") == str(src) and st_entry.get("backed_up", False):
      print(f"[ok] {mid}: already backed up from {src}")
      continue
    if remote_path_has_files(dst):
      print(f"[ok] {mid}: already on drive (skipping)")
      st_models[mid] = {"source_path": str(src), "backed_up": True}
      save_state(state)
      continue

    g = cfg["gdrive"]
    bwlimit = g.get("bwlimit")
    transfers = g.get("transfers", 1)
    checkers = g.get("checkers", 1)
    ok = run_rclone_copy(src, remote_base, rel_dest, bwlimit=bwlimit, transfers=transfers, checkers=checkers)
    if ok:
      st_models[mid] = {
        "source_path": str(src),
        "backed_up": True,
      }
      save_state(state)
    else:
      print(f"[err] {mid}: backup failed")


def _slug_for_dir(path: Path) -> str:
  """Stable GDrive subdir name from a model directory path (e.g. org/name/rev -> org--name--rev)."""
  parts = path.resolve().parts
  if len(parts) >= 3:
    return "--".join(parts[-3:])
  return path.name or "unknown"


def backup_dirs(
  cfg: Dict,
  paths: List[Path],
  from_file: Optional[Path] = None,
) -> None:
  """
  Upload an arbitrary set of model directories to GDrive. Idempotent: skips dirs
  already recorded in state. Paths can be given as arguments or one per line in --from-file.
  """
  if from_file:
    if not from_file.exists():
      print(f"[err] --from-file not found: {from_file}")
      return
    paths = [Path(line.strip()) for line in from_file.read_text().splitlines() if line.strip()]
  else:
    paths = [Path(p) for p in paths]

  if not paths:
    print("No paths to upload. Pass directory paths or use --from-file.")
    return

  state = load_state()
  st_dirs = state.setdefault("dirs", {})
  remote = cfg["gdrive"]["remote"]
  base_path = cfg["gdrive"].get("base_path", "").strip()
  remote_base = f"{remote}/{base_path}" if base_path else remote
  bwlimit = cfg["gdrive"].get("bwlimit")

  for src in paths:
    src = src.resolve()
    if not src.is_dir():
      print(f"[skip] {src}: not a directory")
      continue

    key = str(src)
    if st_dirs.get(key, {}).get("backed_up", False):
      print(f"[ok] {src}: already backed up")
      continue

    rel_dest = f"models/{_slug_for_dir(src)}"
    dst = f"{remote_base.rstrip('/')}/{rel_dest}"
    if remote_path_has_files(dst):
      print(f"[ok] {src}: already on drive (skipping)")
      st_dirs[key] = {"source_path": key, "backed_up": True}
      save_state(state)
      continue

    g = cfg["gdrive"]
    ok = run_rclone_copy(
      src, remote_base, rel_dest,
      bwlimit=g.get("bwlimit"),
      transfers=g.get("transfers", 1),
      checkers=g.get("checkers", 1),
    )
    if ok:
      st_dirs[key] = {"source_path": key, "backed_up": True}
      save_state(state)
    else:
      print(f"[err] {src}: backup failed")


def _normalize_extra_path(p: object) -> Tuple[Path, str]:
  """Return (source path, remote rel_dest e.g. extra/name)."""
  if isinstance(p, dict):
    src = Path(p["path"])
    rel = (p.get("dest") or f"extra/{src.name}").strip()
    return (src, rel if rel.startswith("extra/") else f"extra/{rel}")
  src = Path(p)
  return (src, f"extra/{src.name}")


def backup_extra_paths(cfg: Dict):
  state = load_state()
  remote = cfg["gdrive"]["remote"]
  base_path = cfg["gdrive"].get("base_path", "").strip()
  remote_base = f"{remote}/{base_path}" if base_path else remote
  st_paths = state.setdefault("paths", {})

  for p in cfg.get("extra_paths", []):
    src, rel_dest = _normalize_extra_path(p)
    if not src.exists():
      print(f"[skip] extra {src}: not found")
      continue

    if st_paths.get(str(src), {}).get("backed_up", False):
      print(f"[ok] extra {src}: already backed up")
      continue

    dst = f"{remote_base.rstrip('/')}/{rel_dest}"
    if remote_path_has_files(dst):
      print(f"[ok] extra {src}: already on drive (skipping)")
      st_paths[str(src)] = {"backed_up": True}
      save_state(state)
      continue

    g = cfg["gdrive"]
    ok = run_rclone_copy(
      src, remote_base, rel_dest,
      bwlimit=g.get("bwlimit"),
      transfers=g.get("transfers", 1),
      checkers=g.get("checkers", 1),
    )
    if ok:
      st_paths[str(src)] = {"backed_up": True}
      save_state(state)
    else:
      print(f"[err] extra {src}: backup failed")


def backup_extra_paths_refresh(cfg: Dict):
  """Force-upload extra_paths: ignore local state and remote presence.

  rclone still uses --checksum, so unchanged files are not re-transferred,
  but any changed metadata or new files will be synced.
  """
  remote = cfg["gdrive"]["remote"]
  base_path = cfg["gdrive"].get("base_path", "").strip()
  remote_base = f"{remote}/{base_path}" if base_path else remote

  for p in cfg.get("extra_paths", []):
    src, rel_dest = _normalize_extra_path(p)
    if not src.exists():
      print(f"[skip] extra {src}: not found")
      continue

    g = cfg["gdrive"]
    ok = run_rclone_copy(
      src, remote_base, rel_dest,
      bwlimit=g.get("bwlimit"),
      transfers=g.get("transfers", 1),
      checkers=g.get("checkers", 1),
    )
    if not ok:
      print(f"[err] extra {src}: refresh backup failed")


def list_candidates(cfg: Dict, archiver_root: Path) -> None:
  """Print which models would be uploaded (dry-run). Uses upload_selection if set."""
  sel = cfg.get("upload_selection")
  if not sel:
    gguf_ids = cfg.get("model_ids_gguf", []) or []
    full_ids = cfg.get("model_ids_full", []) or []
    print("Using explicit model_ids_gguf / model_ids_full (no upload_selection).")
    print(f"  GGUF: {len(gguf_ids)} models")
    print(f"  Full: {len(full_ids)} models")
    for mid in gguf_ids:
      print(f"    gguf  {mid}")
    for mid in full_ids:
      print(f"    full {mid}")
    return

  run_state_path = Path(sel.get("run_state_path", "/mnt/models/d5/run_state.json"))
  drives = sel.get("drives", ["d2", "d3"])
  max_total_gb = float(sel.get("max_total_gb", 3000))
  max_per_gb = float(sel.get("max_per_model_gb", 200))
  gguf_ids, full_ids = compute_upload_lists(
    cfg, archiver_root, run_state_path, drives, max_total_gb, max_per_gb
  )

  run_state = load_archiver_run_state(run_state_path)
  models_state = run_state.get("models", {})
  total_gguf = sum(models_state.get(mid, {}).get("total_bytes", 0) for mid in gguf_ids)
  total_full = sum(models_state.get(mid, {}).get("total_bytes", 0) for mid in full_ids)
  total_gb = (total_gguf + total_full) / 1024**3

  print(f"Upload selection: drives={drives}, max_total_gb={max_total_gb}, max_per_model_gb={max_per_gb}")
  print(f"  GGUF: {len(gguf_ids)} models, {total_gguf / 1024**3:.1f} GB")
  print(f"  Full: {len(full_ids)} models, {total_full / 1024**3:.1f} GB")
  print(f"  Total: {total_gb:.1f} GB")
  for mid in gguf_ids:
    b = models_state.get(mid, {}).get("total_bytes", 0)
    print(f"    gguf  {mid}  ({b / 1024**3:.1f} GB)")
  for mid in full_ids:
    b = models_state.get(mid, {}).get("total_bytes", 0)
    print(f"    full {mid}  ({b / 1024**3:.1f} GB)")


def compare_with_archiver(cfg: Dict, archiver_root: Path) -> None:
  """
  Compare planned GDrive upload set with model archival registry and run_state.
  Reports: planned count, in registry, already downloaded (complete), path exists.
  """
  registry = load_registry(archiver_root)
  registry_ids = set(registry.keys())

  sel = cfg.get("upload_selection")
  if sel:
    run_state_path = Path(sel.get("run_state_path", "/mnt/models/d5/run_state.json"))
    drives = sel.get("drives", ["d2", "d3"])
    max_total_gb = float(sel.get("max_total_gb", 3000))
    max_per_gb = float(sel.get("max_per_model_gb", 200))
    gguf_ids, full_ids = compute_upload_lists(
      cfg, archiver_root, run_state_path, drives, max_total_gb, max_per_gb
    )
    planned_ids = set(gguf_ids) | set(full_ids)
    selection_note = f"upload_selection (drives={drives}, max_total_gb={max_total_gb})"
  else:
    gguf_ids = cfg.get("model_ids_gguf", []) or []
    full_ids = cfg.get("model_ids_full", []) or []
    planned_ids = set(gguf_ids) | set(full_ids)
    run_state_path = Path("/mnt/models/d5/run_state.json")
    selection_note = "explicit model_ids_gguf / model_ids_full"

  run_state = load_archiver_run_state(run_state_path)
  models_state = run_state.get("models", {})
  drives = load_drives(archiver_root)

  in_registry = planned_ids & registry_ids
  not_in_registry = planned_ids - registry_ids
  complete = {mid for mid in planned_ids if models_state.get(mid, {}).get("status") == "complete"}
  not_downloaded = planned_ids - complete

  # Path exists (for in-registry only)
  path_exists = set()
  for mid in in_registry:
    entry = registry[mid]
    path = resolve_model_path(entry, drives)
    if path and path.exists():
      path_exists.add(mid)

  print("GDrive planned upload vs archiver")
  print("=" * 60)
  print(f"Selection: {selection_note}")
  print(f"Registry (registry.yaml): {len(registry_ids)} models total")
  print()
  print(f"Planned for GDrive upload: {len(planned_ids)} models")
  print(f"  In registry:            {len(in_registry)}")
  print(f"  Not in registry:        {len(not_in_registry)}")
  print(f"  Already downloaded:     {len(complete)} (run_state status=complete)")
  print(f"  Not yet downloaded:     {len(not_downloaded)}")
  print(f"  Path exists on disk:    {len(path_exists)} (of those in registry)")
  print()
  if not_in_registry:
    print("Planned but not in registry (will be skipped by backup):")
    for mid in sorted(not_in_registry):
      print(f"  - {mid}")
  if not_downloaded and run_state_path.exists():
    print("Planned but not yet downloaded (run_state not complete):")
    for mid in sorted(not_downloaded)[:20]:
      print(f"  - {mid}")
    if len(not_downloaded) > 20:
      print(f"  ... and {len(not_downloaded) - 20} more")
  if not run_state_path.exists():
    print(f"Note: run_state not found at {run_state_path} (cannot report downloaded count).")


def main():
  parser = argparse.ArgumentParser(description="Survivor backup to Google Drive using rclone.")
  sub = parser.add_subparsers(dest="cmd", required=True)

  sub.add_parser("backup-gguf")
  sub.add_parser("backup-full")
  sub.add_parser("backup-extra")
  sub.add_parser("backup-extra-refresh", help="Force-upload extra_paths even if already backed up.")
  sub.add_parser("backup-extra-if-pending", help="Run backup-extra if metadata_pending_path exists, then clear it.")
  sub.add_parser("backup-all")
  sub.add_parser("list-candidates")
  sub.add_parser("compare-with-archiver")
  p_dirs = sub.add_parser("backup-dirs", help="Upload arbitrary model directories (paths or --from-file).")
  p_dirs.add_argument("paths", nargs="*", help="Directory paths to upload.")
  p_dirs.add_argument("--from-file", type=Path, metavar="FILE", help="File with one directory path per line.")

  args = parser.parse_args()

  cfg = load_yaml(CONFIG_PATH)
  archiver_root = Path(cfg["archiver_root"])

  if args.cmd == "backup-gguf":
    backup_models(cfg, archiver_root, kind="gguf")
  elif args.cmd == "backup-full":
    backup_models(cfg, archiver_root, kind="full")
  elif args.cmd == "backup-extra":
    backup_extra_paths(cfg)
  elif args.cmd == "backup-extra-refresh":
    backup_extra_paths_refresh(cfg)
  elif args.cmd == "backup-extra-if-pending":
    pending_path = cfg.get("metadata_pending_path")
    if not pending_path:
      print("metadata_pending_path not set in config; skipping.")
    else:
      path = Path(pending_path)
      if path.exists():
        backup_extra_paths(cfg)
        try:
          path.unlink()
        except OSError as e:
          print(f"[warn] could not remove {path}: {e}")
      else:
        print("No pending metadata upload (sentinel not present).")
  elif args.cmd == "backup-all":
    backup_models(cfg, archiver_root, kind="gguf")
    backup_models(cfg, archiver_root, kind="full")
    backup_extra_paths(cfg)
  elif args.cmd == "list-candidates":
    list_candidates(cfg, archiver_root)
  elif args.cmd == "compare-with-archiver":
    compare_with_archiver(cfg, archiver_root)
  elif args.cmd == "backup-dirs":
    backup_dirs(cfg, getattr(args, "paths", []) or [], getattr(args, "from_file", None))


if __name__ == "__main__":
  main()

