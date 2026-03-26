#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml


CONFIG_PATH = Path(__file__).with_name("config.yaml")
STATE_PATH = Path(__file__).with_name("state.json")
UPLOADED_LOG_PATH = Path(__file__).with_name("logs") / "uploaded.log"
TIER_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6}

# GDrive budget fill order: lower rank = chosen earlier. See UPLOAD-SELECTION.md.
DISAPPEARING_RE = re.compile(
  r"takedown|\bdmca\b|re-?host|at\s+risk|may\s+disappear|preservation\s+priority|"
  r"community\s+mirror|fork-only|unofficial\s+mirror",
  re.I,
)
ABLIT_UNCENSOR_RE = re.compile(
  r"ablitr|uncensor|uncensored|unaligned|\bdolphin\b|mlabonne|tensorblock|huihui|"
  r"rombod|fingu|failspy|combinhorizon|wizard.*vicuna|uncens",
  re.I,
)
HOSTABLE_MAX_BYTES = 50 * 1024**3


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


def verify_model_dir_before_upload(archiver_root: Path, src: Path) -> bool:
  """
  Verify all files in src against manifest.json or .sha256 sidecars (archiver semantics).
  Returns True if all checks pass (or there are no files to verify); False if any fail.
  """
  archiver_src = archiver_root / "src"
  if not archiver_src.is_dir():
    return True  # no archiver tree — skip verification
  if str(archiver_src) not in sys.path:
    sys.path.insert(0, str(archiver_src))
  try:
    from archiver.verifier import verify_model_dir
  except ImportError:
    return True  # archiver not available — skip verification
  results = verify_model_dir(src)
  if not results:
    return True
  return all(r.get("ok", False) for r in results)


def log_upload_success(identifier: str, source_path: str, kind: str = "model") -> None:
  """Append one line to the uploaded-models log (timestamp, id/path, source)."""
  UPLOADED_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
  ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
  line = f"{ts}\t{kind}\t{identifier}\t{source_path}\n"
  with UPLOADED_LOG_PATH.open("a") as f:
    f.write(line)


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


def gdrive_urgency_rank(mid: str, raw: dict, entry: ModelEntry, size_bytes: int) -> int:
  """
  Lower = higher off-site priority when filling upload_selection budget.
  0 explicit / disappearance-risk notes, 1 abliterated-uncensored / niche-experimental,
  2 hostable (GGUF / small / priority-2), 3 default.
  """
  notes = f"{raw.get('notes') or ''} {mid} {raw.get('hf_repo') or ''}"
  g = raw.get("gdrive_urgency")
  if g in ("critical", "high", "first", 0, 1, "0", "1"):
    return 0
  if DISAPPEARING_RE.search(notes):
    return 0
  if entry.tier == "D" or ABLIT_UNCENSOR_RE.search(notes) or ABLIT_UNCENSOR_RE.search(mid):
    return 1
  if entry.tier == "G" or entry.tier == "F":
    return 1
  pr = raw.get("priority", 99)
  if entry.tier == "C" or pr == 2 or size_bytes <= HOSTABLE_MAX_BYTES:
    return 2
  return 3


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

  # Sort: GDrive urgency (disappearance / uncensored / hostable first), then tier,
  # priority, then size ascending (fit more models in budget).
  reg_raw = load_yaml(archiver_root / "config" / "registry.yaml")
  reg_models = reg_raw.get("models", [])
  reg_by_id = {m["id"]: m for m in reg_models if m.get("id")}

  def sort_key(item: Tuple[str, int, bool]) -> Tuple[int, int, int, int]:
    mid, size, _ = item
    entry = registry[mid]
    tier_rank = TIER_ORDER.get(entry.tier, 99)
    raw = reg_by_id.get(mid, {})
    priority = raw.get("priority", 1)
    urg = gdrive_urgency_rank(mid, raw, entry, size)
    return (urg, tier_rank, priority, size)

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
    run_state_path = Path(sel.get("run_state_path", "/mnt/models/d3/run_state.json"))
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


def gdrive_remote_base(cfg: Dict) -> str:
  """rclone destination root: remote + base_path (e.g. gdrive:FOLDER_ID/models)."""
  remote = cfg["gdrive"]["remote"].rstrip("/")
  base_path = cfg["gdrive"].get("base_path", "").strip().strip("/")
  if not base_path:
    return remote
  return f"{remote}/{base_path}"


def run_rclone_copy(
  src: Path,
  remote_base: str,
  rel_dest: str,
  bwlimit: Optional[str] = None,
  transfers: int = 1,
  checkers: int = 1,
  exclude_patterns: Optional[List[str]] = None,
) -> bool:
  """
  Idempotent merge to remote: rclone copy only uploads missing or changed files (--checksum).
  Safe to re-run after interruption; do not skip calling this based on “any file exists” on Drive.
  """
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
  for pat in exclude_patterns or []:
    cmd.extend(["--exclude", pat])
  if bwlimit:
    cmd.extend(["--bwlimit", bwlimit])
  print(f"[rclone] {' '.join(cmd)}")
  result = subprocess.run(cmd)
  return result.returncode == 0


def backup_models(cfg: Dict, archiver_root: Path, kind: str):
  drives = load_drives(archiver_root)
  registry = load_registry(archiver_root)
  state = load_state()

  remote_base = gdrive_remote_base(cfg)

  planned: List[str] = get_model_ids_for_backup(cfg, archiver_root, kind)
  run_state_path = Path(
    cfg.get("upload_selection", {}).get("run_state_path", "/mnt/models/d3/run_state.json")
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

    # rel_dest is under gdrive.base_path (set to "models" in config); do not prefix "models/" again.
    rel_dest = mid.replace("/", "--")
    dst = f"{remote_base.rstrip('/')}/{rel_dest}"
    upload_target = dst
    was_marked_complete = (
      st_entry.get("source_path") == str(src)
      and st_entry.get("backed_up", False)
      and st_entry.get("upload_target") == upload_target
    )

    if not verify_model_dir_before_upload(archiver_root, src):
      print(f"[skip] {mid}: verification failed (checksum/manifest) — not uploading")
      continue

    g = cfg["gdrive"]
    bwlimit = g.get("bwlimit")
    transfers = g.get("transfers", 1)
    checkers = g.get("checkers", 1)
    ok = run_rclone_copy(
      src,
      remote_base,
      rel_dest,
      bwlimit=bwlimit,
      transfers=transfers,
      checkers=checkers,
      exclude_patterns=None,
    )
    if ok:
      st_models[mid] = {
        "source_path": str(src),
        "backed_up": True,
        "upload_target": upload_target,
      }
      save_state(state)
      if not was_marked_complete:
        log_upload_success(mid, str(src), kind="model")
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
  Upload an arbitrary set of model directories to GDrive. Each run invokes rclone copy
  (checksum); interrupted uploads resume on the next run without manual cleanup.
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
  remote_base = gdrive_remote_base(cfg)
  bwlimit = cfg["gdrive"].get("bwlimit")

  for src in paths:
    src = src.resolve()
    if not src.is_dir():
      print(f"[skip] {src}: not a directory")
      continue

    key = str(src)
    rel_dest = _slug_for_dir(src)
    dst = f"{remote_base.rstrip('/')}/{rel_dest}"
    upload_target = dst
    st_e = st_dirs.get(key, {})
    was_marked_complete = st_e.get("backed_up", False) and st_e.get("upload_target") == upload_target

    archiver_root = Path(cfg.get("archiver_root", "."))
    if not verify_model_dir_before_upload(archiver_root, src):
      print(f"[skip] {src}: verification failed (checksum/manifest) — not uploading")
      continue

    g = cfg["gdrive"]
    ok = run_rclone_copy(
      src,
      remote_base,
      rel_dest,
      bwlimit=g.get("bwlimit"),
      transfers=g.get("transfers", 1),
      checkers=g.get("checkers", 1),
      exclude_patterns=None,
    )
    if ok:
      st_dirs[key] = {"source_path": key, "backed_up": True, "upload_target": upload_target}
      save_state(state)
      if not was_marked_complete:
        log_upload_success(_slug_for_dir(src), key, kind="dir")
    else:
      print(f"[err] {src}: backup failed")


def _normalize_extra_path(p: object) -> Tuple[Path, str, List[str]]:
  """Return (source path, remote rel_dest e.g. extra/name, rclone --exclude patterns)."""
  if isinstance(p, dict):
    src = Path(p["path"])
    rel = (p.get("dest") or f"extra/{src.name}").strip()
    rel = rel if rel.startswith("extra/") else f"extra/{rel}"
    excl = p.get("exclude") or []
    if isinstance(excl, str):
      excl = [excl]
    return (src, rel, list(excl))
  src = Path(p)
  return (src, f"extra/{src.name}", [])


def backup_extra_paths(cfg: Dict):
  state = load_state()
  remote_base = gdrive_remote_base(cfg)
  st_paths = state.setdefault("paths", {})

  for p in cfg.get("extra_paths", []):
    src, rel_dest, excludes = _normalize_extra_path(p)
    if not src.exists():
      print(f"[skip] extra {src}: not found")
      continue

    dst = f"{remote_base.rstrip('/')}/{rel_dest}"
    upload_target = dst

    g = cfg["gdrive"]
    ok = run_rclone_copy(
      src,
      remote_base,
      rel_dest,
      bwlimit=g.get("bwlimit"),
      transfers=g.get("transfers", 1),
      checkers=g.get("checkers", 1),
      exclude_patterns=excludes or None,
    )
    if ok:
      st_paths[str(src)] = {"backed_up": True, "upload_target": upload_target}
      save_state(state)
    else:
      print(f"[err] extra {src}: backup failed")


def _normalize_staging_entry(p: object) -> Tuple[Path, str, List[str]]:
  """upload_staging list item -> (local root dir, remote subpath under gdrive remote_base, excludes)."""
  if not isinstance(p, dict):
    raise ValueError("upload_staging entries must be mappings with 'path' and 'dest'")
  src = Path(p["path"])
  dest = (p.get("dest") or "").strip().strip("/")
  if not dest:
    raise ValueError(f"upload_staging entry missing dest: {p!r}")
  excl = p.get("exclude") or []
  if isinstance(excl, str):
    excl = [excl]
  return (src, dest, list(excl))


def list_staging(cfg: Dict, archiver_root: Path) -> None:
  """Print staging roots, immediate subdirs, and whether local verification would pass."""
  entries = cfg.get("upload_staging") or []
  if not entries:
    print("upload_staging is empty in config.yaml")
    return
  verify_children = cfg.get("upload_staging_verify", True)
  remote_base = gdrive_remote_base(cfg)
  print(f"Remote base: {remote_base}")
  print()
  for raw in entries:
    try:
      src, dest, _ = _normalize_staging_entry(raw)
    except ValueError as e:
      print(f"[err] {e}")
      continue
    print(f"Staging root: {src}")
    print(f"  -> Drive: {remote_base.rstrip('/')}/{dest}/<model_dir>/")
    if not src.is_dir():
      print("  (missing or not a directory)")
      print()
      continue
    children = [c for c in sorted(src.iterdir()) if c.is_dir()]
    files = [c for c in src.iterdir() if c.is_file()]
    if files:
      print(f"  note: {len(files)} loose file(s) at root (not uploaded as model trees)")
    if not children:
      print("  (no subdirectories — add model dirs here, then run backup-staging)")
      print()
      continue
    for child in children:
      ok = True
      if verify_children:
        ok = verify_model_dir_before_upload(archiver_root, child)
      vs = "ok" if ok else "FAIL"
      print(f"  [{vs}] {child.name}")
    print()


def backup_staging(cfg: Dict, archiver_root: Path) -> None:
  """
  Upload only from configured staging folders (e.g. D3/D5 gdrive-upload).
  Each immediate subdirectory is one model tree → remote dest/<subdir_name>/.
  Same rclone copy --checksum merge/resume semantics as other backup commands.
  """
  entries = cfg.get("upload_staging") or []
  if not entries:
    print("upload_staging is empty; nothing to do.")
    return
  verify_children = cfg.get("upload_staging_verify", True)
  remote_base = gdrive_remote_base(cfg)
  state = load_state()
  st_st = state.setdefault("staging", {})
  g = cfg["gdrive"]

  for raw in entries:
    try:
      src, dest, excludes = _normalize_staging_entry(raw)
    except ValueError as e:
      print(f"[err] {e}")
      continue
    if not src.exists():
      print(f"[skip] staging root missing: {src}")
      continue
    if not src.is_dir():
      print(f"[skip] staging path not a directory: {src}")
      continue

    children = [c for c in sorted(src.iterdir()) if c.is_dir()]
    for c in src.iterdir():
      if c.is_file():
        print(f"[warn] loose file at staging root (ignored): {c.name}")

    if not children:
      print(f"[info] no model subdirs under {src} — nothing to upload")
      continue

    for child in children:
      key = str(child.resolve())
      rel_dest = f"{dest}/{child.name}"
      dst = f"{remote_base.rstrip('/')}/{rel_dest}"
      upload_target = dst
      st_entry = st_st.get(key, {})
      was_marked_complete = st_entry.get("backed_up", False) and st_entry.get("upload_target") == upload_target

      if verify_children and not verify_model_dir_before_upload(archiver_root, child):
        print(f"[skip] {dest}/{child.name}: verification failed — not uploading")
        continue

      ok = run_rclone_copy(
        child,
        remote_base,
        rel_dest,
        bwlimit=g.get("bwlimit"),
        transfers=g.get("transfers", 1),
        checkers=g.get("checkers", 1),
        exclude_patterns=excludes or None,
      )
      if ok:
        st_st[key] = {
          "backed_up": True,
          "upload_target": upload_target,
          "staging_root": str(src),
          "dest": dest,
        }
        save_state(state)
        if not was_marked_complete:
          log_upload_success(f"{dest}/{child.name}", key, kind="staging")
      else:
        print(f"[err] {dest}/{child.name}: backup failed")


def backup_extra_paths_refresh(cfg: Dict):
  """Same merge as backup_extra_paths; always runs rclone (no short-circuit). Records state on success."""
  state = load_state()
  st_paths = state.setdefault("paths", {})
  remote_base = gdrive_remote_base(cfg)

  for p in cfg.get("extra_paths", []):
    src, rel_dest, excludes = _normalize_extra_path(p)
    if not src.exists():
      print(f"[skip] extra {src}: not found")
      continue

    dst = f"{remote_base.rstrip('/')}/{rel_dest}"
    g = cfg["gdrive"]
    ok = run_rclone_copy(
      src,
      remote_base,
      rel_dest,
      bwlimit=g.get("bwlimit"),
      transfers=g.get("transfers", 1),
      checkers=g.get("checkers", 1),
      exclude_patterns=excludes or None,
    )
    if ok:
      st_paths[str(src)] = {"backed_up": True, "upload_target": dst}
      save_state(state)
    else:
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

  run_state_path = Path(sel.get("run_state_path", "/mnt/models/d3/run_state.json"))
  drives = sel.get("drives", ["d2", "d3"])
  max_total_gb = float(sel.get("max_total_gb", 3000))
  max_per_gb = float(sel.get("max_per_model_gb", 200))
  gguf_ids, full_ids = compute_upload_lists(
    cfg, archiver_root, run_state_path, drives, max_total_gb, max_per_gb
  )

  run_state = load_archiver_run_state(run_state_path)
  models_state = run_state.get("models", {})
  registry = load_registry(archiver_root)
  reg_raw = load_yaml(archiver_root / "config" / "registry.yaml")
  reg_by_id = {m["id"]: m for m in reg_raw.get("models", []) if m.get("id")}
  total_gguf = sum(models_state.get(mid, {}).get("total_bytes", 0) for mid in gguf_ids)
  total_full = sum(models_state.get(mid, {}).get("total_bytes", 0) for mid in full_ids)
  total_gb = (total_gguf + total_full) / 1024**3

  print(f"Upload selection: drives={drives}, max_total_gb={max_total_gb}, max_per_model_gb={max_per_gb}")
  print("  Urgency ranks: 0=explicit/disappearance-risk, 1=uncensored-abliterated/niche tier F·G, 2=hostable, 3=default")
  print(f"  GGUF: {len(gguf_ids)} models, {total_gguf / 1024**3:.1f} GB")
  print(f"  Full: {len(full_ids)} models, {total_full / 1024**3:.1f} GB")
  print(f"  Total: {total_gb:.1f} GB")
  for mid in gguf_ids:
    b = models_state.get(mid, {}).get("total_bytes", 0)
    ent = registry.get(mid)
    raw = reg_by_id.get(mid, {})
    u = gdrive_urgency_rank(mid, raw, ent, b) if ent else "?"
    print(f"    gguf  [u{u}] {mid}  ({b / 1024**3:.1f} GB)")
  for mid in full_ids:
    b = models_state.get(mid, {}).get("total_bytes", 0)
    ent = registry.get(mid)
    raw = reg_by_id.get(mid, {})
    u = gdrive_urgency_rank(mid, raw, ent, b) if ent else "?"
    print(f"    full [u{u}] {mid}  ({b / 1024**3:.1f} GB)")


def compare_with_archiver(cfg: Dict, archiver_root: Path) -> None:
  """
  Compare planned GDrive upload set with model archival registry and run_state.
  Reports: planned count, in registry, already downloaded (complete), path exists.
  """
  registry = load_registry(archiver_root)
  registry_ids = set(registry.keys())

  sel = cfg.get("upload_selection")
  if sel:
    run_state_path = Path(sel.get("run_state_path", "/mnt/models/d3/run_state.json"))
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
    run_state_path = Path("/mnt/models/d3/run_state.json")
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
  sub.add_parser("backup-staging", help="Upload from upload_staging folders (D3/D5 staging dirs).")
  sub.add_parser("list-staging", help="Dry-run: list staging dirs and verification status.")
  p_reg = sub.add_parser("backup-registry", help="Upload from gdrive-registry.yaml (verify + rclone --checksum).")
  p_reg.add_argument("--dry-run", action="store_true")
  p_reg.add_argument("--limit", type=int, default=None, metavar="N", help="Only first N model dirs")
  p_reg.add_argument("--no-verify", action="store_true", help="Skip local SHA verify (not recommended)")
  p_reg.add_argument(
    "--resync-all",
    action="store_true",
    help="Ignore logs/registry-upload-state.json; run rclone for every dir (full re-upload pass).",
  )
  p_reg.add_argument(
    "--verify-remote",
    action="store_true",
    help="Tracker-skipped dirs: rclone check local vs remote (checksum) before skipping.",
  )
  p_reg.add_argument(
    "--no-verify-remote",
    action="store_true",
    help="Disable remote check even if registry_verify_remote is set in config.",
  )
  sub.add_parser("list-registry", help="List model revision dirs implied by gdrive-registry.yaml.")
  sub.add_parser(
    "uploaded-registry-list",
    help="Write definitive uploaded model list from registry-upload-state.json (+uploaded.log metadata).",
  )
  sub.add_parser(
    "upload-registry-status",
    help="Write logs/GDRIVE-REGISTRY-UPLOAD-STATUS.md from discovery + uploaded.log.",
  )

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
  elif args.cmd == "backup-staging":
    backup_staging(cfg, archiver_root)
  elif args.cmd == "list-staging":
    list_staging(cfg, archiver_root)
  elif args.cmd == "backup-registry":
    from upload_registry import run_registry_upload

    reg_path = Path(__file__).resolve().parent / "gdrive-registry.yaml"
    reg = load_yaml(reg_path)
    g = cfg.get("gdrive") or {}
    want_remote = bool(
      getattr(args, "verify_remote", False)
      or g.get("registry_verify_remote")
      or cfg.get("registry_verify_remote")
    )
    verify_remote = want_remote and not getattr(args, "no_verify_remote", False)
    sys.exit(
      run_registry_upload(
        cfg,
        reg,
        archiver_root=archiver_root,
        dry_run=args.dry_run,
        limit=args.limit,
        no_verify=args.no_verify,
        resync_all=getattr(args, "resync_all", False),
        verify_remote=verify_remote,
      )
    )
  elif args.cmd == "list-registry":
    from upload_registry import print_registry_plan

    reg_path = Path(__file__).resolve().parent / "gdrive-registry.yaml"
    reg = load_yaml(reg_path)
    print_registry_plan(cfg, reg)
  elif args.cmd == "upload-registry-status":
    from upload_registry import write_registry_upload_status

    reg_path = Path(__file__).resolve().parent / "gdrive-registry.yaml"
    reg = load_yaml(reg_path)
    out = write_registry_upload_status(cfg, reg)
    print(f"Wrote {out}")
  elif args.cmd == "uploaded-registry-list":
    from upload_registry import write_uploaded_models_catalog

    reg_path = Path(__file__).resolve().parent / "gdrive-registry.yaml"
    reg = load_yaml(reg_path)
    out_json, out_md = write_uploaded_models_catalog(cfg, reg)
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")


if __name__ == "__main__":
  main()

