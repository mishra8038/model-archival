"""
Console display (rich Live) and STATUS.md writer.
Both are updated from SchedulerStats by the scheduler callbacks.
"""

from __future__ import annotations

import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import psutil
from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

from archiver.models import Registry
from archiver.scheduler import SchedulerStats
from archiver.state import RunState

STATUS_MD_REFRESH_SECS = 60
HEARTBEAT_REFRESH_SECS = 2


def _fmt_bytes(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(b) < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024  # type: ignore[assignment]
    return f"{b:.1f} PB"


def _fmt_eta(secs: Optional[float]) -> str:
    if secs is None or secs <= 0:
        return "—"
    h, rem = divmod(int(secs), 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}h {m}m"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def _fmt_speed(mbps: float) -> str:
    if mbps >= 1000:
        return f"{mbps/1024:.1f} GB/s"
    return f"{mbps:.0f} MB/s"


class StatusDisplay:
    """
    Handles both the rich live console display (TTY) and STATUS.md file writing.
    Thread-safe: update() can be called from any thread.
    """

    def __init__(
        self,
        registry: Registry,
        state: RunState,
        status_md_path: Path,
        total_bytes: int = 0,
    ) -> None:
        self.registry = registry
        self.state = state
        self.status_md_path = status_md_path
        self.total_bytes = total_bytes
        self._tty = sys.stdout.isatty()
        self._console = Console()
        self._lock = threading.Lock()
        self._stats: Optional[SchedulerStats] = None
        self._live: Optional[Live] = None
        self._md_timer: Optional[threading.Timer] = None
        self._start_time = time.time()

    def start(self) -> None:
        if self._tty:
            self._live = Live(
                self._build_layout(),
                console=self._console,
                refresh_per_second=0.5,
                screen=False,
            )
            self._live.start()
        self._schedule_md_refresh()

    def stop(self) -> None:
        if self._live:
            self._live.stop()
        if self._md_timer:
            self._md_timer.cancel()
        self._write_status_md()  # final write

    def update(self, stats: SchedulerStats) -> None:
        with self._lock:
            self._stats = stats
        if self._live:
            self._live.update(self._build_layout())

    # ------------------------------------------------------------------
    # Rich layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> Layout:
        stats = self._stats
        layout = Layout()
        layout.split_column(
            Layout(self._overall_panel(stats), name="overall", size=3),
            Layout(self._active_panel(stats), name="active", size=8),
            Layout(
                Columns([
                    self._drives_panel(),
                    self._queue_panel(stats),
                ]),
                name="mid",
                size=9,
            ),
            Layout(self._completed_panel(stats), name="completed"),
        )
        return layout

    def _overall_panel(self, stats: Optional[SchedulerStats]) -> Panel:
        if stats is None or self.total_bytes == 0:
            return Panel("[dim]Initialising…[/]", title="Archive Progress")
        done = stats.done_bytes
        pct = done / self.total_bytes * 100 if self.total_bytes else 0
        bar_width = 40
        filled = int(bar_width * pct / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        eta = _fmt_eta(stats.eta_seconds)
        speed = _fmt_speed(stats.ewma_speed_mbps)
        text = (
            f"[green]{bar}[/]  {pct:.1f}%  "
            f"{_fmt_bytes(done)} / {_fmt_bytes(self.total_bytes)}  "
            f"[cyan]{speed}[/]  ETA: [yellow]{eta}[/]"
        )
        return Panel(text, title="Archive Progress")

    def _active_panel(self, stats: Optional[SchedulerStats]) -> Panel:
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
        table.add_column("Drive", width=6)
        table.add_column("Model", width=40)
        table.add_column("Status")
        if stats and stats.active:
            for drive, model_id in stats.active.items():
                table.add_row(drive.upper(), model_id, "[yellow]downloading…[/]")
        else:
            table.add_row("—", "—", "[dim]idle[/]")
        return Panel(table, title="Active Downloads")

    def _drives_panel(self) -> Panel:
        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column("Drive", width=4)
        table.add_column("Bar", width=22)
        table.add_column("Usage", width=16)
        for label, drive in self.registry.drives.items():
            mp = drive.mount_point
            try:
                usage = psutil.disk_usage(str(mp))
                used_gb = usage.used / 1024**3
                total_gb = usage.total / 1024**3
                pct = usage.percent
                bar_w = 20
                filled = int(bar_w * pct / 100)
                bar = f"[green]{'█' * filled}[/][dim]{'░' * (bar_w - filled)}[/]"
                table.add_row(label.upper(), bar, f"{used_gb:.1f}/{total_gb:.1f} TB")
            except Exception:
                table.add_row(label.upper(), "[red]unavailable[/]", "—")
        return Panel(table, title="Drive Usage", width=46)

    def _queue_panel(self, stats: Optional[SchedulerStats]) -> Panel:
        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column("Model")
        if stats and stats.pending:
            for mid in stats.pending[:8]:
                m = self.registry.get(mid)
                drive = f"({m.drive})" if m else ""
                table.add_row(f"{mid.split('/')[-1]} {drive}")
        else:
            table.add_row("[dim]—[/]")
        return Panel(table, title="Queue", width=32)

    def _completed_panel(self, stats: Optional[SchedulerStats]) -> Panel:
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
        table.add_column("Model", width=42)
        table.add_column("Drive", width=4)
        table.add_column("Size", width=10)
        table.add_column("Status", width=10)
        if stats:
            for mid in reversed(stats.completed[-10:]):
                m = self.registry.get(mid)
                data = self.state.get_model_data(mid)
                size = _fmt_bytes(data.get("total_bytes", 0))
                table.add_row(
                    mid.split("/")[-1],
                    (m.drive if m else "—").upper(),
                    size,
                    "[green]✓ verified[/]",
                )
            for mid in stats.failed:
                table.add_row(mid.split("/")[-1], "—", "—", "[red]✗ failed[/]")
        return Panel(table, title="Completed")

    # ------------------------------------------------------------------
    # STATUS.md
    # ------------------------------------------------------------------

    def _schedule_md_refresh(self) -> None:
        self._write_status_md()
        self._md_timer = threading.Timer(STATUS_MD_REFRESH_SECS, self._schedule_md_refresh)
        self._md_timer.daemon = True
        self._md_timer.start()

    def _write_status_md(self) -> None:
        with self._lock:
            stats = self._stats

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        elapsed = time.time() - self._start_time

        lines = [
            "# Archive Status",
            f"_Last updated: {now} — auto-refreshed every ~{STATUS_MD_REFRESH_SECS}s_",
            "",
            "## Overall Progress",
        ]

        if stats and self.total_bytes > 0:
            pct = stats.done_bytes / self.total_bytes * 100
            n_complete = len(stats.completed)
            n_active = len(stats.active)
            n_pending = len(stats.pending)
            n_failed = len(stats.failed)
            lines += [
                f"- **Total:** {_fmt_bytes(self.total_bytes)} across {len(self.registry.models)} models",
                f"- **Downloaded:** {_fmt_bytes(stats.done_bytes)} ({pct:.1f}%) — "
                f"{n_complete} complete, {n_active} in progress, {n_pending} pending, {n_failed} failed",
                f"- **Speed:** {_fmt_speed(stats.ewma_speed_mbps)}",
                f"- **ETA:** {_fmt_eta(stats.eta_seconds)}",
                f"- **Elapsed:** {_fmt_eta(elapsed)}",
            ]
        else:
            lines.append("- Initialising…")

        lines += ["", "## Active Downloads",
                  "| Drive | Model | Speed |",
                  "|-------|-------|-------|"]
        if stats and stats.active:
            for drive, model_id in stats.active.items():
                lines.append(f"| {drive.upper()} | {model_id} | {_fmt_speed(stats.ewma_speed_mbps)} |")
        else:
            lines.append("| — | — | — |")

        lines += ["", "## Completed Models",
                  "| Model | Tier | Drive | Size | Status | Completed At |",
                  "|-------|------|-------|------|--------|--------------|"]
        if stats:
            for mid in reversed(stats.completed):
                m = self.registry.get(mid)
                data = self.state.get_model_data(mid)
                lines.append(
                    f"| {mid} | {m.tier if m else '?'} | {(m.drive if m else '?').upper()} "
                    f"| {_fmt_bytes(data.get('total_bytes', 0))} | ✓ | "
                    f"{data.get('completed_at', '—')[:16]} |"
                )

        lines += ["", "## Failed / Skipped",
                  "| Model | Reason |",
                  "|-------|--------|"]
        if stats and stats.failed:
            for mid in stats.failed:
                data = self.state.get_model_data(mid)
                lines.append(f"| {mid} | {data.get('error', '—')} |")
        else:
            lines.append("| — | — |")

        lines += ["", "## Drive Usage",
                  "| Drive | Mount | Used | Free | Total |",
                  "|-------|-------|------|------|-------|"]
        for label, drive in self.registry.drives.items():
            try:
                u = psutil.disk_usage(str(drive.mount_point))
                lines.append(
                    f"| {label.upper()} | {drive.mount_point} "
                    f"| {u.used/1024**3:.1f} TB | {u.free/1024**3:.1f} TB "
                    f"| {u.total/1024**3:.1f} TB |"
                )
            except Exception:
                lines.append(f"| {label.upper()} | {drive.mount_point} | N/A | N/A | N/A |")

        content = "\n".join(lines) + "\n"
        tmp = self.status_md_path.with_suffix(".md.tmp")
        try:
            tmp.write_text(content, encoding="utf-8")
            tmp.replace(self.status_md_path)
        except Exception as e:
            pass  # Non-fatal — don't crash the downloader over a status file
