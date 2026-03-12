#!/usr/bin/env python3
import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml


CONFIG_PATH = Path(__file__).with_name("config.yaml")
STATE_PATH = Path(__file__).with_name("state.json")


@dataclass
class DriveConfig:
  name: str
  mount_point: str


@dataclass
class ModelEntry:
  model_id: str
  hf_repo: str
  drive: str


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
    )
  return out


def resolve_model_path(entry: ModelEntry, drives: Dict[str, DriveConfig]) -> Optional[Path]:
  d = drives.get(entry.drive)
  if not d:
    return None
  return Path(d.mount_point) / "hf" / entry.hf_repo


def run_rclone_copy(src: Path, remote_base: str, rel_dest: str) -> bool:
  dst = f"{remote_base.rstrip('/')}/{rel_dest}"
  cmd = [
    "rclone",
    "copy",
    str(src),
    dst,
    "--checksum",
    "--transfers",
    "2",
    "--checkers",
    "4",
    "--retries",
    "10",
    "--low-level-retries",
    "20",
  ]
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

  key = "model_ids_gguf" if kind == "gguf" else "model_ids_full"
  ids: List[str] = cfg.get(key, []) or []

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

    if st_entry.get("source_path") == str(src) and st_entry.get("backed_up", False):
      print(f"[ok] {mid}: already backed up from {src}")
      continue

    rel_dest = f"models/{mid.replace('/', '--')}"
    ok = run_rclone_copy(src, remote_base, rel_dest)
    if ok:
      st_models[mid] = {
        "source_path": str(src),
        "backed_up": True,
      }
      save_state(state)
    else:
      print(f"[err] {mid}: backup failed")


def backup_extra_paths(cfg: Dict):
  state = load_state()
  remote = cfg["gdrive"]["remote"]
  base_path = cfg["gdrive"].get("base_path", "").strip()
  remote_base = f"{remote}/{base_path}" if base_path else remote

  for p in cfg.get("extra_paths", []):
    src = Path(p)
    if not src.exists():
      print(f"[skip] extra {src}: not found")
      continue

    st_paths = state.setdefault("paths", {})

    rel_dest = f"extra/{src.name}"
    ok = run_rclone_copy(src, remote_base, rel_dest)
    if ok:
      st_paths[str(src)] = {
        "backed_up": True,
      }
      save_state(state)
    else:
      print(f"[err] extra {src}: backup failed")


def main():
  parser = argparse.ArgumentParser(description="Survivor backup to Google Drive using rclone.")
  sub = parser.add_subparsers(dest="cmd", required=True)

  sub.add_parser("backup-gguf")
  sub.add_parser("backup-full")
  sub.add_parser("backup-extra")
  sub.add_parser("backup-all")

  args = parser.parse_args()

  cfg = load_yaml(CONFIG_PATH)
  archiver_root = Path(cfg["archiver_root"])

  if args.cmd == "backup-gguf":
    backup_models(cfg, archiver_root, kind="gguf")
  elif args.cmd == "backup-full":
    backup_models(cfg, archiver_root, kind="full")
  elif args.cmd == "backup-extra":
    backup_extra_paths(cfg)
  elif args.cmd == "backup-all":
    backup_models(cfg, archiver_root, kind="gguf")
    backup_models(cfg, archiver_root, kind="full")
    backup_extra_paths(cfg)


if __name__ == "__main__":
  main()

