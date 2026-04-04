from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Iterator

import httpx

GITHUB_API = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"


@dataclass(frozen=True)
class RepoInfo:
    full_name: str
    default_branch: str
    is_fork: bool
    archived: bool
    private: bool
    clone_url: str


def resolve_token(explicit: str | None) -> str:
    if explicit:
        return explicit.strip()
    env = os.environ.get("GITHUB_TOKEN", "").strip()
    if env:
        return env
    try:
        out = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        out = ""
    if out:
        return out
    raise RuntimeError(
        "No GitHub credentials: set GITHUB_TOKEN or run `gh auth login` "
        "so `gh auth token` works."
    )


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }


def iter_owned_repos(token: str, *, affiliation: str = "owner") -> Iterator[dict]:
    """Yield raw repo objects from GET /user/repos (paginated)."""
    page = 1
    per_page = 100
    with httpx.Client(timeout=60.0) as client:
        while True:
            r = client.get(
                f"{GITHUB_API}/user/repos",
                headers=_headers(token),
                params={
                    "affiliation": affiliation,
                    "per_page": per_page,
                    "page": page,
                    "sort": "full_name",
                },
            )
            r.raise_for_status()
            batch: list = r.json()
            if not batch:
                break
            yield from batch
            if len(batch) < per_page:
                break
            page += 1


def repo_dict_to_info(raw: dict) -> RepoInfo | None:
    full = raw.get("full_name") or ""
    if not full:
        return None
    branch = raw.get("default_branch") or ""
    if not branch:
        return None
    return RepoInfo(
        full_name=full,
        default_branch=branch,
        is_fork=bool(raw.get("fork")),
        archived=bool(raw.get("archived")),
        private=bool(raw.get("private")),
        clone_url=(raw.get("clone_url") or f"https://github.com/{full}.git"),
    )


def list_repos_for_snapshot(
    token: str,
    *,
    affiliation: str = "owner",
    require_default_branch: str | None = "main",
    include_forks: bool = False,
    include_archived: bool = True,
) -> list[RepoInfo]:
    out: list[RepoInfo] = []
    seen: set[str] = set()
    for raw in iter_owned_repos(token, affiliation=affiliation):
        info = repo_dict_to_info(raw)
        if info is None or info.full_name in seen:
            continue
        seen.add(info.full_name)
        if not include_forks and info.is_fork:
            continue
        if not include_archived and info.archived:
            continue
        if require_default_branch and info.default_branch != require_default_branch:
            continue
        out.append(info)
    out.sort(key=lambda r: r.full_name.lower())
    return out
