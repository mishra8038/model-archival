"""
HuggingFace fingerprint crawler — release-oriented integrity reference.

Mission: record the SHA-256 of every weight file in a model's latest GA
release so that, in future, a copy obtained from any mirror (archive.org,
ModelScope, community torrents, etc.) can be verified for integrity.

Design principles:
  - Keyed on *release tag* (or "HEAD-main" fallback), not git commit SHA.
    A release tag is stable, appears on mirrors, and maps to downloadable
    artifacts.  A commit SHA is HF-internal and useless outside HF.
  - Records the canonical *source_url* for every file so a future verifier
    knows exactly what URL each hash corresponds to.
  - Per-file SHA-256 comes from HF's LFS metadata (no weight bytes fetched).
    These are the same hashes a downloader would verify against.
  - Zero bytes of weight data are downloaded.  Cost: 2-3 API calls per model.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from huggingface_hub import HfApi
from huggingface_hub.utils import GatedRepoError, RepositoryNotFoundError

log = logging.getLogger(__name__)

_WEIGHT_EXTENSIONS = {
    ".safetensors", ".bin", ".gguf", ".pt", ".pth", ".ggml",
}

HF_BASE = "https://huggingface.co"


@dataclass
class FileFingerprint:
    filename: str           # path within repo (e.g. "model-00001-of-00163.safetensors")
    sha256: str             # SHA-256 of the raw file bytes (from HF LFS metadata)
    size_bytes: int
    source_url: str         # canonical URL to download this exact file at this revision
    lfs_oid: str = ""       # HF LFS object ID (sha256 prefixed, for cross-reference)


@dataclass
class ReleaseFingerprint:
    """Fingerprint for one model release — the unit of verification."""

    hf_repo: str
    release_tag: str        # e.g. "main" / "v1.0" / "HEAD-main" (fallback)
    is_head_fallback: bool  # True when no formal tag exists
    commit_sha: str         # commit SHA at time of crawl (informational only)
    crawled_at: str         # ISO-8601 UTC
    files: list[FileFingerprint] = field(default_factory=list)

    @property
    def total_size_bytes(self) -> int:
        return sum(f.size_bytes for f in self.files)

    # Legacy alias so existing call sites that reference .commit_sha still work
    @property
    def hf_commit_sha(self) -> str:
        return self.commit_sha


class Crawler:
    """
    Crawls a HuggingFace model repo and returns a ReleaseFingerprint.

    Uses the HF API tree listing (expand=True) which includes LFS sha256
    inline — no pointer files downloaded, no commit history walked.
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

    def crawl(self, hf_repo: str) -> ReleaseFingerprint:
        """
        Crawl the latest release of *hf_repo* and return a ReleaseFingerprint.

        Raises PermissionError  for gated repos without a valid token.
        Raises FileNotFoundError for repos that don't exist.
        """
        crawled_at = datetime.now(timezone.utc).isoformat()

        # 1. Resolve the best available release tag
        release_tag, is_fallback = self._resolve_release_tag(hf_repo)

        # 2. Get the commit SHA at that tag (informational)
        commit_sha = self._get_commit_at_revision(hf_repo, release_tag)

        # 3. Enumerate weight files + SHA-256 from LFS metadata
        files = self._list_weight_files(hf_repo, commit_sha, release_tag)

        log.info(
            "%-55s  tag=%-20s  %3d files  %s",
            hf_repo,
            release_tag,
            len(files),
            _human_bytes(sum(f.size_bytes for f in files)),
        )

        return ReleaseFingerprint(
            hf_repo=hf_repo,
            release_tag=release_tag,
            is_head_fallback=is_fallback,
            commit_sha=commit_sha,
            crawled_at=crawled_at,
            files=files,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _resolve_release_tag(self, hf_repo: str) -> tuple[str, bool]:
        """
        Returns (tag, is_fallback).

        Tries repo tags first; falls back to "main" branch HEAD.
        Most HF model repos don't use git tags, so fallback is the common case.
        """
        for attempt in range(1, self._retry_attempts + 1):
            try:
                tags = list(self._api.list_repo_refs(
                    repo_id=hf_repo, repo_type="model"
                ).tags)
                if tags:
                    # Pick the most recently created tag
                    best = sorted(tags, key=lambda t: getattr(t, "target_commit", "") or "", reverse=True)[0]
                    return best.name, False
                # No tags — use main branch
                return "main", True
            except GatedRepoError as e:
                raise PermissionError(f"Gated repo: {hf_repo}") from e
            except RepositoryNotFoundError as e:
                raise FileNotFoundError(f"Repo not found: {hf_repo}") from e
            except Exception as e:
                if attempt == self._retry_attempts:
                    log.warning("Could not resolve tag for %s, using 'main': %s", hf_repo, e)
                    return "main", True
                if not self._handle_rate_limit(e):
                    time.sleep(self._retry_delay * attempt)
        return "main", True

    def _get_commit_at_revision(self, hf_repo: str, revision: str) -> str:
        for attempt in range(1, self._retry_attempts + 1):
            try:
                info = self._api.repo_info(
                    repo_id=hf_repo, repo_type="model", revision=revision
                )
                return info.sha or revision
            except GatedRepoError as e:
                raise PermissionError(f"Gated repo: {hf_repo}") from e
            except RepositoryNotFoundError as e:
                raise FileNotFoundError(f"Repo not found: {hf_repo}") from e
            except Exception as e:
                if attempt == self._retry_attempts:
                    return revision
                if not self._handle_rate_limit(e):
                    time.sleep(self._retry_delay * attempt)
        return revision

    def _list_weight_files(
        self, hf_repo: str, revision: str, release_tag: str
    ) -> list[FileFingerprint]:
        for attempt in range(1, self._retry_attempts + 1):
            try:
                tree = list(self._api.list_repo_tree(
                    repo_id=hf_repo,
                    repo_type="model",
                    revision=revision,
                    recursive=True,
                    expand=True,   # includes lfs sha256 + size inline
                ))
                files: list[FileFingerprint] = []
                for entry in tree:
                    if not any(entry.path.endswith(ext) for ext in _WEIGHT_EXTENSIONS):
                        continue
                    lfs = getattr(entry, "lfs", None)
                    sha256 = lfs.sha256 if lfs and getattr(lfs, "sha256", None) else ""
                    size   = (lfs.size if lfs and getattr(lfs, "size", None) else None) \
                             or getattr(entry, "size", 0) or 0
                    lfs_oid = getattr(lfs, "oid", "") if lfs else ""

                    if not sha256:
                        log.debug("  No LFS sha256 for %s/%s — skipping", hf_repo, entry.path)
                        continue

                    # Canonical download URL pinned to this exact commit
                    source_url = (
                        f"{HF_BASE}/{hf_repo}/resolve/{revision}/{entry.path}"
                    )

                    files.append(FileFingerprint(
                        filename=entry.path,
                        sha256=sha256,
                        size_bytes=size,
                        source_url=source_url,
                        lfs_oid=lfs_oid or "",
                    ))
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

    def _handle_rate_limit(self, exc: Exception) -> bool:
        msg = str(exc)
        if "429" not in msg and "rate limit" not in msg.lower():
            return False
        m = re.search(r"Retry after (\d+) seconds", msg)
        wait = int(m.group(1)) + 5 if m else 310
        log.warning("Rate-limited by HF — sleeping %ds …", wait)
        time.sleep(wait)
        return True


def _human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} PB"
