"""
Drive-aware download scheduler.

Maximize simultaneous downloads (bandwidth permitting):
- Worker pool of max_parallel_models threads. Each worker picks the next model from any
  drive that has pending work and is under that drive's concurrency cap (max_models_per_drive).
- Add more models only when average speed per model would stay >= min_speed_per_model_mbps
  (default 6 MB/s). So when aggregate speed / (active + 1) < 6 we wait before starting another.
- A background thread samples aggregate speed for ETA and for the 6 MB/s gating.
"""

from __future__ import annotations

import logging
import os
import random
import signal
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from archiver.models import ModelEntry, Registry
from archiver.state import RunState, STATUS_COMPLETE, STATUS_FAILED, STATUS_SKIPPED, STATUS_IN_PROGRESS

log = logging.getLogger(__name__)

SAMPLE_INTERVAL_S = 10   # speed sample interval for ETA and add-on gating
EWMA_ALPHA = 0.1
ACTIVITY_LOG_SPEED_INTERVAL = 6
MIN_SPEED_PER_MODEL_MBPS = 6.0   # only add another model if avg would stay >= this
ADD_ON_WAIT_S = 10               # recheck interval when waiting for headroom
RETRY_BACKOFF_MIN_S = 60         # min seconds before retrying a failed model (network blips)
RETRY_BACKOFF_MAX_S = 300        # max seconds (spread load when many failed at once)


@dataclass
class SchedulerStats:
    # drive → list of model_id (multiple active per drive)
    active: dict[str, list[str]] = field(default_factory=dict)
    completed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)
    speeds_mbps: dict[str, float] = field(default_factory=dict)
    total_bytes: int = 0
    done_bytes: int = 0
    ewma_speed_mbps: float = 0.0
    eta_seconds: Optional[float] = None


class DriveScheduler:
    """
    Worker-pool scheduler: maximize concurrent models subject to per-drive cap and
    minimum speed per model (add more only when aggregate / (n+1) >= min_speed_mbps).
    """

    def __init__(
        self,
        registry: Registry,
        state: RunState,
        download_fn: Callable[[ModelEntry], dict],
        get_speed_fn: Callable[[], float],
        on_model_complete: Optional[Callable[[ModelEntry, dict], None]] = None,
        on_model_failed: Optional[Callable[[ModelEntry, str], None]] = None,
        on_status_update: Optional[Callable[[SchedulerStats], None]] = None,
        token_accessible: Optional[dict[str, bool]] = None,
        max_parallel_models: int = 12,
        max_models_per_drive: int = 4,
        min_speed_per_model_mbps: float = MIN_SPEED_PER_MODEL_MBPS,
        activity_log_path: Optional[Path] = None,
    ) -> None:
        self.registry = registry
        self.state = state
        self.download_fn = download_fn
        self.get_speed_fn = get_speed_fn
        self.on_model_complete = on_model_complete
        self.on_model_failed = on_model_failed
        self.on_status_update = on_status_update
        self.token_accessible = token_accessible or {}
        self.max_parallel_models = max_parallel_models
        self.max_models_per_drive = max_models_per_drive
        self.min_speed_per_model_mbps = min_speed_per_model_mbps
        self._activity_log_path = activity_log_path
        self._activity_lock = threading.Lock()
        self._sampler_tick = 0

        self._queues: dict[str, deque[ModelEntry]] = defaultdict(deque)
        self._ewma_speed = 0.0

        self._stats = SchedulerStats()
        self._stop_event = threading.Event()
        self._workers: list[threading.Thread] = []
        # drive → list of model_id currently downloading (for gating + display)
        self._active_drives: dict[str, list[str]] = defaultdict(list)
        self._work_condition = threading.Condition()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_queue(self, models: list[ModelEntry]) -> None:
        """Populate per-drive queues. Called before run()."""
        skipped = 0
        for m in models:
            if self.state.is_complete(m.id):
                log.debug("Already complete, skipping: %s", m.id)
                continue
            if m.requires_auth and not self.token_accessible.get(m.id, True):
                log.warning("Skipping gated model (no token access): %s", m.id)
                self.state.set_model_status(m.id, STATUS_SKIPPED, error="No HF token access")
                skipped += 1
                continue
            if m.requires_auth and not self.token_accessible:
                # Token not set at all — skip priority-2
                if m.priority >= 2:
                    log.info("Deferring gated model (no HF_TOKEN): %s", m.id)
                    continue
            self._queues[m.drive].append(m)

        total = sum(len(q) for q in self._queues.values())
        log.info(
            "Queue built: %d models across %d drives (%d skipped)",
            total, len(self._queues), skipped
        )
        self._stats.pending = [m.id for q in self._queues.values() for m in q]

    def _log_activity(self, line: str) -> None:
        """Append one line to the activity log (thread-safe)."""
        if not self._activity_log_path:
            return
        with self._activity_lock:
            try:
                with open(self._activity_log_path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
                    f.flush()
            except Exception as e:
                log.debug("Activity log write failed: %s", e)

    def run(self) -> SchedulerStats:
        """Start worker pool and block until all queues are drained or shutdown requested."""
        total_pending = sum(len(q) for q in self._queues.values())
        if total_pending == 0:
            log.info("Nothing to download.")
            return self._stats

        n_workers = min(self.max_parallel_models, total_pending)
        self._log_activity(
            f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} RUN_START "
            f"workers={n_workers} max_per_drive={self.max_models_per_drive} "
            f"min_speed_mbps={self.min_speed_per_model_mbps}"
        )

        if threading.current_thread() is threading.main_thread():
            def _handle_signal(signum, frame):
                sig_name = signal.Signals(signum).name
                log.warning(
                    "Signal %s received — stopping after current shards finish. "
                    "Downloads are resumable.",
                    sig_name,
                )
                self._stop_event.set()
            signal.signal(signal.SIGTERM, _handle_signal)
            signal.signal(signal.SIGINT,  _handle_signal)

        for i in range(n_workers):
            t = threading.Thread(
                target=self._worker,
                name=f"worker-{i}",
                daemon=True,
            )
            self._workers.append(t)
            t.start()

        sampler = threading.Thread(
            target=self._sampler_loop, daemon=True, name="bandwidth-sampler"
        )
        sampler.start()

        for t in self._workers:
            t.join()

        self._stop_event.set()
        sampler.join(timeout=5)
        self._log_activity(
            f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} RUN_END "
            f"completed={len(self._stats.completed)} failed={len(self._stats.failed)}"
        )
        return self._stats

    # ------------------------------------------------------------------
    # Worker thread
    # ------------------------------------------------------------------

    def _worker(self) -> None:
        while not self._stop_event.is_set():
            pair = self._next_model()
            if pair is None:
                break
            drive, model = pair
            self._run_model(model, drive)
        log.debug("Worker finished")

    def _next_model(self) -> Optional[tuple[str, ModelEntry]]:
        """Get next (drive, model) or None. Waits when at cap or when adding one more would drop avg below min_speed."""
        with self._work_condition:
            while not self._stop_event.is_set():
                n_active = sum(len(v) for v in self._active_drives.values())
                if n_active >= self.max_parallel_models:
                    self._work_condition.wait(timeout=ADD_ON_WAIT_S)
                    continue
                speed = self.get_speed_fn()
                if n_active > 0 and speed / (n_active + 1) < self.min_speed_per_model_mbps:
                    self._work_condition.wait(timeout=ADD_ON_WAIT_S)
                    continue
                # Pick a drive with pending and under per-drive cap
                for drive in sorted(self._queues.keys()):
                    if not self._queues[drive]:
                        continue
                    if len(self._active_drives[drive]) >= self.max_models_per_drive:
                        continue
                    model = self._queues[drive].popleft()
                    self._active_drives[drive].append(model.id)
                    self._sync_active_to_stats()
                    return (drive, model)
                self._work_condition.wait(timeout=ADD_ON_WAIT_S)
        return None

    def _sync_active_to_stats(self) -> None:
        """Copy _active_drives to _stats.active for display."""
        self._stats.active = {d: list(ids) for d, ids in self._active_drives.items() if ids}

    def _run_model(self, model: ModelEntry, drive: str) -> None:
        # Random backoff before retrying a previously failed model (e.g. after network outage)
        if self.state.get_model_status(model.id) == STATUS_FAILED:
            backoff = random.uniform(RETRY_BACKOFF_MIN_S, RETRY_BACKOFF_MAX_S)
            log.info("Retrying failed model %s after %.0f s random backoff", model.id, backoff)
            time.sleep(backoff)

        start_time = time.time()
        self.state.set_model_status(model.id, STATUS_IN_PROGRESS, drive=drive)
        if model.id in self._stats.pending:
            self._stats.pending.remove(model.id)
        self._log_activity(
            f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} MODEL_START {drive} {model.id}"
        )
        self._emit_status()

        try:
            manifest = self.download_fn(model)
            total_bytes = manifest.get("total_size_bytes", 0) if manifest else 0
            duration_s = int(time.time() - start_time)
            size_gb = round(total_bytes / (1024**3), 2) if total_bytes else 0
            self.state.set_model_status(
                model.id, STATUS_COMPLETE,
                commit_sha=model.commit_sha,
                total_bytes=total_bytes,
                drive=drive,
            )
            self._stats.completed.append(model.id)
            self._stats.done_bytes += total_bytes
            self._log_activity(
                f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} MODEL_DONE {drive} {model.id} size_gb={size_gb} duration_s={duration_s}"
            )
            if self.on_model_complete:
                self.on_model_complete(model, manifest or {})
            log.info("✓ %s complete", model.id)

        except Exception as e:
            err_msg = str(e).replace("\n", " ")[:200]
            self.state.set_model_status(model.id, STATUS_FAILED, error=str(e))
            self._stats.failed.append(model.id)
            self._log_activity(
                f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} MODEL_FAIL {drive} {model.id} error={err_msg}"
            )
            if self.on_model_failed:
                self.on_model_failed(model, str(e))
            log.error("✗ %s failed: %s", model.id, e)

        finally:
            with self._work_condition:
                self._active_drives[drive].remove(model.id)
                if not self._active_drives[drive]:
                    del self._active_drives[drive]
                self._sync_active_to_stats()
                self._work_condition.notify_all()
            self._emit_status()

    # ------------------------------------------------------------------
    # Bandwidth sampler
    # ------------------------------------------------------------------

    def _sampler_loop(self) -> None:
        while not self._stop_event.wait(timeout=SAMPLE_INTERVAL_S):
            try:
                speed = self.get_speed_fn()
                if self._ewma_speed == 0:
                    self._ewma_speed = speed
                else:
                    self._ewma_speed = EWMA_ALPHA * speed + (1 - EWMA_ALPHA) * self._ewma_speed
                self._stats.ewma_speed_mbps = self._ewma_speed
                # Estimate remaining bytes and ETA based on average size of completed models.
                # This gives a coarse ETA for the whole queue without needing registry sizes.
                if self._stats.completed and self._ewma_speed > 0:
                    avg_size = self._stats.done_bytes / max(len(self._stats.completed), 1)
                    n_active = sum(len(v) for v in self._stats.active.values())
                    remaining_models = len(self._stats.pending) + n_active
                    est_remaining = avg_size * remaining_models
                    self._stats.total_bytes = self._stats.done_bytes + int(est_remaining)
                else:
                    self._stats.total_bytes = 0
                    self._stats.eta_seconds = None
                if self._stats.total_bytes > self._stats.done_bytes and self._ewma_speed >= 0.1:
                    remaining = self._stats.total_bytes - self._stats.done_bytes
                    eta = remaining / (self._ewma_speed * 1024 * 1024)
                    self._stats.eta_seconds = eta if eta < 1e10 else None  # avoid overflow in logs
                else:
                    if self._ewma_speed < 0.1:
                        self._stats.eta_seconds = None
                self._sampler_tick += 1
                if self._sampler_tick >= ACTIVITY_LOG_SPEED_INTERVAL:
                    self._sampler_tick = 0
                    n_active = sum(len(v) for v in self._stats.active.values())
                    eta_s = self._stats.eta_seconds if self._stats.eta_seconds is not None and self._stats.eta_seconds < 1e10 else 0
                    self._log_activity(
                        f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} SPEED mbps={self._ewma_speed:.1f} active_models={n_active} eta_s={eta_s:.0f}"
                    )
                self._emit_status()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Status emission
    # ------------------------------------------------------------------

    def _emit_status(self) -> None:
        if self.on_status_update:
            try:
                self.on_status_update(self._stats)
            except Exception:
                pass
