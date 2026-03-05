"""aria2c daemon lifecycle and download task management via aria2p."""

from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import aria2p

log = logging.getLogger(__name__)

ARIA2_PORT = 6800
ARIA2_SECRET = "archiver-local"
ARIA2_CONNECTIONS_PER_FILE = 8
ARIA2_MAX_CONCURRENT = 4


@dataclass
class DownloadTask:
    gid: str
    url: str
    dest: Path
    model_id: str
    filename: str


class Aria2Manager:
    """Manages a local aria2c RPC daemon and wraps aria2p for task control."""

    def __init__(
        self,
        tmp_dir: Path,
        connections_per_file: int = ARIA2_CONNECTIONS_PER_FILE,
        max_concurrent: int = ARIA2_MAX_CONCURRENT,
        port: int = ARIA2_PORT,
        secret: str = ARIA2_SECRET,
    ) -> None:
        self.tmp_dir = tmp_dir
        self.connections_per_file = connections_per_file
        self.max_concurrent = max_concurrent
        self.port = port
        self.secret = secret
        self._proc: Optional[subprocess.Popen] = None
        self._api: Optional[aria2p.API] = None

    # ------------------------------------------------------------------
    # Daemon lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if not shutil.which("aria2c"):
            raise RuntimeError(
                "aria2c not found in PATH.\n"
                "Install with:  sudo apt install aria2   (Debian/Ubuntu)\n"
                "               sudo pacman -S aria2     (Arch)\n"
                "               sudo dnf install aria2   (Fedora)"
            )
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            "aria2c",
            "--enable-rpc",
            f"--rpc-listen-port={self.port}",
            f"--rpc-secret={self.secret}",
            "--rpc-listen-all=false",
            f"--max-concurrent-downloads={self.max_concurrent}",
            f"--split={self.connections_per_file}",
            f"--max-connection-per-server={self.connections_per_file}",
            "--continue=true",           # resume partial downloads
            "--auto-file-renaming=false",
            "--allow-overwrite=true",
            "--retry-wait=30",
            "--max-tries=5",
            "--timeout=300",
            "--connect-timeout=60",
            "--piece-length=32M",        # large pieces suit multi-GB files
            f"--dir={self.tmp_dir}",
            "--daemon=false",            # we manage the process ourselves
            "--quiet=true",
            "--log-level=warn",
        ]
        log.info("Starting aria2c daemon on port %d", self.port)
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid,
        )
        # Wait for RPC to be ready
        self._api = aria2p.API(
            aria2p.Client(host="http://localhost", port=self.port, secret=self.secret)
        )
        for _ in range(20):
            try:
                self._api.get_stats()
                log.info("aria2c daemon ready")
                return
            except Exception:
                time.sleep(0.5)
        raise RuntimeError("aria2c daemon did not start within 10 seconds")

    def stop(self) -> None:
        if self._proc is not None:
            log.info("Stopping aria2c daemon (pid %d)", self._proc.pid)
            try:
                os.killpg(os.getpgid(self._proc.pid), signal.SIGTERM)
                self._proc.wait(timeout=10)
            except Exception:
                self._proc.kill()
            self._proc = None
            self._api = None

    def __enter__(self) -> "Aria2Manager":
        self.start()
        return self

    def __exit__(self, *_) -> None:
        self.stop()

    @property
    def api(self) -> aria2p.API:
        if self._api is None:
            raise RuntimeError("Aria2Manager not started — call start() first")
        return self._api

    # ------------------------------------------------------------------
    # Task submission
    # ------------------------------------------------------------------

    def add_download(
        self,
        url: str,
        dest_dir: Path,
        filename: str,
        model_id: str,
        hf_token: Optional[str] = None,
        speed_limit_mbps: Optional[int] = None,
    ) -> DownloadTask:
        """Submit a single file download to aria2c. Returns a DownloadTask."""
        dest_dir.mkdir(parents=True, exist_ok=True)

        # If a partial file exists but its .aria2 control file does not, aria2 refuses
        # to resume (it would truncate to 0 without the control file's byte-range map).
        # Remove the orphaned partial so aria2 starts a fresh download for this file.
        partial = dest_dir / filename
        control = dest_dir / (filename + ".aria2")
        if partial.exists() and not control.exists():
            log.warning("Removing orphaned partial (no .aria2 control file): %s", partial)
            partial.unlink()

        options: dict = {
            "dir": str(dest_dir),
            "out": filename,
            "auto-file-renaming": "false",
            "allow-overwrite": "true",
            "continue": "true",
        }
        if hf_token:
            options["header"] = f"Authorization: Bearer {hf_token}"
        if speed_limit_mbps:
            options["max-download-limit"] = f"{speed_limit_mbps}M"

        dl = self.api.add_uris([url], options=options)
        log.debug("Queued %s → %s/%s (gid=%s)", url[:80], dest_dir, filename, dl.gid)
        return DownloadTask(
            gid=dl.gid,
            url=url,
            dest=dest_dir / filename,
            model_id=model_id,
            filename=filename,
        )

    # ------------------------------------------------------------------
    # Status queries
    # ------------------------------------------------------------------

    def get_status(self, task: DownloadTask) -> aria2p.Download:
        return self.api.get_download(task.gid)

    def get_all_active(self) -> list[aria2p.Download]:
        return self.api.get_active()

    def wait_for_completion(
        self,
        task: DownloadTask,
        poll_interval: float = 2.0,
        on_progress=None,
    ) -> aria2p.Download:
        """Block until the given task completes or errors. Calls on_progress(dl) each poll."""
        while True:
            dl = self.get_status(task)
            status = dl.status
            if on_progress:
                on_progress(dl)
            if status == "complete":
                return dl
            if status == "error":
                raise RuntimeError(
                    f"aria2c error for {task.filename}: {dl.error_message}"
                )
            if status == "removed":
                raise RuntimeError(f"Download {task.filename} was removed unexpectedly")
            time.sleep(poll_interval)

    def aggregate_speed_mbps(self) -> float:
        """Return total current download speed across all active tasks in MB/s."""
        try:
            stats = self.api.get_stats()
            return stats.download_speed / (1024 * 1024)
        except Exception:
            return 0.0
