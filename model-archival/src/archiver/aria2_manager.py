"""aria2c daemon lifecycle and download task management via aria2p."""

from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import threading
import time
from datetime import datetime, time as dt_time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import aria2p

log = logging.getLogger(__name__)

ARIA2_PORT = 6800
ARIA2_SECRET = "archiver-local"
ARIA2_CONNECTIONS_PER_FILE = 8   # HTTP connections per file (CDN parallelism)
ARIA2_MAX_CONCURRENT = 16       # Max files in flight across all workers (disk + HF resolver friendly)


@dataclass
class DownloadTask:
    gid: str
    url: str
    dest: Path
    model_id: str
    filename: str


@dataclass(frozen=True)
class BandwidthSchedule:
    """Local-time bandwidth cap window for aria2.

    When the current local time falls inside [start_time, end_time), the global
    aria2 cap is ``cap_mbps`` MB/s. **Outside** that interval the limit is
    cleared (unlimited). For overnight full speed with a daytime neighbor cap,
    set the window to your *capped* hours, e.g. ``07:00-23:00``.
    """

    cap_mbps: float
    start_time: dt_time
    end_time: dt_time

    def is_active(self, now: Optional[dt_time] = None) -> bool:
        current = now or datetime.now().time()
        if self.start_time == self.end_time:
            return True
        if self.start_time < self.end_time:
            return self.start_time <= current < self.end_time
        return current >= self.start_time or current < self.end_time


class Aria2Manager:
    """Manages a local aria2c RPC daemon and wraps aria2p for task control."""

    def __init__(
        self,
        tmp_dir: Path,
        connections_per_file: int = ARIA2_CONNECTIONS_PER_FILE,
        max_concurrent: int = ARIA2_MAX_CONCURRENT,
        max_overall_download_limit_mbps: Optional[float] = None,
        bandwidth_schedule: Optional[BandwidthSchedule] = None,
        port: int = ARIA2_PORT,
        secret: str = ARIA2_SECRET,
        taper_after_seconds: Optional[float] = None,
        taper_to_mbps: Optional[float] = None,
    ) -> None:
        self.tmp_dir = tmp_dir
        self.connections_per_file = connections_per_file
        self.max_concurrent = max_concurrent
        self.max_overall_download_limit_mbps = max_overall_download_limit_mbps
        self.bandwidth_schedule = bandwidth_schedule
        self.taper_after_seconds = taper_after_seconds
        self.taper_to_mbps = taper_to_mbps
        self.port = port
        self.secret = secret
        self._proc: Optional[subprocess.Popen] = None
        self._api: Optional[aria2p.API] = None
        self._schedule_stop = threading.Event()
        self._schedule_thread: Optional[threading.Thread] = None
        self._taper_stop = threading.Event()
        self._taper_thread: Optional[threading.Thread] = None
        self._last_applied_limit_mbps: Optional[float] = None

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
            "--continue=true",
            "--auto-file-renaming=false",
            "--allow-overwrite=true",
            "--retry-wait=30",
            "--max-tries=5",
            "--timeout=300",
            "--connect-timeout=60",
            "--piece-length=32M",
            f"--dir={self.tmp_dir}",
            "--daemon=false",
            "--quiet=true",
            "--log-level=warn",
        ]
        if self.max_overall_download_limit_mbps is not None and self.max_overall_download_limit_mbps > 0:
            # aria2 expects bytes per second
            limit_bps = int(self.max_overall_download_limit_mbps * 1024 * 1024)
            cmd.append(f"--max-overall-download-limit={limit_bps}")
            log.info("Bandwidth cap: %.0f MB/s", self.max_overall_download_limit_mbps)
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
            # If port 6800 is still held by a *stale* aria2 from a crashed/killed archiver,
            # our child exits immediately but RPC still answers — we would then talk to the
            # old daemon and keep its bandwidth cap (e.g. 1 MiB/s). Fail fast instead.
            if self._proc.poll() is not None:
                code = self._proc.returncode
                raise RuntimeError(
                    f"aria2c exited on startup (exit {code}) — port {self.port} is probably "
                    "in use by another aria2c. Stop the stale daemon "
                    f"(e.g. `pkill -f 'aria2c.*rpc-listen-port={self.port}'`) and retry."
                )
            try:
                self._api.get_stats()
                log.info("aria2c daemon ready")
                self._apply_bandwidth_policy(force=True)
                if self.bandwidth_schedule is not None:
                    self._schedule_stop.clear()
                    self._schedule_thread = threading.Thread(
                        target=self._bandwidth_schedule_loop,
                        name="aria2-bandwidth-schedule",
                        daemon=True,
                    )
                    self._schedule_thread.start()
                elif (
                    self.taper_after_seconds is not None
                    and self.taper_after_seconds > 0
                    and self.taper_to_mbps is not None
                    and self.taper_to_mbps > 0
                    and self.max_overall_download_limit_mbps is not None
                    and self.max_overall_download_limit_mbps > 0
                ):
                    self._taper_stop.clear()
                    self._taper_thread = threading.Thread(
                        target=self._bandwidth_taper_loop,
                        name="aria2-bandwidth-taper",
                        daemon=True,
                    )
                    self._taper_thread.start()
                    log.info(
                        "Bandwidth taper: %.4g MB/s for %.0f s, then %.4g MB/s",
                        self.max_overall_download_limit_mbps,
                        self.taper_after_seconds,
                        self.taper_to_mbps,
                    )
                return
            except Exception:
                time.sleep(0.5)
        raise RuntimeError("aria2c daemon did not start within 10 seconds")

    def stop(self) -> None:
        self._schedule_stop.set()
        self._taper_stop.set()
        if self._schedule_thread is not None:
            self._schedule_thread.join(timeout=5)
            self._schedule_thread = None
        if self._taper_thread is not None:
            self._taper_thread.join(timeout=5)
            self._taper_thread = None
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

    def _scheduled_limit_mbps(self) -> Optional[float]:
        if self.bandwidth_schedule is None:
            return None
        if self.bandwidth_schedule.is_active():
            return self.bandwidth_schedule.cap_mbps
        return None

    def _apply_bandwidth_policy(self, force: bool = False) -> None:
        limit_mbps = self._scheduled_limit_mbps()
        if self.bandwidth_schedule is None:
            limit_mbps = self.max_overall_download_limit_mbps

        if not force and limit_mbps == self._last_applied_limit_mbps:
            return

        # Use bytes/sec (same as aria2 CLI) so RPC matches startup argv and sub-integer
        # caps (e.g. 0.75 MB/s) are not truncated by int() + "M".
        if limit_mbps is None or limit_mbps <= 0:
            limit_opt = "0"
        else:
            limit_opt = str(int(round(limit_mbps * 1024 * 1024)))
        options = {"max-overall-download-limit": limit_opt}
        self.api.set_global_options(options)
        self._last_applied_limit_mbps = limit_mbps

        if limit_mbps is None or limit_mbps <= 0:
            log.info("Bandwidth cap disabled")
        else:
            log.info("Bandwidth cap set to %.0f MB/s", limit_mbps)

    def _bandwidth_schedule_loop(self) -> None:
        while not self._schedule_stop.wait(30):
            try:
                self._apply_bandwidth_policy()
            except Exception as exc:
                log.warning("Failed to refresh bandwidth cap schedule: %s", exc)

    def _bandwidth_taper_loop(self) -> None:
        """After ``taper_after_seconds``, lower flat cap to ``taper_to_mbps`` (aria2 RPC)."""
        assert self.taper_after_seconds is not None and self.taper_after_seconds > 0
        deadline = time.monotonic() + float(self.taper_after_seconds)
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if self._taper_stop.wait(timeout=min(1.0, max(0.01, remaining))):
                return
        if self._proc is not None and self._proc.poll() is not None:
            return
        if self._api is None:
            return
        prev = self.max_overall_download_limit_mbps
        self.max_overall_download_limit_mbps = self.taper_to_mbps
        try:
            log.info(
                "Bandwidth taper: after %.0f s, cap %.4g → %.4g MB/s",
                self.taper_after_seconds,
                prev or 0,
                self.taper_to_mbps,
            )
            self._apply_bandwidth_policy(force=True)
        except Exception as exc:
            log.warning("Bandwidth taper apply failed: %s", exc)
