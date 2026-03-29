#!/usr/bin/env python3
"""
Repair local checksum failures recorded in logs/gdrive-preupload-verify-failures.jsonl.

Strategy (minimal I/O):
  - Read JSONL; skip manifest/verifier exception rows (need manual fix).
  - Group by model revision dir + file; drop files that already verify OK (stale JSONL).
  - For each bad file: remove blob + .sha256 sidecar, hf_hub_download pinned revision,
    re-hash vs manifest, write sidecar, then optional rclone copy of that dir only.

Independent logs:
  - logs/preupload-verify-repair.log  (human, append)
  - logs/preupload-verify-repair-state.json  (audit JSON)

Reconcile (optional): refresh logs/GDRIVE-REGISTRY-UPLOAD-STATUS.md via backup.py and
append logs/PREUPLOAD-REPAIR-RECONCILE.md.

Usage:
  cd gdrive-archival
  export RCLONE_CONFIG=$PWD/rclone.conf   # if needed
  export HF_TOKEN=...                     # or ~/.hf_token for gated repos

  python3 repair_preupload_failures.py --dry-run
  python3 repair_preupload_failures.py --no-upload
  python3 repair_preupload_failures.py
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Optional, Set, Tuple

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
VERIFY_JSONL = SCRIPT_DIR / "logs" / "gdrive-preupload-verify-failures.jsonl"
REPAIR_LOG = SCRIPT_DIR / "logs" / "preupload-verify-repair.log"
STATE_PATH = SCRIPT_DIR / "logs" / "preupload-verify-repair-state.json"
RECONCILE_MD = SCRIPT_DIR / "logs" / "PREUPLOAD-REPAIR-RECONCILE.md"
STATE_VERSION = 1


def _now_iso() -> str:
  return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_yaml(path: Path) -> dict:
  with path.open("r", encoding="utf-8") as f:
    return yaml.safe_load(f) or {}


def _append_repair_log(line: str) -> None:
  REPAIR_LOG.parent.mkdir(parents=True, exist_ok=True)
  with REPAIR_LOG.open("a", encoding="utf-8") as f:
    f.write(f"{_now_iso()} {line}\n")


def load_state() -> dict:
  if not STATE_PATH.is_file():
    return {"version": STATE_VERSION, "runs": [], "repaired_keys": []}
  try:
    data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return {"version": STATE_VERSION, "runs": [], "repaired_keys": []}
  if not isinstance(data.get("runs"), list):
    data["runs"] = []
  if not isinstance(data.get("repaired_keys"), list):
    data["repaired_keys"] = []
  data["version"] = STATE_VERSION
  return data


def save_state(data: dict) -> None:
  STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
  tmp = STATE_PATH.with_suffix(".json.tmp")
  tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
  tmp.replace(STATE_PATH)


def _hf_token() -> Optional[str]:
  t = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
  if t:
    return t.strip() or None
  p = Path.home() / ".hf_token"
  if p.is_file():
    try:
      return p.read_text(encoding="utf-8").strip() or None
    except OSError:
      return None
  return None


def _archiver_src(cfg: dict) -> Optional[Path]:
  ar = Path(cfg.get("archiver_root") or "").expanduser()
  candidates = [
    ar / "src",
    SCRIPT_DIR.parent / "local" / "src",
    SCRIPT_DIR.parent / "model-archival" / "src",
    SCRIPT_DIR.parent / "model-archiver" / "src",
  ]
  for p in candidates:
    if (p / "archiver" / "verifier.py").is_file():
      return p.resolve()
  return None


def _models_prefix(cfg: dict) -> str:
  g = cfg.get("gdrive") or {}
  remote = str(g.get("remote", "")).rstrip("/")
  base_path = str(g.get("base_path") or "").strip().strip("/")
  remote_base = f"{remote}/{base_path}" if base_path else remote
  return f"{remote_base.rstrip('/')}/models"


def load_failure_records(path: Path) -> List[dict]:
  if not path.is_file():
    return []
  out: List[dict] = []
  for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
    line = line.strip()
    if not line:
      continue
    try:
      out.append(json.loads(line))
    except json.JSONDecodeError:
      continue
  return out


def parse_failures(records: List[dict]) -> Tuple[DefaultDict[str, Set[str]], List[str]]:
  """
  Returns (model_relpath -> set of relative file paths to fix), list of skip reasons
  for manifest/exception rows.
  """
  by_model: DefaultDict[str, Set[str]] = defaultdict(set)
  skips: List[str] = []
  for rec in records:
    rel = str(rec.get("model_relpath") or "").strip()
    if not rel:
      continue
    err = rec.get("error")
    if err:
      skips.append(f"{rel}: {err}")
      continue
    fp = rec.get("file")
    if fp is None:
      continue
    fstr = str(fp).strip()
    if not fstr:
      continue
    if fstr == "manifest.json" and rec.get("expected_sha256") is None:
      skips.append(f"{rel}: manifest/verify exception (see jsonl error if present)")
      continue
    by_model[rel].add(fstr)
  return by_model, skips


def _sidecar_path(blob: Path) -> Path:
  return blob.with_suffix(blob.suffix + ".sha256")


def redownload_file(
  model_dir: Path,
  rel_file: str,
  hf_repo: str,
  revision: str,
  expected_sha256: str,
  token: Optional[str],
  dry_run: bool,
) -> Tuple[bool, str]:
  try:
    from huggingface_hub import hf_hub_download
  except ImportError:
    return False, "huggingface_hub not installed (pip/uv add huggingface_hub)"

  dest = model_dir / rel_file
  if dry_run:
    return True, f"dry-run: would hf_hub_download {hf_repo}@{revision[:12]}… {rel_file}"

  dest.parent.mkdir(parents=True, exist_ok=True)
  if dest.exists():
    dest.unlink()
  sc = _sidecar_path(dest)
  if sc.exists():
    sc.unlink()

  try:
    cached = hf_hub_download(
      repo_id=hf_repo,
      filename=rel_file,
      revision=revision,
      token=token,
      local_dir=str(model_dir),
    )
  except Exception as e:
    return False, f"hf_hub_download failed: {e}"

  got = Path(cached)
  if not got.exists():
    return False, f"download path missing: {cached}"

  # hf_hub_download with local_dir should place at model_dir/rel_file
  final = model_dir / rel_file
  if got.resolve() != final.resolve():
    final.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(got), str(final))

  if not final.is_file():
    return False, f"expected file at {final}"

  try:
    from archiver.verifier import sha256_file, write_sidecar
  except ImportError:
    return False, "archiver.verifier not importable (set archiver_root in config.yaml)"

  actual = sha256_file(final)
  if actual != expected_sha256:
    try:
      final.unlink()
    except OSError:
      pass
    return False, f"post-download SHA mismatch: expected {expected_sha256[:16]}… got {actual[:16]}…"

  write_sidecar(final, actual)
  return True, "ok"


def reconcile_main_status() -> Tuple[int, str]:
  backup_py = SCRIPT_DIR / "backup.py"
  if not backup_py.is_file():
    return 1, "backup.py not found"
  r = subprocess.run(
    [sys.executable, str(backup_py), "upload-registry-status"],
    cwd=str(SCRIPT_DIR),
    capture_output=True,
    text=True,
  )
  msg = (r.stdout or "").strip() or (r.stderr or "").strip() or f"exit {r.returncode}"
  return r.returncode, msg


def append_reconcile_summary(
  *,
  repaired_models: List[str],
  failed_models: List[str],
  skipped_manifest: List[str],
  dry_run: bool,
) -> None:
  RECONCILE_MD.parent.mkdir(parents=True, exist_ok=True)
  lines = [
    f"\n## {_now_iso()} (UTC)\n\n",
    f"- dry_run: `{dry_run}`\n",
    f"- models repaired (local + upload if enabled): {len(repaired_models)}\n",
  ]
  if repaired_models:
    lines.append("\n**Repaired relpaths:**\n\n")
    for m in repaired_models:
      lines.append(f"- `{m}`\n")
  if failed_models:
    lines.append("\n**Failed:**\n\n")
    for m in failed_models:
      lines.append(f"- `{m}`\n")
  if skipped_manifest:
    lines.append("\n**Skipped (manifest / verifier exception — manual):**\n\n")
    for s in skipped_manifest[:20]:
      lines.append(f"- {s}\n")
    if len(skipped_manifest) > 20:
      lines.append(f"- … and {len(skipped_manifest) - 20} more\n")
  lines.append(
    "\nMain status refreshed via `python3 backup.py upload-registry-status` "
    "(see `logs/GDRIVE-REGISTRY-UPLOAD-STATUS.md`).\n"
  )
  with RECONCILE_MD.open("a", encoding="utf-8") as f:
    f.write("".join(lines))


def main() -> int:
  parser = argparse.ArgumentParser(description="Repair pre-upload verify failures (per-file HF re-fetch).")
  parser.add_argument("--dry-run", action="store_true", help="Print actions only")
  parser.add_argument("--no-upload", action="store_true", help="Fix local files only (no rclone)")
  parser.add_argument(
    "--no-reconcile",
    action="store_true",
    help="Do not run backup.py upload-registry-status or append PREUPLOAD-REPAIR-RECONCILE.md",
  )
  parser.add_argument("--jsonl", type=Path, default=VERIFY_JSONL, help="Alternate failures JSONL")
  parser.add_argument("--limit-models", type=int, default=None, help="Max distinct model dirs to process")
  args = parser.parse_args()

  if not CONFIG_PATH.is_file():
    print(f"error: missing {CONFIG_PATH}", file=sys.stderr)
    return 2

  cfg = load_yaml(CONFIG_PATH)
  mount = Path(cfg.get("models_mount", "/mnt/models")).resolve()
  src = _archiver_src(cfg)
  if not src:
    print(
      "error: archiver src not found (set archiver_root in config.yaml)",
      file=sys.stderr,
    )
    return 2
  if str(src) not in sys.path:
    sys.path.insert(0, str(src))
  from archiver.verifier import load_manifest, verify_file, verify_model_dir

  records = load_failure_records(args.jsonl)
  by_model, skip_msgs = parse_failures(records)
  if not by_model:
    if skip_msgs:
      print(
        f"No checksum file repairs needed ({len(skip_msgs)} JSONL row(s) are manifest/verifier exceptions — "
        "manual fix or uploader `non_archiver_manifest` skip; see logs/gdrive-preupload-verify-report.md)."
      )
    else:
      print("No failure records in JSONL (or file missing).")
      _append_repair_log("no jsonl records")
      return 0

  token = _hf_token()
  g = cfg.get("gdrive") or {}
  transfers = int(g.get("transfers", 1))
  checkers = int(g.get("checkers", 1))
  bwlimit = g.get("bwlimit")
  models_prefix = _models_prefix(cfg)

  # Import upload helpers only when uploading
  run_rclone = None
  mark_complete = None
  if not args.no_upload:
    from upload_registry import (
      load_registry_upload_state,
      mark_registry_model_complete,
      run_rclone_copy_dir,
    )

    run_rclone = run_rclone_copy_dir
    mark_complete = mark_registry_model_complete
    load_upload_state = load_registry_upload_state

  state = load_state()
  repaired_keys: Set[str] = set(str(x) for x in state.get("repaired_keys", []))

  run_entry: Dict[str, Any] = {
    "at_utc": _now_iso(),
    "dry_run": args.dry_run,
    "no_upload": args.no_upload,
    "models": [],
  }

  repaired_models: List[str] = []
  failed_models: List[str] = []

  items = sorted(by_model.items(), key=lambda x: x[0])
  if args.limit_models is not None:
    items = items[: max(0, args.limit_models)]

  _append_repair_log(
    f"start dry_run={args.dry_run} no_upload={args.no_upload} models={len(items)} jsonl={args.jsonl}"
  )

  for rel_pos, files in items:
    model_dir = (mount / rel_pos).resolve()
    if not model_dir.is_dir():
      msg = f"[skip] not a directory: {model_dir}"
      print(msg, file=sys.stderr)
      _append_repair_log(f"{rel_pos}: skip missing_dir")
      continue

    manifest = load_manifest(model_dir)
    if not manifest:
      msg = f"[skip] no manifest.json: {rel_pos}"
      print(msg, file=sys.stderr)
      _append_repair_log(f"{rel_pos}: skip no_manifest")
      failed_models.append(rel_pos)
      continue

    hf_repo = str(manifest.get("hf_repo") or "").strip()
    revision = str(manifest.get("commit_sha") or "").strip() or "main"
    if not hf_repo:
      print(f"[skip] manifest missing hf_repo: {rel_pos}", file=sys.stderr)
      failed_models.append(rel_pos)
      continue

    mf_files: Dict[str, dict] = {str(e["path"]): e for e in manifest.get("files") or [] if "path" in e}

    # Drop files that already match manifest now
    todo: Set[str] = set()
    for fname in sorted(files):
      key = f"{rel_pos}|{fname}"
      entry = mf_files.get(fname)
      if not entry:
        print(f"[skip] {rel_pos}: file not in manifest `{fname}`", file=sys.stderr)
        continue
      exp = entry.get("sha256")
      if not exp:
        continue
      target = model_dir / fname
      ok, _ = verify_file(target, str(exp))
      if ok:
        _append_repair_log(f"{rel_pos}: already_ok {fname}")
        continue
      todo.add(fname)

    if not todo:
      print(f"[ok] {rel_pos}: nothing to redownload (stale jsonl or already fixed)")
      continue

    model_ok = True
    for fname in sorted(todo):
      key = f"{rel_pos}|{fname}"
      entry = mf_files[fname]
      exp = str(entry["sha256"])
      ok, detail = redownload_file(
        model_dir, fname, hf_repo, revision, exp, token, args.dry_run
      )
      print(f"  {fname}: {detail}")
      _append_repair_log(f"{rel_pos}: redownload {fname} -> {detail}")
      if not ok:
        model_ok = False
      else:
        repaired_keys.add(key)

    if not model_ok:
      failed_models.append(rel_pos)
      run_entry["models"].append({"relpath": rel_pos, "ok": False, "files": sorted(todo)})
      continue

    # Full dir verify
    if args.dry_run:
      print(f"[dry-run] would verify + upload: {rel_pos}")
      repaired_models.append(rel_pos)
      run_entry["models"].append({"relpath": rel_pos, "ok": True, "dry_run": True})
      continue

    results = verify_model_dir(model_dir)
    bad = [r for r in results if not r.get("ok")]
    if bad:
      print(f"[fail] verify_model_dir after repair: {rel_pos}", file=sys.stderr)
      for r in bad:
        print(f"    {r.get('path')}", file=sys.stderr)
      failed_models.append(rel_pos)
      run_entry["models"].append({"relpath": rel_pos, "ok": False, "post_verify": "failed"})
      continue

    if args.no_upload:
      print(f"[ok] local verify passed: {rel_pos}")
      repaired_models.append(rel_pos)
      run_entry["models"].append({"relpath": rel_pos, "ok": True, "upload": False})
      continue

    dst = f"{models_prefix}/{rel_pos}"
    assert run_rclone is not None and mark_complete is not None
    up_ok = run_rclone(model_dir, dst, transfers, checkers, bwlimit, None, False)
    if not up_ok:
      print(f"[fail] rclone: {rel_pos}", file=sys.stderr)
      failed_models.append(rel_pos)
      run_entry["models"].append({"relpath": rel_pos, "ok": False, "upload": False})
      continue

    from backup import log_upload_success

    log_upload_success(rel_pos, str(model_dir), kind="registry-model")
    st = load_upload_state()
    mark_complete(st, rel_pos)
    print(f"[ok] uploaded: {rel_pos}")
    repaired_models.append(rel_pos)
    run_entry["models"].append({"relpath": rel_pos, "ok": True, "upload": True})

  state["runs"].append(run_entry)
  state["repaired_keys"] = sorted(repaired_keys)
  if not args.dry_run:
    save_state(state)

  if not args.no_reconcile and not args.dry_run:
    code, out = reconcile_main_status()
    print(f"[reconcile] backup upload-registry-status: {out}")
    _append_repair_log(f"reconcile upload-registry-status rc={code} {out[:200]}")
    append_reconcile_summary(
      repaired_models=repaired_models,
      failed_models=failed_models,
      skipped_manifest=skip_msgs,
      dry_run=False,
    )
  elif args.dry_run and not args.no_reconcile:
    print("[reconcile] skipped (dry-run)")

  if skip_msgs:
    print("\nSkipped (manual) manifest/exception rows:", len(skip_msgs))
  return 1 if failed_models else 0


if __name__ == "__main__":
  raise SystemExit(main())
