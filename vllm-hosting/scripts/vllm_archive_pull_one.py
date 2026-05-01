#!/usr/bin/env python3
"""
Download the next pending Hugging Face model from vllm-immediate-targets.yaml by default
(focused >21B / <120 GiB queue). Override with --manifest for the full catalog.

Respects HF_HOME / VLLM_ARCHIVE_ROOT from the environment (see config/env-archive-vm-vllm.sh).
Uses `trickle` for a ~2 MiB/s download cap by default (override THROTTLE_KBPS).
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
from typing import Any

try:
    import yaml
except ImportError as e:  # pragma: no cover
    print("Install PyYAML: pip install pyyaml", file=sys.stderr)
    raise SystemExit(1) from e


def _load_manifest(path: pathlib.Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "entries" not in data:
        raise SystemExit(f"Invalid manifest: {path}")
    return data


def _state_paths(root: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    st = root / "state"
    st.mkdir(parents=True, exist_ok=True)
    return st / "completed_repos.txt", st / "failed_repos.jsonl"


def _completed_set(completed_file: pathlib.Path) -> set[str]:
    if not completed_file.is_file():
        return set()
    return {ln.strip() for ln in completed_file.read_text(encoding="utf-8").splitlines() if ln.strip()}


def _append_completed(completed_file: pathlib.Path, hf_repo: str) -> None:
    with completed_file.open("a", encoding="utf-8") as f:
        f.write(hf_repo + "\n")


def _append_failed(failed_file: pathlib.Path, hf_repo: str, err: str) -> None:
    row = {"hf_repo": hf_repo, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "error": err[:2000]}
    with failed_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _which(name: str) -> str | None:
    from shutil import which

    return which(name)


def _run_download(
    hf_repo: str,
    throttle_kib_s: int,
    use_trickle: bool,
    extra_cli_args: list[str],
) -> int:
    hub = _which("huggingface-cli")
    if not hub:
        print("huggingface-cli not found. Install: pip install 'huggingface_hub[cli]'", file=sys.stderr)
        return 127

    cmd = [
        hub,
        "download",
        hf_repo,
        "--resume-download",
    ]
    cmd.extend(extra_cli_args)

    if use_trickle:
        trickle = _which("trickle")
        if not trickle:
            print("trickle not found (sudo apt install trickle). Set USE_TRICKLE=0 to disable cap.", file=sys.stderr)
            return 127
        cmd = [
            trickle,
            "-d",
            str(throttle_kib_s),
            "-u",
            os.environ.get("THROTTLE_UPLOAD_KBPS", "512"),
            "--",
        ] + cmd

    print("Running:", " ".join(cmd), flush=True)
    return subprocess.call(cmd)


def main() -> None:
    ap = argparse.ArgumentParser(description="Pull next vLLM archive model from manifest (one HF repo).")
    ap.add_argument(
        "--manifest",
        type=pathlib.Path,
        default=None,
        help="Path to vllm-archive-manifest.yaml (default: beside this script)",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print next repo and exit 0")
    ap.add_argument("--list", action="store_true", help="List pending repos and exit")
    ap.add_argument("--hf-arg", action="append", default=[], help="Extra args for huggingface-cli download (repeatable)")
    args = ap.parse_args()

    script_root = pathlib.Path(__file__).resolve().parents[1]
    manifest = args.manifest or (script_root / "config" / "vllm-immediate-targets.yaml")
    if not manifest.is_file():
        raise SystemExit(f"Missing manifest: {manifest}")

    archive_root = pathlib.Path(os.environ.get("VLLM_ARCHIVE_ROOT", "/mnt/models/d5/vllm"))
    completed_file, failed_file = _state_paths(archive_root)
    done = _completed_set(completed_file)

    data = _load_manifest(manifest)
    entries = data["entries"]
    pending = [e for e in entries if e["hf_repo"] not in done]

    if args.list:
        for e in pending:
            print(e["hf_repo"])
        return

    if not pending:
        print("All manifest repos marked complete in", completed_file)
        return

    next_entry = pending[0]
    hf_repo = next_entry["hf_repo"]
    if args.dry_run:
        print(hf_repo)
        return

    lock = pathlib.Path(os.environ.get("VLLM_PULL_LOCK", "/tmp/vllm-archive-pull.lock"))
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
    except FileExistsError:
        print(f"Another pull holds {lock}; remove if stale.", file=sys.stderr)
        raise SystemExit(2)

    use_trickle = os.environ.get("USE_TRICKLE", "1") not in ("0", "false", "no")
    throttle = int(os.environ.get("THROTTLE_KBPS", "2048"))

    try:
        rc = _run_download(hf_repo, throttle, use_trickle, list(args.hf_arg))
        if rc == 0:
            _append_completed(completed_file, hf_repo)
            print("OK:", hf_repo, "->", completed_file)
        else:
            _append_failed(failed_file, hf_repo, f"exit_code={rc}")
            raise SystemExit(rc)
    finally:
        try:
            lock.unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    main()
