"""
Console display (rich Live), STATUS.md writer, and RunReport.

RunReport writes a timestamped Markdown run report to the logs directory
that captures the full session: pre-flight results, per-model outcomes
(start / complete / fail / skip), drive usage snapshots, and a final summary.
It is written incrementally so that if the process is interrupted the report
still contains everything up to that point.
"""

from __future__ import annotations

import platform
import socket
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
from rich.rule import Rule
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
        elapsed = time.time() - self._start_time
        elapsed_str = _fmt_eta(elapsed)
        if stats is None or self.total_bytes == 0:
            speed_str = _fmt_speed(stats.ewma_speed_mbps) if stats else "—"
            return Panel(
                f"[dim]Initialising…[/]  [cyan]{speed_str}[/]  elapsed: {elapsed_str}",
                title="Archive Progress",
            )
        done = stats.done_bytes
        pct = done / self.total_bytes * 100 if self.total_bytes else 0
        bar_width = 38
        filled = int(bar_width * pct / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        eta = _fmt_eta(stats.eta_seconds)
        speed = _fmt_speed(stats.ewma_speed_mbps)
        mbps_num = stats.ewma_speed_mbps
        speed_colour = "green" if mbps_num >= 20 else ("yellow" if mbps_num >= 5 else "red")
        text = (
            f"[green]{bar}[/]  {pct:.1f}%  "
            f"{_fmt_bytes(done)} / {_fmt_bytes(self.total_bytes)}  "
            f"[{speed_colour}]{speed}[/]  ETA: [yellow]{eta}[/]  elapsed: [dim]{elapsed_str}[/]"
        )
        return Panel(text, title="Archive Progress")

    def _active_panel(self, stats: Optional[SchedulerStats]) -> Panel:
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
        table.add_column("Drive", width=6)
        table.add_column("Model", width=38)
        table.add_column("Status", width=16)
        table.add_column("Speed", width=12)
        n_active = len(stats.active) if stats and stats.active else 0
        if stats and stats.active:
            # Divide aggregate speed evenly across active drives as an estimate
            per_drive_mbps = stats.ewma_speed_mbps / max(n_active, 1)
            mbps_colour = "green" if per_drive_mbps >= 10 else ("yellow" if per_drive_mbps >= 2 else "red")
            for drive, model_id in stats.active.items():
                table.add_row(
                    drive.upper(),
                    model_id,
                    "[yellow]downloading…[/]",
                    f"[{mbps_colour}]{_fmt_speed(per_drive_mbps)}[/]",
                )
        else:
            table.add_row("—", "—", "[dim]idle[/]", "—")
        # Footer line: aggregate speed + total active
        speed_total = _fmt_speed(stats.ewma_speed_mbps) if stats else "—"
        mbps_total = stats.ewma_speed_mbps if stats else 0.0
        mbps_col = "green" if mbps_total >= 20 else ("yellow" if mbps_total >= 5 else "red")
        title = (
            f"Active Downloads  [dim]│[/]  "
            f"total: [{mbps_col}]{speed_total}[/]  "
            f"([dim]{mbps_total*8:.0f} Mbps[/])"
        )
        return Panel(table, title=title)

    def _drives_panel(self) -> Panel:
        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column("Drive", width=4)
        table.add_column("Bar", width=22)
        table.add_column("Usage", width=16)
        for label, drive in self.registry.drives.items():
            mp = drive.mount_point
            try:
                usage = psutil.disk_usage(str(mp))
                # Use true tebibytes for TB display
                used_tb = usage.used / 1024**4
                total_tb = usage.total / 1024**4
                pct = usage.percent
                bar_w = 20
                filled = int(bar_w * pct / 100)
                bar = f"[green]{'█' * filled}[/][dim]{'░' * (bar_w - filled)}[/]"
                table.add_row(label.upper(), bar, f"{used_tb:.1f}/{total_tb:.1f} TB")
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
                used_tb = u.used / 1024**4
                free_tb = u.free / 1024**4
                total_tb = u.total / 1024**4
                lines.append(
                    f"| {label.upper()} | {drive.mount_point} "
                    f"| {used_tb:.1f} TB | {free_tb:.1f} TB "
                    f"| {total_tb:.1f} TB |"
                )
            except Exception:
                lines.append(f"| {label.upper()} | {drive.mount_point} | N/A | N/A | N/A |")

        content = "\n".join(lines) + "\n"
        tmp = self.status_md_path.with_suffix(".md.tmp")
        try:
            tmp.write_text(content, encoding="utf-8")
            tmp.replace(self.status_md_path)
        except Exception:
            pass  # Non-fatal — don't crash the downloader over a status file


# ---------------------------------------------------------------------------
# RunReport — timestamped Markdown report for the entire archiver session
# ---------------------------------------------------------------------------

def _h(b: int) -> str:
    """Human-readable byte size."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(b) < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024  # type: ignore[assignment]
    return f"{b:.1f} PB"


class RunReport:
    """
    Writes a timestamped Markdown run-report file to ``log_dir``.

    The report is written **incrementally** — each section is appended as
    events arrive so that an interrupted run still produces a useful record.

    Usage::

        report = RunReport(log_dir=logs_dir, registry=reg)
        report.open(hf_token_set=True, models=selected_models)
        ...
        report.record_model_start(model)
        report.record_model_complete(model, manifest)
        report.record_model_fail(model, reason)
        ...
        report.close(stats)
    """

    def __init__(self, log_dir: Path, registry: Registry) -> None:
        self.log_dir = log_dir
        self.registry = registry
        self._path: Optional[Path] = None
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._console = Console()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def path(self) -> Optional[Path]:
        return self._path

    def open(
        self,
        hf_token_set: bool,
        models: list,
        preflight_warnings: list[str] | None = None,
        preflight_token_results: dict[str, bool] | None = None,
        cli_args: dict | None = None,
    ) -> None:
        """Write the report header and pre-flight summary. Call once before downloads start."""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self._path = self.log_dir / f"run-report-{ts}.md"
        self._start_time = time.time()

        lines: list[str] = []
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        lines += [
            "# Archiver Run Report",
            "",
            f"**Started:** {now_str}  ",
            f"**Host:** {socket.gethostname()}  ",
            f"**Python:** {platform.python_version()}  ",
            f"**OS:** {platform.system()} {platform.release()}  ",
            "",
            "---",
            "",
        ]

        # CLI options summary
        if cli_args:
            lines += ["## Run Options", ""]
            lines += [f"| Option | Value |", "|--------|-------|"]
            for k, v in cli_args.items():
                lines.append(f"| `{k}` | `{v}` |")
            lines += ["", "---", ""]

        # Pre-flight
        lines += ["## Pre-flight", ""]
        lines.append(f"- HF token present: **{'yes' if hf_token_set else 'no'}**")

        if preflight_warnings:
            lines.append("")
            lines.append("**Warnings:**")
            for w in preflight_warnings:
                lines.append(f"- ⚠ {w}")

        if preflight_token_results:
            lines += ["", "**Token access:**", ""]
            lines += ["| Model | Accessible |", "|-------|------------|"]
            for mid, ok in preflight_token_results.items():
                lines.append(f"| {mid} | {'✔ yes' if ok else '✗ no'} |")

        lines += ["", "---", ""]

        # Model queue summary
        lines += ["## Download Queue", ""]
        lines += [
            f"| # | Model | Tier | Drive | P | Auth |",
            "|---|-------|------|-------|---|------|",
        ]
        for i, m in enumerate(models, 1):
            auth = "yes" if m.requires_auth else "no"
            lines.append(
                f"| {i} | `{m.id}` | {m.tier} | {m.drive.upper()} | {m.priority} | {auth} |"
            )

        lines += ["", "---", "", "## Model Events", ""]

        # Drive snapshot
        lines += self._drive_snapshot_section()
        lines += ["", "---", ""]

        self._write_lines(lines)

        # Print report path to console
        self._console.print(
            f"  [dim]Run report → [bold]{self._path}[/bold][/dim]"
        )

    def record_model_start(self, model) -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        lines = [
            f"### ▶ `{model.id}`",
            "",
            f"- **Started:** {ts}  ",
            f"- **Tier:** {model.tier}  Drive: {model.drive.upper()}  "
            f"Priority: {model.priority}  Auth: {'yes' if model.requires_auth else 'no'}",
            "",
        ]
        self._write_lines(lines)
        self._console.print(
            f"  [cyan]▶ START[/cyan]  [bold]{model.id}[/bold]  "
            f"[dim](tier {model.tier} / {model.drive.upper()})[/dim]"
        )

    def record_model_complete(self, model, manifest: dict) -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        total_bytes = manifest.get("total_size_bytes", 0)
        n_files = len(manifest.get("files", []))
        commit = (manifest.get("commit_sha") or model.commit_sha or "—")[:16]
        elapsed = time.time() - self._start_time

        lines = [
            f"- **Completed:** {ts}  ",
            f"- **Size:** {_h(total_bytes)}  Files: {n_files}  Commit: `{commit}`  ",
            f"- **Status:** ✔ COMPLETE",
            "",
        ]
        self._write_lines(lines)
        self._console.print(
            f"  [green]✔ DONE[/green]   [bold]{model.id}[/bold]  "
            f"[dim]{_h(total_bytes)} / {n_files} files / {commit}[/dim]"
        )

    def record_model_fail(self, model, reason: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        lines = [
            f"- **Failed:** {ts}  ",
            f"- **Error:** `{reason}`  ",
            f"- **Status:** ✗ FAILED",
            "",
        ]
        self._write_lines(lines)
        self._console.print(
            f"  [red]✗ FAIL[/red]   [bold]{model.id}[/bold]  [dim]{reason[:100]}[/dim]"
        )

    def record_verification(
        self,
        model_id: str,
        results: list[dict],
        *,
        re_hash: bool = False,
    ) -> None:
        """
        Record post-download checksum verification results in the report.

        ``results`` is the list returned by ``verifier.verify_model_dir``:
        each entry has ``path``, ``ok``, ``expected``, ``actual``, ``size_bytes``.

        ``re_hash=True`` means every file was fully re-hashed from disk (slow path);
        ``re_hash=False`` means only sidecar existence was confirmed (fast path used
        immediately after download when the digest is already known).
        """
        n_pass = sum(1 for r in results if r.get("ok"))
        n_fail = sum(1 for r in results if not r.get("ok"))
        total_bytes = sum(r.get("size_bytes", 0) for r in results)
        method = "full re-hash" if re_hash else "sidecar cross-check"

        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")

        status_icon = "✔" if n_fail == 0 else "✗"
        status_label = "ALL PASS" if n_fail == 0 else f"{n_fail} FAILED"

        lines = [
            f"#### {status_icon} Verification — `{model_id}`",
            "",
            f"- **Method:** {method}  ",
            f"- **At:** {ts}  ",
            f"- **Files:** {n_pass} passed  {n_fail} failed  ({_h(total_bytes)} total)  ",
            f"- **Result:** {status_label}",
            "",
        ]

        if n_fail > 0 or len(results) <= 20:
            # Show full table for small models or when there are failures
            lines += [
                "| File | Size | Status |",
                "|------|------|--------|",
            ]
            for r in results:
                icon = "✔" if r.get("ok") else "✗"
                colour_open  = "" if r.get("ok") else ""
                size = _h(r.get("size_bytes", 0))
                fname = Path(r["path"]).name
                lines.append(f"| `{fname}` | {size} | {icon} |")
            lines.append("")
        else:
            # Large model — just summarise
            lines += [f"  _(all {n_pass} files passed — table omitted for brevity)_", ""]

        self._write_lines(lines)

        # Console feedback
        if n_fail == 0:
            self._console.print(
                f"  [green]✔ VERIFY[/green] [bold]{model_id}[/bold]  "
                f"[dim]{n_pass} files OK  {_h(total_bytes)}  ({method})[/dim]"
            )
        else:
            self._console.print(
                f"  [red]✗ VERIFY[/red] [bold]{model_id}[/bold]  "
                f"[red]{n_fail} file(s) FAILED[/red]  "
                f"[dim]{n_pass} passed  ({method})[/dim]"
            )

    def record_model_skip(self, model_id: str, reason: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        lines = [
            f"### — `{model_id}` (skipped)",
            "",
            f"- **Skipped:** {ts}  Reason: {reason}",
            "",
        ]
        self._write_lines(lines)

    def record_preflight_fail(self, error: str) -> None:
        lines = [
            "## ✗ Pre-flight FAILED",
            "",
            f"> **Error:** {error}",
            "",
            f"Run aborted at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        ]
        self._write_lines(lines)
        self._flush_report_path()

    def close(self, stats: Optional[SchedulerStats]) -> None:
        """Write the final summary section and close the report."""
        elapsed = time.time() - self._start_time
        h, rem = divmod(int(elapsed), 3600)
        m, s = divmod(rem, 60)
        elapsed_str = f"{h}h {m}m {s}s" if h else (f"{m}m {s}s" if m else f"{s}s")

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        n_complete = len(stats.completed) if stats else 0
        n_failed   = len(stats.failed)    if stats else 0
        done_bytes = stats.done_bytes      if stats else 0

        lines: list[str] = [
            "---",
            "",
            "## Final Summary",
            "",
            f"| Metric | Value |",
            "|--------|-------|",
            f"| Completed | {n_complete} |",
            f"| Failed | {n_failed} |",
            f"| Downloaded | {_h(done_bytes)} |",
            f"| Elapsed | {elapsed_str} |",
            f"| Finished | {now_str} |",
            "",
        ]

        # Completed model list
        if stats and stats.completed:
            lines += ["**Completed models:**", ""]
            for mid in stats.completed:
                lines.append(f"- ✔ `{mid}`")
            lines.append("")

        # Failed model list
        if stats and stats.failed:
            lines += ["**Failed models:**", ""]
            for mid in stats.failed:
                lines.append(f"- ✗ `{mid}`")
            lines.append("")

        # Drive snapshot at end
        lines += self._drive_snapshot_section()

        result = "SUCCESS" if (not stats or not stats.failed) else f"PARTIAL ({n_failed} failed)"
        lines += ["", f"---", "", f"**Result: {result}**", ""]

        self._write_lines(lines)
        self._flush_report_path()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _drive_snapshot_section(self) -> list[str]:
        lines = ["### Drive Usage Snapshot", ""]
        lines += ["| Drive | Mount | Used | Free | Total | Use% |",
                  "|-------|-------|------|------|-------|------|"]
        for label, drive in self.registry.drives.items():
            try:
                u = psutil.disk_usage(str(drive.mount_point))
                lines.append(
                    f"| {label.upper()} | {drive.mount_point} "
                    f"| {u.used/1024**3:.1f} GB | {u.free/1024**3:.1f} GB "
                    f"| {u.total/1024**3:.1f} GB | {u.percent:.1f}% |"
                )
            except Exception:
                lines.append(f"| {label.upper()} | {drive.mount_point} | — | — | — | — |")
        return lines

    def _write_lines(self, lines: list[str]) -> None:
        if not self._path:
            return
        with self._lock:
            try:
                with self._path.open("a", encoding="utf-8") as fh:
                    fh.write("\n".join(lines) + "\n")
            except Exception:
                pass

    def _flush_report_path(self) -> None:
        if self._path:
            self._console.print(
                f"\n  [dim]Run report → [bold]{self._path}[/bold][/dim]"
            )
