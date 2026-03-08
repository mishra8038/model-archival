"""Persistent run state: tracks per-model download status across invocations."""

from __future__ import annotations

import json
import logging
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# Per-model status values
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETE = "complete"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"      # auth required but no token


class RunState:
    """
    Manages run_state.json — a JSON file persisted on D5 that records the
    status of every model across all runs.
    """

    def __init__(self, state_path: Path) -> None:
        self.state_path = state_path
        self._lock = threading.Lock()
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text())
            except Exception as e:
                log.warning("Could not read run_state.json: %s — starting fresh", e)
        return {"models": {}, "runs": []}

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._data, indent=2))
        tmp.replace(self.state_path)

    # ------------------------------------------------------------------
    # Model status
    # ------------------------------------------------------------------

    def get_model_status(self, model_id: str) -> str:
        return self._data["models"].get(model_id, {}).get("status", STATUS_PENDING)

    def get_model_data(self, model_id: str) -> dict:
        return self._data["models"].get(model_id, {})

    def set_model_status(
        self,
        model_id: str,
        status: str,
        *,
        commit_sha: Optional[str] = None,
        total_bytes: Optional[int] = None,
        error: Optional[str] = None,
        drive: Optional[str] = None,
    ) -> None:
        with self._lock:
            entry = self._data["models"].setdefault(model_id, {})
            entry["status"] = status
            entry["updated_at"] = datetime.now(timezone.utc).isoformat()
            if commit_sha:
                entry["commit_sha"] = commit_sha
            if total_bytes is not None:
                entry["total_bytes"] = total_bytes
            if error:
                entry["error"] = error
            if drive:
                entry["drive"] = drive
            if status == STATUS_COMPLETE:
                entry["completed_at"] = datetime.now(timezone.utc).isoformat()
                entry.pop("error", None)
        self._save()

    def increment_retries(self, model_id: str) -> int:
        with self._lock:
            entry = self._data["models"].setdefault(model_id, {})
            entry["retries"] = entry.get("retries", 0) + 1
        self._save()
        return entry["retries"]

    def get_retries(self, model_id: str) -> int:
        return self._data["models"].get(model_id, {}).get("retries", 0)

    def is_complete(self, model_id: str) -> bool:
        return self.get_model_status(model_id) == STATUS_COMPLETE

    def all_statuses(self) -> dict[str, str]:
        return {mid: d.get("status", STATUS_PENDING) for mid, d in self._data["models"].items()}

    def summary(self) -> dict:
        counts: dict[str, int] = {}
        for d in self._data["models"].values():
            s = d.get("status", STATUS_PENDING)
            counts[s] = counts.get(s, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # Run log
    # ------------------------------------------------------------------

    def start_run(self) -> None:
        self._data.setdefault("runs", []).append({
            "started_at": datetime.now(timezone.utc).isoformat(),
        })
        self._save()

    def end_run(self, summary: dict) -> None:
        runs = self._data.get("runs", [])
        if runs:
            runs[-1]["ended_at"] = datetime.now(timezone.utc).isoformat()
            runs[-1]["summary"] = summary
        self._save()


# ------------------------------------------------------------------
# Archive replication
# ------------------------------------------------------------------

def sync_archive(primary: Path, replica_roots: list[Path]) -> None:
    """
    Copy the primary archive/ directory to archive/ on each replica drive.
    Uses shutil.copy2 — safe for small metadata files; skips weight files.
    """
    if not primary.exists():
        return
    for root in replica_roots:
        dest = root / "archive"
        try:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(primary, dest)
            log.debug("Synced archive → %s", dest)
        except Exception as e:
            log.warning("Could not sync archive to %s: %s", dest, e)
