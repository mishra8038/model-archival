from __future__ import annotations

import subprocess
from pathlib import Path


class RcloneError(Exception):
    pass


def rclone_available() -> bool:
    try:
        subprocess.run(
            ["rclone", "version"],
            capture_output=True,
            check=True,
            timeout=10,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def rclone_copy_local_to_remote(
    local_dir: Path,
    remote_spec: str,
    *,
    dry_run: bool = False,
    extra_args: list[str] | None = None,
) -> None:
    """
    Run `rclone copy LOCAL remote:path` where remote_spec is like `gdrive:Backups/gh-archival/run`.

    rclone must already be configured (`rclone config`).
    """
    local_dir = local_dir.resolve()
    if not local_dir.is_dir():
        raise RcloneError(f"Local path is not a directory: {local_dir}")

    cmd = ["rclone", "copy", str(local_dir), remote_spec, "--stats-one-line"]
    if dry_run:
        cmd.append("--dry-run")
    if extra_args:
        cmd.extend(extra_args)
    try:
        subprocess.run(cmd, check=True, timeout=86400)
    except FileNotFoundError as e:
        raise RcloneError("rclone not found; install https://rclone.org/install/") from e
    except subprocess.CalledProcessError as e:
        raise RcloneError(f"rclone copy failed with exit code {e.returncode}") from e
    except subprocess.TimeoutExpired as e:
        raise RcloneError("rclone copy timed out") from e
