"""
Colab downloader — HuggingFace → Google Drive

Fully resumable at the per-file level. State is checkpointed after every
file so a crash or session timeout wastes at most one file's transfer.

No dependency on the local/ archiver package. Requires only:
    huggingface_hub  (pre-installed in Colab)
    pyyaml           (pre-installed in Colab)
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.utils import EntryNotFoundError, RepositoryNotFoundError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHUNK = 8 * 1024 * 1024   # 8 MB hash read chunk
MAX_RETRIES = 5
RETRY_BASE  = 15           # seconds, doubled each retry

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FileResult:
    path: str
    size_bytes: int
    sha256: str
    status: str           # "downloaded" | "skipped" | "failed"
    error: Optional[str] = None


@dataclass
class ModelResult:
    model_id: str
    commit_sha: str
    dest_dir: Path
    status: str           # "complete" | "partial" | "failed" | "skipped"
    files: list[FileResult] = field(default_factory=list)
    total_bytes: int = 0
    elapsed_seconds: float = 0.0
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _sidecar(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".sha256")


def _read_sidecar(path: Path) -> Optional[str]:
    sc = _sidecar(path)
    return sc.read_text().strip() if sc.exists() else None


def _write_sidecar(path: Path, digest: str) -> None:
    _sidecar(path).write_text(digest + "\n")


# ---------------------------------------------------------------------------
# Per-file state (checkpointed inside model's dest_dir)
# ---------------------------------------------------------------------------

def _load_file_state(dest_dir: Path) -> dict:
    """Load per-file completion state from dest_dir/.file_state.json."""
    p = dest_dir / ".file_state.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {}


def _save_file_state(dest_dir: Path, file_state: dict) -> None:
    """Atomically write per-file state after each completed file."""
    p = dest_dir / ".file_state.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(file_state, indent=2) + "\n")
    tmp.replace(p)


# ---------------------------------------------------------------------------
# Core per-file downloader
# ---------------------------------------------------------------------------

def _download_file(
    repo_id: str,
    filename: str,
    dest_dir: Path,
    hf_token: Optional[str],
    revision: str,
    on_progress: Optional[Callable[[str, str], None]] = None,
) -> FileResult:
    """Download a single file, skip if .sha256 sidecar already present."""

    final_path = dest_dir / filename
    final_path.parent.mkdir(parents=True, exist_ok=True)

    # Fast-path: already done
    if final_path.exists():
        existing = _read_sidecar(final_path)
        if existing:
            size = final_path.stat().st_size
            _log(f"  ├─ SKIP   {filename}  {_human(size)}")
            if on_progress:
                on_progress(filename, "skipped")
            return FileResult(path=filename, size_bytes=size,
                              sha256=existing, status="skipped")

    if on_progress:
        on_progress(filename, "downloading")

    last_error = None
    for attempt in range(MAX_RETRIES):
        if attempt:
            wait = RETRY_BASE * (2 ** (attempt - 1))
            _log(f"  ├─ RETRY  {filename}  attempt {attempt+1}/{MAX_RETRIES}  wait {wait}s")
            time.sleep(wait)
        try:
            cached = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                revision=revision,
                token=hf_token,
                local_dir=str(dest_dir),
                local_dir_use_symlinks=False,
            )
            cached_path = Path(cached)
            if cached_path.resolve() != final_path.resolve():
                final_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(cached_path), str(final_path))

            digest = _sha256_file(final_path)
            _write_sidecar(final_path, digest)
            size = final_path.stat().st_size
            _log(f"  ├─ OK     {filename}  sha256={digest[:16]}…  {_human(size)}")
            if on_progress:
                on_progress(filename, "done")
            return FileResult(path=filename, size_bytes=size,
                              sha256=digest, status="downloaded")

        except (EntryNotFoundError, RepositoryNotFoundError) as e:
            if on_progress:
                on_progress(filename, "failed")
            return FileResult(path=filename, size_bytes=0, sha256="",
                              status="failed", error=str(e))
        except Exception as e:
            last_error = e
            _log(f"  ├─ ERR    {filename}  {e}")

    if on_progress:
        on_progress(filename, "failed")
    return FileResult(path=filename, size_bytes=0, sha256="",
                      status="failed", error=str(last_error))


# ---------------------------------------------------------------------------
# GGUF quant filter
# ---------------------------------------------------------------------------

def _should_include(filename: str, quant_levels: Optional[list[str]]) -> bool:
    if not quant_levels:
        return True
    lower = filename.lower()
    if not lower.endswith(".gguf"):
        return True
    return any(q.lower() in lower for q in quant_levels)


# ---------------------------------------------------------------------------
# Manifest / descriptor / index writers
# ---------------------------------------------------------------------------

def _write_manifest(dest_dir: Path, model_id: str, commit_sha: str,
                    files: list[FileResult]) -> None:
    manifest = {
        "model_id": model_id,
        "commit_sha": commit_sha,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "source": "google-colab",
        "total_size_bytes": sum(f.size_bytes for f in files),
        "files": {
            f.path: {"sha256": f.sha256, "size_bytes": f.size_bytes, "status": f.status}
            for f in files
        },
    }
    tmp = dest_dir / ".manifest.tmp"
    tmp.write_text(json.dumps(manifest, indent=2) + "\n")
    tmp.replace(dest_dir / "manifest.json")


def _write_descriptor(dest_dir: Path, model_id: str, commit_sha: str,
                      tier: str, total_bytes: int) -> None:
    info = {
        "model_id": model_id,
        "commit_sha": commit_sha,
        "tier": tier,
        "archive_source": "google-colab → google-drive",
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "total_size_bytes": total_bytes,
        "total_size_human": _human(total_bytes),
    }
    (dest_dir / "DESCRIPTOR.json").write_text(json.dumps(info, indent=2) + "\n")
    (dest_dir / "DESCRIPTOR.md").write_text(
        f"# {model_id}\n\n"
        f"| Field | Value |\n|-------|-------|\n"
        f"| Commit SHA | `{commit_sha}` |\n"
        f"| Tier | {tier} |\n"
        f"| Archived | {info['archived_at']} |\n"
        f"| Source | Google Colab → Google Drive |\n"
        f"| Total size | {info['total_size_human']} |\n"
    )


def _append_global_index(index_path: Path, model_id: str,
                         files: list[FileResult]) -> None:
    with open(index_path, "a") as f:
        for fr in files:
            if fr.sha256:
                f.write(json.dumps({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "model_id": model_id,
                    "file": fr.path,
                    "sha256": fr.sha256,
                    "size": fr.size_bytes,
                    "source": "colab",
                }) + "\n")


# ---------------------------------------------------------------------------
# Session time guard
# ---------------------------------------------------------------------------

class SessionGuard:
    """Warns when a Colab session is approaching its time limit."""

    def __init__(self, limit_hours: float = 23.0):
        self._start = time.monotonic()
        self._limit_seconds = limit_hours * 3600

    def elapsed_hours(self) -> float:
        return (time.monotonic() - self._start) / 3600

    def remaining_hours(self) -> float:
        return max(0.0, self._limit_seconds / 3600 - self.elapsed_hours())

    def is_near_limit(self, warn_hours: float = 1.0) -> bool:
        return self.remaining_hours() <= warn_hours

    def status_line(self) -> str:
        e = self.elapsed_hours()
        r = self.remaining_hours()
        return f"Session: {e:.1f}h elapsed  {r:.1f}h remaining"


# ---------------------------------------------------------------------------
# Top-level model downloader
# ---------------------------------------------------------------------------

def download_model(
    model_id: str,
    dest_root: Path,
    hf_token: Optional[str] = None,
    tier: str = "A",
    quant_levels: Optional[list[str]] = None,
    global_index_path: Optional[Path] = None,
    state: Optional[dict] = None,
    save_state_fn: Optional[Callable] = None,
    session_guard: Optional[SessionGuard] = None,
    on_file_progress: Optional[Callable[[str, str, int, int], None]] = None,
) -> ModelResult:
    """
    Download all files for a HuggingFace model into dest_root/<org>/<name>/<commit>/

    Per-file state is checkpointed after each file completes so a crash
    wastes at most one file's transfer.

    Args:
        model_id:          e.g. "deepseek-ai/DeepSeek-R1"
        dest_root:         root on Google Drive
        hf_token:          HF token or None
        tier:              A/B/C/D
        quant_levels:      GGUF quant filter e.g. ["Q4_K_M"]
        global_index_path: path to global_index.jsonl
        state:             mutable dict for model-level status
        save_state_fn:     called after each file to persist state to Drive
        session_guard:     SessionGuard instance for time limit warnings
        on_file_progress:  callback(filename, status, files_done, files_total)
    """
    # Model-level state check
    if state is not None and state.get(model_id) == "complete":
        _log(f"└── SKIP   {model_id}  (state=complete)")
        org, name = model_id.split("/", 1)
        existing = list((dest_root / org / name).glob("*/manifest.json"))
        dest_dir = existing[0].parent if existing else dest_root / org / name / "cached"
        return ModelResult(model_id=model_id, commit_sha="cached",
                           dest_dir=dest_dir, status="skipped")

    # Session time check
    if session_guard and session_guard.is_near_limit(warn_hours=1.5):
        _log(f"⚠  SESSION LIMIT APPROACHING — {session_guard.status_line()}")
        _log(f"⚠  Skipping {model_id} — start a new session to continue")
        if state is not None:
            state.setdefault(model_id, "pending")
        return ModelResult(model_id=model_id, commit_sha="",
                           dest_dir=dest_root, status="skipped",
                           error="session_limit_approaching")

    api = HfApi()
    t0  = time.monotonic()

    # Resolve commit SHA
    try:
        info       = api.repo_info(repo_id=model_id, token=hf_token)
        commit_sha = info.sha
    except RepositoryNotFoundError:
        msg = f"Repo not found or token required: {model_id}"
        _log(f"└── FAIL   {model_id}  {msg}")
        if state is not None:
            state[model_id] = "failed"
        if save_state_fn:
            save_state_fn()
        return ModelResult(model_id=model_id, commit_sha="",
                           dest_dir=dest_root, status="failed", error=msg)
    except Exception as e:
        _log(f"└── FAIL   {model_id}  {e}")
        if state is not None:
            state[model_id] = "failed"
        if save_state_fn:
            save_state_fn()
        return ModelResult(model_id=model_id, commit_sha="",
                           dest_dir=dest_root, status="failed", error=str(e))

    org, name = model_id.split("/", 1)
    dest_dir  = dest_root / org / name / commit_sha[:12]
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Fast-path: manifest already complete
    manifest_path = dest_dir / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
            all_ok = all(
                (dest_dir / fn).exists() and _read_sidecar(dest_dir / fn)
                for fn in manifest.get("files", {})
            )
            if all_ok:
                _log(f"└── SKIP   {model_id}  commit={commit_sha[:12]}  manifest complete")
                if state is not None:
                    state[model_id] = "complete"
                if save_state_fn:
                    save_state_fn()
                files = [
                    FileResult(path=fn, size_bytes=d["size_bytes"],
                               sha256=d["sha256"], status="skipped")
                    for fn, d in manifest["files"].items()
                ]
                return ModelResult(model_id=model_id, commit_sha=commit_sha,
                                   dest_dir=dest_dir, status="skipped",
                                   files=files,
                                   total_bytes=sum(f.size_bytes for f in files))
        except Exception:
            pass

    # List repo files
    try:
        repo_files = [
            f for f in api.list_repo_tree(repo_id=model_id, recursive=True,
                                          token=hf_token)
            if hasattr(f, "path") and not f.path.endswith("/")
               and _should_include(f.path, quant_levels)
        ]
    except Exception as e:
        _log(f"└── FAIL   {model_id}  list_repo_tree: {e}")
        if state is not None:
            state[model_id] = "failed"
        if save_state_fn:
            save_state_fn()
        return ModelResult(model_id=model_id, commit_sha=commit_sha,
                           dest_dir=dest_dir, status="failed", error=str(e))

    total_size  = sum(getattr(f, "size", 0) or 0 for f in repo_files)
    total_files = len(repo_files)

    _log(
        f"┌── BEGIN  {model_id}  commit={commit_sha[:12]}"
        f"  files={total_files}  size={total_size / 1024**3:.1f} GB"
        + (f"  [{session_guard.status_line()}]" if session_guard else "")
    )

    if state is not None:
        state[model_id] = "in_progress"
    if save_state_fn:
        save_state_fn()

    # Load per-file checkpoint state
    file_state = _load_file_state(dest_dir)
    results: list[FileResult] = []

    for idx, repo_file in enumerate(repo_files, 1):
        fn = repo_file.path

        # Per-file skip from checkpoint (faster than sidecar check for large repos)
        if file_state.get(fn) == "done":
            size     = (dest_dir / fn).stat().st_size if (dest_dir / fn).exists() else 0
            digest   = _read_sidecar(dest_dir / fn) or ""
            results.append(FileResult(path=fn, size_bytes=size,
                                      sha256=digest, status="skipped"))
            if on_file_progress:
                on_file_progress(fn, "skipped", idx, total_files)
            continue

        # Session limit — stop mid-model cleanly
        if session_guard and session_guard.is_near_limit(warn_hours=1.0):
            _log(f"⚠  SESSION LIMIT — stopping cleanly after {idx-1}/{total_files} files")
            _log(f"   Restart the notebook to continue from this file.")
            break

        def _progress_cb(filename: str, status: str,
                         _idx=idx, _total=total_files) -> None:
            if on_file_progress:
                on_file_progress(filename, status, _idx, _total)

        fr = _download_file(
            repo_id=model_id,
            filename=fn,
            dest_dir=dest_dir,
            hf_token=hf_token,
            revision=commit_sha,
            on_progress=_progress_cb,
        )
        results.append(fr)

        # Checkpoint after every file
        if fr.status in ("downloaded", "skipped"):
            file_state[fn] = "done"
        else:
            file_state[fn] = "failed"
        _save_file_state(dest_dir, file_state)
        if save_state_fn:
            save_state_fn()

    # Determine overall status
    failures    = [r for r in results if r.status == "failed"]
    all_done    = len(results) == total_files
    status      = "complete" if (all_done and not failures) else "partial"
    total_bytes = sum(r.size_bytes for r in results)
    elapsed     = time.monotonic() - t0

    _write_manifest(dest_dir, model_id, commit_sha, results)
    _write_descriptor(dest_dir, model_id, commit_sha, tier, total_bytes)

    if global_index_path is not None:
        _append_global_index(global_index_path, model_id, results)

    if state is not None:
        state[model_id] = status
    if save_state_fn:
        save_state_fn()

    speed = total_bytes / elapsed / 1024**2 if elapsed > 0 else 0
    _log(
        f"└── {'DONE' if not failures else 'PARTIAL'}  "
        f"{model_id}  commit={commit_sha[:12]}"
        f"  files={len(results)}/{total_files}"
        f"  {total_bytes / 1024**3:.2f} GB"
        f"  {elapsed / 60:.1f} min  {speed:.1f} MB/s"
        + (f"  FAIL={len(failures)}" if failures else "")
    )

    return ModelResult(
        model_id=model_id, commit_sha=commit_sha, dest_dir=dest_dir,
        status=status, files=results, total_bytes=total_bytes,
        elapsed_seconds=elapsed,
    )
