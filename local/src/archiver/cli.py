"""Click CLI entry points for the archiver tool."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from collections import deque
from pathlib import Path
from typing import Optional

import click
import psutil
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from archiver.models import load_registry, save_registry, Registry
from archiver.state import (
    RunState,
    STATUS_COMPLETE,
    STATUS_FAILED,
    STATUS_IN_PROGRESS,
    STATUS_PENDING,
    STATUS_SKIPPED,
    sync_archive,
)

console = Console()

DEFAULT_REGISTRY = Path("config/registry.yaml")
DEFAULT_DRIVES = Path("config/drives.yaml")

# Minimum free space required on the root/boot filesystem before we allow a run.
# The root SSD only needs to hold the Python env, logs symlink, and nothing else.
ROOT_FS_MIN_FREE_GB = 10


def _d5_path(reg: Registry) -> Path:
    """Return the D5 mount point, falling back to /tmp/archiver if not configured."""
    d5 = reg.drives.get("d5")
    return d5.mount_point if d5 else Path("/tmp/archiver")


def _tmp_dir(reg: Registry) -> Path:
    """
    Return the scratch directory for in-progress downloads.
    Reads tmp_dir from D1 in drives.yaml (D1 has ~2.3 TB headroom post-downloads,
    far more than the 1 TB D5 drive). Falls back to <d5>/.tmp for safety.
    """
    d1 = reg.drives.get("d1")
    if d1 and d1.tmp_dir:
        return d1.tmp_dir
    # Fallback: .tmp on whichever drive has a configured tmp_dir
    for drive in reg.drives.values():
        if drive.tmp_dir:
            return drive.tmp_dir
    return _d5_path(reg) / ".tmp"


def _state_path(reg: Registry) -> Path:
    """run_state.json always lives on D5, never on the root SSD."""
    return _d5_path(reg) / "run_state.json"


def _load(registry_path: Path, drives_path: Path) -> tuple[Registry, RunState]:
    if not registry_path.exists():
        raise click.ClickException(f"Registry not found: {registry_path}")
    reg = load_registry(registry_path, drives_path if drives_path.exists() else None)
    # State file is on D5 — the 1 TB scratch/infra drive — not on the root SSD.
    state = RunState(_state_path(reg))
    return reg, state


def _setup_logging(verbose: bool, log_dir: Optional[Path] = None) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_dir:
        from datetime import datetime
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
        fh = logging.FileHandler(log_dir / f"{ts}_download.log")
        fh.setFormatter(logging.Formatter(fmt))
        handlers.append(fh)
    logging.basicConfig(level=level, format=fmt, handlers=handlers)


def _check_root_ssd_space() -> Optional[str]:
    """
    Warn if the root filesystem is low on space.
    The root SSD (256 GB) must never receive model data — this check catches
    accidental misconfiguration where a path resolves to the root fs.
    """
    try:
        usage = psutil.disk_usage("/")
        free_gb = usage.free / 1024 ** 3
        if free_gb < ROOT_FS_MIN_FREE_GB:
            return (
                f"Root filesystem has only {free_gb:.1f} GB free. "
                f"Ensure all data paths point to external drives, not /."
            )
    except Exception:
        pass
    return None


# ------------------------------------------------------------------
# Root group
# ------------------------------------------------------------------

@click.group()
@click.option("--registry", "-r", type=click.Path(), default=str(DEFAULT_REGISTRY),
              show_default=True, help="Path to registry.yaml")
@click.option("--drives", type=click.Path(), default=str(DEFAULT_DRIVES),
              show_default=True, help="Path to drives.yaml")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx: click.Context, registry: str, drives: str, verbose: bool) -> None:
    """Model archival tool — download, verify, and manage LLM weight archives."""
    ctx.ensure_object(dict)
    # Resolve to absolute so worker threads inherit the correct path regardless
    # of any working-directory changes made inside the process.
    ctx.obj["registry_path"] = Path(registry).resolve()
    ctx.obj["drives_path"] = Path(drives).resolve()
    ctx.obj["verbose"] = verbose


# ------------------------------------------------------------------
# download
# ------------------------------------------------------------------

@cli.command("download")
@click.argument("target", default="--all")
@click.option("--tier", type=click.Choice(["A", "B", "C", "D", "E", "F", "G"]), help="Download a specific tier")
@click.option("--all", "download_all", is_flag=True, default=False, help="Download everything")
@click.option("--priority-only", type=int, help="Download only models with this priority (1 or 2)")
@click.option("--dry-run", is_flag=True, help="Print what would be downloaded without fetching")
@click.option("--max-parallel-drives", "max_parallel_models", type=int, default=12, show_default=True,
              help="Max simultaneous model downloads (worker pool size)")
@click.option("--max-per-drive", type=int, default=4, show_default=True,
              help="Max concurrent models per drive (limits disk thrash)")
@click.option("--min-speed-mbps", type=float, default=6.0, show_default=True,
              help="Only add another model if aggregate/(n+1) >= this (MB/s)")
@click.option("--bandwidth-cap", type=float, default=None, help="Total bandwidth cap in MB/s")
@click.option("--fast", is_flag=True, help="Use hf_transfer fast-path (no resume)")
@click.option(
    "--status-out", type=click.Path(), default=None,
    help="Path to write STATUS.md [default: <d5>/STATUS.md]",
)
@click.option(
    "--skip-drive-space-check", is_flag=True,
    help="Do not abort when a drive has <50 GB free (e.g. D2 full by design)",
)
@click.pass_context
def cmd_download(
    ctx: click.Context,
    target: str,
    tier: Optional[str],
    download_all: bool,
    priority_only: Optional[int],
    dry_run: bool,
    max_parallel_models: int,
    max_per_drive: int,
    min_speed_mbps: float,
    bandwidth_cap: Optional[float],
    fast: bool,
    status_out: Optional[str],
    skip_drive_space_check: bool,
) -> None:
    """Download model weights. Use --all, --tier X, or specify a model ID."""
    from archiver.aria2_manager import Aria2Manager
    from archiver.downloader import Downloader
    from archiver.scheduler import DriveScheduler
    from archiver.status import StatusDisplay, RunReport
    from archiver.state import sync_archive
    import archiver.preflight as preflight

    registry_path: Path = ctx.obj["registry_path"]
    drives_path: Path = ctx.obj["drives_path"]
    verbose: bool = ctx.obj["verbose"]
    reg, state = _load(registry_path, drives_path)

    # All runtime paths derived from storage drives — nothing written to the root SSD.
    d5 = _d5_path(reg)
    tmp_dir     = _tmp_dir(reg)      # D1/.tmp — 2.3 TB headroom, not D5's 1 TB
    logs_dir    = d5 / "logs"
    archive_dir = d5 / "archive"
    index_path  = archive_dir / "checksums" / "global_index.jsonl"
    status_path = Path(status_out) if status_out else (d5 / "STATUS.md")
    activity_log_path = d5 / "archiver-activity.log"

    _setup_logging(verbose, log_dir=logs_dir if not dry_run else None)

    # ── Startup banner ────────────────────────────────────────────────────
    _print_startup_banner(reg, d5, tmp_dir, logs_dir, dry_run)

    # Warn if root SSD is unexpectedly low
    root_warn = _check_root_ssd_space()
    if root_warn:
        console.print(f"[yellow]⚠  {root_warn}[/]")

    hf_token = os.environ.get("HF_TOKEN")

    # ── Pre-flight checks ────────────────────────────────────────────────
    console.print(Rule("[bold cyan]Pre-flight Checks[/bold cyan]"))
    try:
        warnings, token_results = preflight.run_all(
            reg, hf_token, skip_drive_space_check=skip_drive_space_check
        )
        console.print("[green]✔[/green]  All pre-flight checks passed")
    except preflight.PreflightError as e:
        console.print(Panel(str(e), title="[bold red]Pre-flight FAILED[/bold red]",
                            border_style="red"))
        if not dry_run:
            # Still create logs dir so the report can be written
            try:
                logs_dir.mkdir(parents=True, exist_ok=True)
                run_report = RunReport(log_dir=logs_dir, registry=reg)
                run_report.open(hf_token_set=bool(hf_token), models=[])
                run_report.record_preflight_fail(str(e))
            except Exception:
                pass
        sys.exit(1)

    for w in warnings:
        console.print(f"[yellow]⚠  {w}[/]")

    # Create required subdirectories only after pre-flight confirms drives are mounted
    for d in [tmp_dir, logs_dir, archive_dir, archive_dir / "checksums"]:
        d.mkdir(parents=True, exist_ok=True)

    # ── Select models ────────────────────────────────────────────────────
    models = reg.models
    if tier:
        models = [m for m in models if m.tier == tier]
    elif not download_all and target not in ("--all", ""):
        models = [m for m in models if m.id == target]
        if not models:
            raise click.ClickException(f"Model '{target}' not found in registry")
    if priority_only:
        models = [m for m in models if m.priority == priority_only]

    models = sorted(models, key=lambda m: (m.priority, m.drive, m.id))

    if dry_run:
        _print_download_plan(models, d5, tmp_dir)
        return

    # ── Run report ───────────────────────────────────────────────────────
    run_report = RunReport(log_dir=logs_dir, registry=reg)
    cli_args = {
        "tier": tier or "all",
        "priority_only": priority_only or "all",
        "max_parallel_models": max_parallel_models,
        "max_per_drive": max_per_drive,
        "min_speed_mbps": min_speed_mbps,
        "bandwidth_cap": bandwidth_cap or "unlimited",
        "hf_token": "set" if hf_token else "not set",
        "logs_dir": str(logs_dir),
        "tmp_dir": str(tmp_dir),
        "status_md": str(status_path),
    }
    run_report.open(
        hf_token_set=bool(hf_token),
        models=models,
        preflight_warnings=warnings,
        preflight_token_results=token_results,
        cli_args=cli_args,
    )

    # ── Status display ───────────────────────────────────────────────────
    status_display = StatusDisplay(
        registry=reg,
        state=state,
        status_md_path=status_path,
        total_bytes=0,
    )

    console.print(Rule("[bold cyan]Downloads[/bold cyan]"))

    with Aria2Manager(
        tmp_dir=tmp_dir,
        max_overall_download_limit_mbps=bandwidth_cap,
    ) as aria2:
        downloader = Downloader(
            aria2=aria2,
            tmp_dir=tmp_dir,
            archive_index_path=index_path,
            hf_token=hf_token,
            dry_run=False,
        )

        def do_download(model):
            run_report.record_model_start(model)
            return downloader.download_model(model, run_report=run_report)

        replica_roots = [
            d.mount_point for label, d in reg.drives.items() if label != "d5"
        ]

        def on_complete(model, manifest):
            run_report.record_model_complete(model, manifest)
            save_registry(reg, registry_path)
            sync_archive(archive_dir, replica_roots)
            status_display.update(scheduler._stats)

        def on_failed(model, reason):
            run_report.record_model_fail(model, reason)

        scheduler = DriveScheduler(
            registry=reg,
            state=state,
            download_fn=do_download,
            get_speed_fn=aria2.aggregate_speed_mbps,
            on_model_complete=on_complete,
            on_model_failed=on_failed,
            on_status_update=status_display.update,
            token_accessible=token_results,
            max_parallel_models=max_parallel_models,
            max_models_per_drive=max_per_drive,
            min_speed_per_model_mbps=min_speed_mbps,
            activity_log_path=activity_log_path,
        )
        scheduler.build_queue(models)

        state.start_run()
        status_display.start()
        try:
            final_stats = scheduler.run()
        finally:
            status_display.stop()
            state.end_run(final_stats.__dict__ if final_stats else {})

    # ── Final summary ────────────────────────────────────────────────────
    n_ok   = len(final_stats.completed) if final_stats else 0
    n_fail = len(final_stats.failed)    if final_stats else 0

    run_report.close(final_stats)

    console.print(Rule())
    _print_final_summary(n_ok, n_fail, final_stats, run_report.path)

    if n_fail:
        sys.exit(1)


# ------------------------------------------------------------------
# verify
# ------------------------------------------------------------------

@cli.command("verify")
@click.argument("model_id", default="")
@click.option("--all", "verify_all", is_flag=True)
@click.option("--tier", type=click.Choice(["A", "B", "C", "D", "E", "F", "G"]))
@click.option("--drive", "drive_filter")
@click.option("--manifest", type=click.Path(), help="Verify against a specific manifest.json")
@click.pass_context
def cmd_verify(
    ctx: click.Context,
    model_id: str,
    verify_all: bool,
    tier: Optional[str],
    drive_filter: Optional[str],
    manifest: Optional[str],
) -> None:
    """Verify SHA-256 checksums for downloaded models."""
    from archiver.verifier import verify_model_dir

    registry_path: Path = ctx.obj["registry_path"]
    drives_path: Path = ctx.obj["drives_path"]
    reg, state = _load(registry_path, drives_path)

    models = reg.models
    if model_id:
        models = [m for m in models if m.id == model_id]
    elif tier:
        models = [m for m in models if m.tier == tier]
    elif drive_filter:
        models = [m for m in models if m.drive == drive_filter]
    elif not verify_all:
        raise click.UsageError("Specify a model ID, --all, --tier, or --drive")

    table = Table(title="Verification Results")
    table.add_column("Model")
    table.add_column("File")
    table.add_column("Status")

    any_fail = False
    for m in models:
        if not state.is_complete(m.id):
            continue
        if m.model_dir is None:
            continue
        results = verify_model_dir(m.model_dir)
        for r in results:
            ok = r["ok"]
            if not ok:
                any_fail = True
            table.add_row(
                m.id,
                r["path"],
                "[green]✓ PASS[/]" if ok else "[red]✗ FAIL[/]",
            )

    console.print(table)
    if any_fail:
        sys.exit(1)


# ------------------------------------------------------------------
# status
# ------------------------------------------------------------------

@cli.command("status")
@click.option("--drive", "drive_filter", help="Filter by drive label (d1..d5)")
@click.pass_context
def cmd_status(ctx: click.Context, drive_filter: Optional[str]) -> None:
    """Show per-model download status."""
    registry_path: Path = ctx.obj["registry_path"]
    drives_path: Path = ctx.obj["drives_path"]
    reg, state = _load(registry_path, drives_path)

    models = reg.models
    if drive_filter:
        models = [m for m in models if m.drive == drive_filter]

    table = Table(title="Archive Status")
    table.add_column("Model", style="cyan", no_wrap=True)
    table.add_column("Tier", width=4)
    table.add_column("Drive", width=4)
    table.add_column("Priority", width=4)
    table.add_column("Status")
    table.add_column("Size")
    table.add_column("Completed At")

    for m in models:
        data = state.get_model_data(m.id)
        s = data.get("status", "pending")
        colour = {"complete": "green", "failed": "red", "in_progress": "yellow"}.get(s, "dim")
        table.add_row(
            m.id,
            m.tier,
            m.drive.upper(),
            str(m.priority),
            f"[{colour}]{s}[/]",
            _fmt_bytes_cli(data.get("total_bytes", 0)),
            data.get("completed_at", "—")[:16],
        )

    console.print(table)
    summary = state.summary()
    console.print(f"\n[bold]Summary:[/] {summary}")


# ------------------------------------------------------------------
# stats
# ------------------------------------------------------------------

TIER_LABELS = {"A": "flagship", "B": "smaller/code", "C": "GGUF", "D": "uncensored", "E": "reasoning", "F": "vision/math", "G": "research"}


@cli.command("stats")
@click.pass_context
def cmd_stats(ctx: click.Context) -> None:
    """Print completed/total counts by tier (no downloads)."""
    registry_path: Path = ctx.obj["registry_path"]
    drives_path: Path = ctx.obj["drives_path"]
    reg, state = _load(registry_path, drives_path)

    table = Table(title="Completed by tier")
    table.add_column("Tier", width=4)
    table.add_column("Label", width=16)
    table.add_column("Complete", justify="right", width=8)
    table.add_column("Total", justify="right", width=6)

    for tier in "ABCDEFG":
        models = [m for m in reg.models if m.tier == tier]
        n = len(models)
        if n == 0:
            continue
        complete = sum(1 for m in models if state.is_complete(m.id))
        table.add_row(tier, TIER_LABELS.get(tier, tier), str(complete), str(n))

    console.print(table)
    summary = state.summary()
    n_complete = summary.get(STATUS_COMPLETE, 0)
    console.print(f"\n[bold]Overall:[/] {n_complete} complete, {summary}")


# ------------------------------------------------------------------
# list
# ------------------------------------------------------------------

@cli.command("list")
@click.option("--tier", type=click.Choice(["A", "B", "C", "D", "E", "F", "G"]))
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def cmd_list(ctx: click.Context, tier: Optional[str], as_json: bool) -> None:
    """List all models in the registry."""
    registry_path: Path = ctx.obj["registry_path"]
    drives_path: Path = ctx.obj["drives_path"]
    reg, _ = _load(registry_path, drives_path)

    models = [m for m in reg.models if (not tier or m.tier == tier)]

    if as_json:
        print(json.dumps([m.__dict__ for m in models], default=str, indent=2))
        return

    table = Table(title="Model Registry")
    table.add_column("ID", style="cyan")
    table.add_column("Tier", width=4)
    table.add_column("Drive", width=4)
    table.add_column("P", width=2, header_style="dim")
    table.add_column("Auth", width=5)
    table.add_column("Licence")
    table.add_column("Commit SHA")

    for m in models:
        table.add_row(
            m.id,
            m.tier,
            m.drive.upper(),
            str(m.priority),
            "yes" if m.requires_auth else "no",
            m.licence,
            (m.commit_sha or "—")[:12],
        )

    console.print(table)


# ------------------------------------------------------------------
# pin
# ------------------------------------------------------------------

@cli.command("pin")
@click.argument("model_id")
@click.argument("commit_sha")
@click.pass_context
def cmd_pin(ctx: click.Context, model_id: str, commit_sha: str) -> None:
    """Pin a model to a specific commit SHA in the registry."""
    registry_path: Path = ctx.obj["registry_path"]
    drives_path: Path = ctx.obj["drives_path"]
    reg, _ = _load(registry_path, drives_path)

    m = reg.get(model_id)
    if not m:
        raise click.ClickException(f"Model '{model_id}' not in registry")

    old = m.commit_sha
    m.commit_sha = commit_sha
    save_registry(reg, registry_path)
    console.print(f"Pinned [cyan]{model_id}[/]: {old or '(unset)'} → {commit_sha}")


# ------------------------------------------------------------------
# tokens check
# ------------------------------------------------------------------

@cli.command("tokens")
@click.argument("action", type=click.Choice(["check"]))
@click.pass_context
def cmd_tokens(ctx: click.Context, action: str) -> None:
    """Check HF token access for all gated models."""
    import archiver.preflight as preflight

    registry_path: Path = ctx.obj["registry_path"]
    drives_path: Path = ctx.obj["drives_path"]
    reg, _ = _load(registry_path, drives_path)

    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        console.print("[yellow]HF_TOKEN not set in environment[/]")
        sys.exit(1)

    results = preflight.check_hf_token(hf_token, reg)
    table = Table(title="Token Access Check")
    table.add_column("Model")
    table.add_column("Accessible")
    for mid, ok in results.items():
        table.add_row(mid, "[green]✓ yes[/]" if ok else "[red]✗ no[/]")
    console.print(table)
    if not all(results.values()):
        sys.exit(1)


# ------------------------------------------------------------------
# drives status
# ------------------------------------------------------------------

@cli.command("drives")
@click.argument("action", type=click.Choice(["status"]))
@click.pass_context
def cmd_drives(ctx: click.Context, action: str) -> None:
    """Show drive usage information."""
    registry_path: Path = ctx.obj["registry_path"]
    drives_path: Path = ctx.obj["drives_path"]
    reg, _ = _load(registry_path, drives_path)

    table = Table(title="Drive Status")
    table.add_column("Label", width=6)
    table.add_column("Mount Point")
    table.add_column("Role")
    table.add_column("Used")
    table.add_column("Free")
    table.add_column("Total")
    table.add_column("Use%")

    for label, drive in reg.drives.items():
        try:
            u = psutil.disk_usage(str(drive.mount_point))
            table.add_row(
                label.upper(),
                str(drive.mount_point),
                drive.role,
                f"{u.used/1024**3:.1f} GB",
                f"{u.free/1024**3:.1f} GB",
                f"{u.total/1024**3:.1f} GB",
                f"{u.percent:.1f}%",
            )
        except Exception as e:
            table.add_row(label.upper(), str(drive.mount_point), drive.role,
                          "—", "—", "—", f"[red]{e}[/]")

    # Always also show root filesystem so the user can see SSD usage
    try:
        u = psutil.disk_usage("/")
        table.add_row(
            "ROOT",
            "/",
            "OS + project (SSD)",
            f"{u.used/1024**3:.1f} GB",
            f"{u.free/1024**3:.1f} GB",
            f"{u.total/1024**3:.1f} GB",
            f"{u.percent:.1f}%",
        )
    except Exception:
        pass

    console.print(table)


# ------------------------------------------------------------------
# report
# ------------------------------------------------------------------

@cli.command("report")
@click.option("--output", type=click.Path(), default=None,
              help="Output path [default: <d5>/STATUS.md or <d5>/ARCHIVE-REPORT.md]")
@click.option(
    "--full",
    "full_report",
    is_flag=True,
    default=False,
    help="Generate a full Markdown report (chosen models, queue, status, ETA)",
)
@click.pass_context
def cmd_report(ctx: click.Context, output: Optional[str], full_report: bool) -> None:
    """
    Generate Markdown status reports without starting any downloads.

    By default this regenerates STATUS.md from run_state.json. With --full it
    writes a richer ARCHIVE-REPORT.md that documents the registry, what was
    selected, current queue, completed models, and (if available) an ETA.
    """
    from archiver.status import StatusDisplay, STATUS_MD_REFRESH_SECS

    registry_path: Path = ctx.obj["registry_path"]
    drives_path: Path = ctx.obj["drives_path"]
    reg, state = _load(registry_path, drives_path)

    d5 = _d5_path(reg)

    if not full_report:
        # Lightweight mode: just regenerate STATUS.md, similar to the live run.
        out_path = Path(output) if output else (d5 / "STATUS.md")
        display = StatusDisplay(registry=reg, state=state, status_md_path=out_path)
        display._write_status_md()
        console.print(f"[green]STATUS.md written → {out_path}[/]")
        return

    # Full report mode: richer snapshot that documents the entire archive state.
    out_path = Path(output) if output else (d5 / "ARCHIVE-REPORT.md")

    # Basic counts from persistent state.
    summary = state.summary()
    total_models = len(reg.models)
    n_complete = summary.get(STATUS_COMPLETE, 0)
    n_failed = summary.get(STATUS_FAILED, 0)
    n_in_progress = summary.get(STATUS_IN_PROGRESS, 0)
    n_pending = summary.get(STATUS_PENDING, 0)
    n_skipped = summary.get(STATUS_SKIPPED, 0)

    # Derive queue (pending + in_progress) from registry ordering.
    queue = []
    completed = []
    failed = []
    skipped = []
    for m in sorted(reg.models, key=lambda m: (m.tier, m.priority, m.drive, m.id)):
        data = state.get_model_data(m.id)
        status = data.get("status", STATUS_PENDING)
        row = (m, data, status)
        if status in (STATUS_PENDING, STATUS_IN_PROGRESS):
            queue.append(row)
        elif status == STATUS_COMPLETE:
            completed.append(row)
        elif status == STATUS_FAILED:
            failed.append(row)
        elif status == STATUS_SKIPPED:
            skipped.append(row)

    # Recent activity from append-only log (for summaries and thread count).
    recent_activity_lines: list[str] = []
    activity_log_path = d5 / "archiver-activity.log"
    if activity_log_path.exists():
        try:
            with open(activity_log_path, "r", encoding="utf-8") as f:
                tail = deque(f, maxlen=80)
            recent_activity_lines = list(tail)
        except Exception:
            pass

    # Try to pick up the latest ETA from the live STATUS.md if it exists.
    eta_str = "—"
    status_md_path = d5 / "STATUS.md"
    if status_md_path.exists():
        try:
            for line in status_md_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("- **ETA:**"):
                    # Line format from StatusDisplay: "- **ETA:** 1h 23m"
                    eta_str = line.split("**ETA:**", 1)[-1].strip()
                    break
        except Exception:
            pass

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines: list[str] = []
    lines += [
        "# Archive Snapshot Report",
        "",
        f"_Generated: {now_str}_",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total models in registry | {total_models} |",
        f"| Complete | {n_complete} |",
        f"| In progress | {n_in_progress} |",
        f"| Pending | {n_pending} |",
        f"| Failed | {n_failed} |",
        f"| Skipped (no token / gated) | {n_skipped} |",
        f"| ETA (from live STATUS.md) | {eta_str} |",
        "",
        "## Recent Activity",
        "",
        "Last entries from `archiver-activity.log` (RUN_START/WORKER_START/MODEL_* / SPEED / RUN_END):",
        "",
    ]
    if recent_activity_lines:
        for ln in recent_activity_lines:
            lines.append(f"    {ln}")
    else:
        lines.append("    (no activity log yet)")
    lines += [
        "",
        "## Selected Models (Registry)",
        "",
        "| Model | Tier | Drive | Priority | Auth |",
        "|-------|------|-------|----------|------|",
    ]

    for m in reg.models:
        lines.append(
            f"| `{m.id}` | {m.tier} | {m.drive.upper()} | {m.priority} | "
            f"{'yes' if m.requires_auth else 'no'} |"
        )

    # Queue section: what is still to do this run.
    lines += [
        "",
        "## Queue (Pending + In Progress)",
        "",
        "| Model | Tier | Drive | Priority | Status | Size | Last Updated |",
        "|-------|------|-------|----------|--------|------|--------------|",
    ]

    if queue:
        for m, data, status in queue:
            size = _fmt_bytes_cli(data.get("total_bytes", 0))
            updated = (data.get("updated_at") or "—")[:16]
            lines.append(
                f"| `{m.id}` | {m.tier} | {m.drive.upper()} | {m.priority} | "
                f"{status} | {size} | {updated} |"
            )
    else:
        lines.append("| — | — | — | — | — | — | — |")

    # Completed section.
    lines += [
        "",
        "## Completed Models",
        "",
        "| Model | Tier | Drive | Size | Completed At |",
        "|-------|------|-------|------|--------------|",
    ]

    if completed:
        for m, data, _ in completed:
            size = _fmt_bytes_cli(data.get("total_bytes", 0))
            completed_at = (data.get("completed_at") or "—")[:16]
            lines.append(
                f"| `{m.id}` | {m.tier} | {m.drive.upper()} | {size} | {completed_at} |"
            )
    else:
        lines.append("| — | — | — | — | — |")

    # Failed / skipped section.
    lines += [
        "",
        "## Failed / Skipped Models",
        "",
        "| Model | Status | Reason |",
        "|-------|--------|--------|",
    ]

    if failed or skipped:
        for m, data, status in failed + skipped:
            reason = data.get("error", "—")
            lines.append(f"| `{m.id}` | {status} | {reason} |")
    else:
        lines.append("| — | — | — |")

    # Drive usage snapshot.
    lines += [
        "",
        "## Drive Usage",
        "",
        "| Drive | Mount | Used | Free | Total |",
        "|-------|-------|------|------|-------|",
    ]
    for label, drive in reg.drives.items():
        try:
            u = psutil.disk_usage(str(drive.mount_point))
            used_tb = u.used / 1024**4
            free_tb = u.free / 1024**4
            total_tb = u.total / 1024**4
            lines.append(
                f"| {label.upper()} | {drive.mount_point} "
                f"| {used_tb:.1f} TB | {free_tb:.1f} TB | {total_tb:.1f} TB |"
            )
        except Exception:
            lines.append(
                f"| {label.upper()} | {drive.mount_point} | N/A | N/A | N/A |"
            )

    content = "\n".join(lines) + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(out_path)

    console.print(f"[green]Archive snapshot report written → {out_path}[/]")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _fmt_bytes_cli(b: int) -> str:
    if b == 0:
        return "—"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(b) < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024  # type: ignore[assignment]
    return f"{b:.1f} PB"


def _print_startup_banner(reg, d5: Path, tmp_dir: Path, logs_dir: Path, dry_run: bool) -> None:
    """Print a rich startup banner with run metadata and drive overview."""
    from rich.rule import Rule
    import socket
    import platform

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    console.print()
    console.print(Rule("[bold magenta]  Model Archiver  [/bold magenta]"))
    console.print()

    info_table = Table(box=None, show_header=False, padding=(0, 2))
    info_table.add_column("key",   style="dim",  width=18)
    info_table.add_column("value", style="bold")
    info_table.add_row("Started",  now_str)
    info_table.add_row("Host",     socket.gethostname())
    info_table.add_row("Python",   platform.python_version())
    info_table.add_row("Mode",     "[yellow]DRY RUN[/yellow]" if dry_run else "[green]LIVE[/green]")
    info_table.add_row("Tmp dir",  str(tmp_dir))
    info_table.add_row("Logs dir", str(logs_dir))
    info_table.add_row("Status",   str(d5 / "STATUS.md"))
    console.print(info_table)

    # Drive overview
    console.print()
    drive_table = Table(title="Drives", box=None, show_header=True, header_style="bold cyan")
    drive_table.add_column("Label", width=6)
    drive_table.add_column("Mount", width=22)
    drive_table.add_column("Role")
    drive_table.add_column("Free", width=10)
    drive_table.add_column("Total", width=10)
    for label, drive in reg.drives.items():
        try:
            u = psutil.disk_usage(str(drive.mount_point))
            free  = _fmt_bytes_cli(u.free)
            total = _fmt_bytes_cli(u.total)
            colour = "green" if u.free / u.total > 0.2 else "yellow"
            drive_table.add_row(
                label.upper(), str(drive.mount_point), drive.role,
                f"[{colour}]{free}[/]", total,
            )
        except Exception:
            drive_table.add_row(label.upper(), str(drive.mount_point), drive.role,
                                "[red]unavailable[/]", "—")
    console.print(drive_table)
    console.print()


def _print_download_plan(models, d5: Path, tmp_dir: Path) -> None:
    from rich.rule import Rule

    console.print(Rule("[bold cyan]Download Plan (dry run)[/bold cyan]"))
    table = Table(show_header=True, header_style="bold")
    table.add_column("#",        width=3)
    table.add_column("Model",    style="cyan")
    table.add_column("Tier",     width=5)
    table.add_column("Drive",    width=5)
    table.add_column("Priority", width=4)
    table.add_column("Auth",     width=5)
    for i, m in enumerate(models, 1):
        table.add_row(
            str(i), m.id, m.tier, m.drive.upper(), str(m.priority),
            "[yellow]yes[/]" if m.requires_auth else "no",
        )
    console.print(table)
    console.print(f"\n  [dim]{len(models)} model(s) would be downloaded[/]")
    console.print()

    path_table = Table(box=None, show_header=False, padding=(0, 2))
    path_table.add_column("key",   style="dim",  width=18)
    path_table.add_column("value", style="bold")
    path_table.add_row("tmp (D1)",   str(tmp_dir))
    path_table.add_row("logs (D5)",  str(d5 / "logs"))
    path_table.add_row("archive",    str(d5 / "archive"))
    path_table.add_row("state",      str(d5 / "run_state.json"))
    path_table.add_row("STATUS.md",  str(d5 / "STATUS.md"))
    console.print(path_table)
    console.print()


def _print_final_summary(n_ok: int, n_fail: int, final_stats, report_path) -> None:
    """Print a final coloured summary panel after all downloads finish."""
    total = n_ok + n_fail
    if n_fail == 0:
        style = "green"
        title = "[bold green]  All Downloads Complete  [/bold green]"
        icon  = "✔"
    else:
        style = "yellow" if n_ok > 0 else "red"
        title = "[bold yellow]  Downloads Finished With Errors  [/bold yellow]"
        icon  = "⚠"

    done_bytes = final_stats.done_bytes if final_stats else 0

    lines = Text()
    lines.append(f"\n  {icon}  {n_ok}/{total} models completed successfully\n", style=style)
    if n_fail:
        lines.append(f"  ✗  {n_fail} model(s) failed — check logs for details\n", style="red")
    lines.append(f"\n  Total downloaded:  {_fmt_bytes_cli(done_bytes)}\n", style="dim")
    if report_path:
        lines.append(f"  Run report:        {report_path}\n", style="dim")

    console.print(Panel(lines, title=title, border_style=style))
    console.print()
