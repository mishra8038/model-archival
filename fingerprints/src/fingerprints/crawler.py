"""
HuggingFace fingerprint crawler.

For a given HF repo, fetches the file listing at HEAD (main branch) and
extracts the SHA-256 and size for every weight file directly from the HF
API tree response. The API includes LFS sha256 in the tree metadata —
no pointer files need to be fetched, no commit history is walked.

Cost per model: 1-2 API calls, ~1 second, zero bytes of weight data.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import re

from huggingface_hub import HfApi
from huggingface_hub.utils import (
    GatedRepoError,
    RepositoryNotFoundError,
)

log = logging.getLogger(__name__)

_WEIGHT_EXTENSIONS = {
    ".safetensors", ".bin", ".gguf", ".pt", ".pth", ".ggml",
}


@dataclass
class FileFingerprint:
    filename: str
    sha256: str
    size_bytes: int


@dataclass
class RepoFingerprint:
    hf_repo: str
    commit_sha: str          # HEAD commit at time of crawl
    crawled_at: str          # ISO-8601 UTC
    files: list[FileFingerprint] = field(default_factory=list)

    @property
    def total_size_bytes(self) -> int:
        return sum(f.size_bytes for f in self.files)


class Crawler:
    """
    Fetches the SHA-256 fingerprint of every weight file in a HF repo at HEAD.
    Uses the HF API tree listing which includes lfs sha256 inline — no pointer
    files are downloaded, no commit history is walked.
    """

    def __init__(
        self,
        hf_token: Optional[str] = None,
        retry_attempts: int = 5,
        retry_delay: float = 2.0,
    ):
        self._api = HfApi(token=hf_token)
        self._retry_attempts = retry_attempts
        self._retry_delay = retry_delay

    def _handle_rate_limit(self, exc: Exception) -> bool:
        """If exc is a 429, sleep for the Retry-After window and return True."""
        msg = str(exc)
        if "429" not in msg and "rate limit" not in msg.lower():
            return False
        m = re.search(r"Retry after (\d+) seconds", msg)
        wait = int(m.group(1)) + 5 if m else 310
        log.warning("Rate-limited by HF — sleeping %ds before retry …", wait)
        time.sleep(wait)
        return True

    def crawl(self, hf_repo: str) -> RepoFingerprint:
        """
        Crawl HEAD of *hf_repo* and return a RepoFingerprint.
        Raises PermissionError for gated repos without a valid token.
        Raises FileNotFoundError for repos that don't exist.
        """
        crawled_at = datetime.now(timezone.utc).isoformat()

        # Get HEAD commit sha
        commit_sha = self._get_head_commit(hf_repo)

        # List all files in the repo tree
        files = self._list_weight_files(hf_repo, commit_sha)

        log.info(
            "%-55s  %3d files  %s",
            hf_repo,
            len(files),
            _human_bytes(sum(f.size_bytes for f in files)),
        )

        return RepoFingerprint(
            hf_repo=hf_repo,
            commit_sha=commit_sha,
            crawled_at=crawled_at,
            files=files,
        )

    def _get_head_commit(self, hf_repo: str) -> str:
        for attempt in range(1, self._retry_attempts + 1):
            try:
                info = self._api.repo_info(repo_id=hf_repo, repo_type="model")
                return info.sha or "main"
            except GatedRepoError as e:
                raise PermissionError(f"Gated repo — token required: {hf_repo}") from e
            except RepositoryNotFoundError as e:
                raise FileNotFoundError(f"Repo not found: {hf_repo}") from e
            except Exception as e:
                if attempt == self._retry_attempts:
                    raise
                log.warning("repo_info attempt %d failed for %s: %s", attempt, hf_repo, e)
                if not self._handle_rate_limit(e):
                    time.sleep(self._retry_delay * attempt)
        return "main"

    def _list_weight_files(self, hf_repo: str, revision: str) -> list[FileFingerprint]:
        for attempt in range(1, self._retry_attempts + 1):
            try:
                tree = list(self._api.list_repo_tree(
                    repo_id=hf_repo,
                    repo_type="model",
                    revision=revision,
                    recursive=True,
                    expand=True,   # includes lfs sha256 + size inline
                ))
                files = []
                for entry in tree:
                    if not any(entry.path.endswith(ext) for ext in _WEIGHT_EXTENSIONS):
                        continue
                    lfs = getattr(entry, "lfs", None)
                    if lfs and getattr(lfs, "sha256", None):
                        files.append(FileFingerprint(
                            filename=entry.path,
                            sha256=lfs.sha256,
                            size_bytes=lfs.size or 0,
                        ))
                    else:
                        # Non-LFS file — size only, sha256 not available without download
                        size = getattr(entry, "size", 0) or 0
                        if size > 0:
                            log.debug("  Non-LFS weight file (no sha256): %s", entry.path)
                return files
            except GatedRepoError as e:
                raise PermissionError(f"Gated repo: {hf_repo}") from e
            except Exception as e:
                if attempt == self._retry_attempts:
                    raise
                log.warning("list_repo_tree attempt %d failed for %s: %s", attempt, hf_repo, e)
                if not self._handle_rate_limit(e):
                    time.sleep(self._retry_delay * attempt)
        return []


def _human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} PB"
