"""
Drive-aware download scheduler.

One worker thread per drive (D1–D4). Workers pull from a per-drive queue.
A bandwidth sampler decides whether to open additional drive slots.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Callable, Optional

from archiver.models import ModelEntry, Registry
from archiver.state import RunState, STATUS_COMPLETE, STATUS_FAILED, STATUS_SKIPPED, STATUS_IN_PROGRESS

log = logging.getLogger(__name__)

BANDWIDTH_SAMPLE_INTERVAL = 10   # seconds
BANDWIDTH_HEADROOM_PCT = 0.85    # open new slot only if utilisation < 85% of peak
EWMA_ALPHA = 0.1                 # smoothing factor for throughput EWMA


@dataclass
class SchedulerStats:
    active: dict[str, str] = field(default_factory=dict)   # drive → model_id
    completed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)
    speeds_mbps: dict[str, float] = field(default_factory=dict)  # drive → MB/s
    total_bytes: int = 0
    done_bytes: int = 0
    ewma_speed_mbps: float = 0.0
    eta_seconds: Optional[float] = None


class DriveScheduler:
    """
    Manages per-drive worker threads and feeds them models in priority order.
    """

    def __init__(
        self,
        registry: Registry,
        state: RunState,
        download_fn: Callable[[ModelEntry], dict],
        get_speed_fn: Callable[[], float],   # → aggregate MB/s
        on_model_complete: Optional[Callable[[ModelEntry, dict], None]] = None,
        on_model_failed: Optional[Callable[[ModelEntry, str], None]] = None,
        on_status_update: Optional[Callable[[SchedulerStats], None]] = None,
        token_accessible: Optional[dict[str, bool]] = None,
        max_parallel_drives: int = 4,
        bandwidth_cap_mbps: Optional[float] = None,
    ) -> None:
        self.registry = registry
        self.state = state
        self.download_fn = download_fn
        self.get_speed_fn = get_speed_fn
        self.on_model_complete = on_model_complete
        self.on_model_failed = on_model_failed
        self.on_status_update = on_status_update
        self.token_accessible = token_accessible or {}
        self.max_parallel_drives = max_parallel_drives
        self.bandwidth_cap_mbps = bandwidth_cap_mbps

        # Per-drive queues: drive_label → deque[ModelEntry]
        self._queues: dict[str, deque[ModelEntry]] = defaultdict(deque)
        self._queue_lock = threading.Lock()

        # Throughput tracking
        self._peak_speed = 0.0
        self._ewma_speed = 0.0
        self._speed_history: deque[float] = deque(maxlen=60)

        self._stats = SchedulerStats()
        self._stop_event = threading.Event()
        self._workers: list[threading.Thread] = []
        self._active_drives: dict[str, Optional[str]] = {}  # drive → model_id or None
        self._active_lock = threading.Lock()

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

    def run(self) -> SchedulerStats:
        """Start workers and block until all queues are drained."""
        active_drives = [d for d in self._queues if self._queues[d]]
        if not active_drives:
            log.info("Nothing to download.")
            return self._stats

        # Limit parallel drives
        active_drives = active_drives[:self.max_parallel_drives]

        for drive in active_drives:
            with self._active_lock:
                self._active_drives[drive] = None
            t = threading.Thread(
                target=self._worker,
                args=(drive,),
                name=f"worker-{drive}",
                daemon=True,
            )
            self._workers.append(t)
            t.start()

        # Bandwidth sampler + status updater
        sampler = threading.Thread(
            target=self._sampler_loop, daemon=True, name="bandwidth-sampler"
        )
        sampler.start()

        for t in self._workers:
            t.join()

        self._stop_event.set()
        sampler.join(timeout=5)
        return self._stats

    # ------------------------------------------------------------------
    # Worker thread
    # ------------------------------------------------------------------

    def _worker(self, drive: str) -> None:
        log.info("Worker started for drive %s", drive)
        while True:
            model = self._next_model(drive)
            if model is None:
                break
            self._run_model(model, drive)
        log.info("Worker finished for drive %s", drive)
        with self._active_lock:
            self._active_drives.pop(drive, None)

    def _next_model(self, drive: str) -> Optional[ModelEntry]:
        with self._queue_lock:
            if self._queues[drive]:
                return self._queues[drive].popleft()
        return None

    def _run_model(self, model: ModelEntry, drive: str) -> None:
        with self._active_lock:
            self._active_drives[drive] = model.id
        self.state.set_model_status(model.id, STATUS_IN_PROGRESS, drive=drive)
        if model.id in self._stats.pending:
            self._stats.pending.remove(model.id)
        self._stats.active[drive] = model.id
        self._emit_status()

        try:
            manifest = self.download_fn(model)
            total_bytes = manifest.get("total_size_bytes", 0) if manifest else 0
            self.state.set_model_status(
                model.id, STATUS_COMPLETE,
                commit_sha=model.commit_sha,
                total_bytes=total_bytes,
                drive=drive,
            )
            self._stats.completed.append(model.id)
            self._stats.done_bytes += total_bytes
            if self.on_model_complete:
                self.on_model_complete(model, manifest or {})
            log.info("✓ %s complete", model.id)

        except Exception as e:
            log.error("✗ %s failed: %s", model.id, e)
            self.state.set_model_status(model.id, STATUS_FAILED, error=str(e))
            self._stats.failed.append(model.id)
            if self.on_model_failed:
                self.on_model_failed(model, str(e))

        finally:
            self._stats.active.pop(drive, None)
            with self._active_lock:
                self._active_drives[drive] = None
            self._emit_status()

    # ------------------------------------------------------------------
    # Bandwidth sampler
    # ------------------------------------------------------------------

    def _sampler_loop(self) -> None:
        while not self._stop_event.wait(timeout=BANDWIDTH_SAMPLE_INTERVAL):
            try:
                speed = self.get_speed_fn()
                self._speed_history.append(speed)
                self._peak_speed = max(self._peak_speed, speed)
                if self._ewma_speed == 0:
                    self._ewma_speed = speed
                else:
                    self._ewma_speed = EWMA_ALPHA * speed + (1 - EWMA_ALPHA) * self._ewma_speed
                self._stats.ewma_speed_mbps = self._ewma_speed
                if self._stats.total_bytes > self._stats.done_bytes and self._ewma_speed > 0:
                    remaining = self._stats.total_bytes - self._stats.done_bytes
                    self._stats.eta_seconds = remaining / (self._ewma_speed * 1024 * 1024)
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
