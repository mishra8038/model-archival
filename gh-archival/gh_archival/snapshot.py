from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from gh_archival.github_client import RepoInfo


class SnapshotError(Exception):
    """One repo failed to archive; message describes the repo and cause."""


def safe_archive_basename(full_name: str) -> str:
    return full_name.replace("/", "__")


def authenticated_clone_url(full_name: str, token: str) -> str:
    return f"https://x-access-token:{token}@github.com/{full_name}.git"


def clone_and_git_archive(
    repo: RepoInfo,
    token: str,
    dest_tgz: Path,
    *,
    depth: int = 1,
    timeout_clone: int = 7200,
    timeout_archive: int = 3600,
) -> None:
    """
    Shallow-clone default branch into a temp dir, then `git archive` to a .tar.gz
    (no .git directory in the artifact).
    """
    dest_tgz = dest_tgz.resolve()
    dest_tgz.parent.mkdir(parents=True, exist_ok=True)
    tmp_root = dest_tgz.parent / ".tmp-clones"
    tmp_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=str(tmp_root)) as td:
        clone_path = Path(td) / "repo"
        url = authenticated_clone_url(repo.full_name, token)
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        try:
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    str(depth),
                    "--single-branch",
                    "--branch",
                    repo.default_branch,
                    url,
                    str(clone_path),
                ],
                check=True,
                timeout=timeout_clone,
                env=env,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            err = (e.stderr or e.stdout or str(e)).strip()
            raise SnapshotError(f"{repo.full_name}: git clone failed: {err}") from e
        except subprocess.TimeoutExpired as e:
            raise SnapshotError(f"{repo.full_name}: git clone timed out") from e

        tmp_tar = dest_tgz.with_suffix(dest_tgz.suffix + ".partial")
        if tmp_tar.exists():
            tmp_tar.unlink()
        try:
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(clone_path),
                    "archive",
                    "--format=tar.gz",
                    "--output",
                    str(tmp_tar),
                    "HEAD",
                ],
                check=True,
                timeout=timeout_archive,
                env=env,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            err = (e.stderr or e.stdout or str(e)).strip()
            if tmp_tar.exists():
                tmp_tar.unlink()
            raise SnapshotError(f"{repo.full_name}: git archive failed: {err}") from e
        except subprocess.TimeoutExpired as e:
            if tmp_tar.exists():
                tmp_tar.unlink()
            raise SnapshotError(f"{repo.full_name}: git archive timed out") from e

        os.replace(tmp_tar, dest_tgz)


def clone_repo_tree(
    repo: RepoInfo,
    token: str,
    dest_dir: Path,
    *,
    depth: int = 1,
    timeout_clone: int = 7200,
) -> None:
    """Shallow clone with .git retained under dest_dir (named safe_archive_basename)."""
    dest_dir = dest_dir.resolve()
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    url = authenticated_clone_url(repo.full_name, token)
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                str(depth),
                "--single-branch",
                "--branch",
                repo.default_branch,
                url,
                str(dest_dir),
            ],
            check=True,
            timeout=timeout_clone,
            env=env,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        err = (e.stderr or e.stdout or str(e)).strip()
        raise SnapshotError(f"{repo.full_name}: git clone failed: {err}") from e
    except subprocess.TimeoutExpired as e:
        raise SnapshotError(f"{repo.full_name}: git clone timed out") from e
