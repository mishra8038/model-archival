"""
Persistent run state — tracks which repos have been crawled so the tool
is fully resumable. Stored as a simple JSON file at the output root.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


STATUS_PENDING   = "pending"
STATUS_COMPLETE  = "complete"
STATUS_FAILED    = "failed"
STATUS_SKIPPED   = "skipped"   # e.g. gated repo without token


class RunState:
    def __init__(self, state_path: Path):
        self._path = state_path
        self._lock = threading.Lock()
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except Exception:
                return {}
        return {}

    def _save(self) -> None:
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._data, indent=2))
        tmp.replace(self._path)

    def get_status(self, hf_repo: str) -> str:
        return self._data.get(hf_repo, {}).get("status", STATUS_PENDING)

    def set_complete(self, hf_repo: str, crawled_at: str, file_count: int) -> None:
        with self._lock:
            self._data[hf_repo] = {
                "status": STATUS_COMPLETE,
                "crawled_at": crawled_at,
                "file_count": file_count,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save()

    def set_failed(self, hf_repo: str, error: str) -> None:
        with self._lock:
            self._data[hf_repo] = {
                "status": STATUS_FAILED,
                "error": str(error)[:500],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save()

    def set_skipped(self, hf_repo: str, reason: str) -> None:
        with self._lock:
            self._data[hf_repo] = {
                "status": STATUS_SKIPPED,
                "reason": reason,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save()

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {
            STATUS_PENDING: 0,
            STATUS_COMPLETE: 0,
            STATUS_FAILED: 0,
            STATUS_SKIPPED: 0,
        }
        for v in self._data.values():
            s = v.get("status", STATUS_PENDING)
            counts[s] = counts.get(s, 0) + 1
        return counts

    def all_entries(self) -> dict:
        return dict(self._data)
