"""Click CLI entry points for the archiver tool."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import click
import psutil
from rich.console import Console
from rich.table import Table

from archiver.models import load_registry, save_registry, Registry
from archiver.state import RunState, STATUS_COMPLETE, STATUS_FAILED, sync_archive

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
    ctx.obj["registry_path"] = Path(registry)
    ctx.obj["drives_path"] = Path(drives)
    ctx.obj["verbose"] = verbose


# ------------------------------------------------------------------
# download
# ------------------------------------------------------------------

@cli.command("download")
@click.argument("target", default="--all")
@click.option("--tier", type=click.Choice(["A", "B", "C", "D"]), help="Download a specific tier")
@click.option("--all", "download_all", is_flag=True, default=False, help="Download everything")
@click.option("--priority-only", type=int, help="Download only models with this priority (1 or 2)")
@click.option("--dry-run", is_flag=True, help="Print what would be downloaded without fetching")
@click.option("--max-parallel-drives", type=int, default=4, show_default=True)
@click.option("--bandwidth-cap", type=float, default=None, help="Total bandwidth cap in MB/s")
@click.option("--fast", is_flag=True, help="Use hf_transfer fast-path (no resume)")
@click.option(
    "--status-out", type=click.Path(), default=None,
    help="Path to write STATUS.md [default: <d5>/STATUS.md]",
)
@click.pass_context
def cmd_download(
    ctx: click.Context,
    target: str,
    tier: Optional[str],
    download_all: bool,
    priority_only: Optional[int],
    dry_run: bool,
    max_parallel_drives: int,
    bandwidth_cap: Optional[float],
    fast: bool,
    status_out: Optional[str],
) -> None:
    """Download model weights. Use --all, --tier X, or specify a model ID."""
    from archiver.aria2_manager import Aria2Manager
    from archiver.downloader import Downloader
    from archiver.scheduler import DriveScheduler
    from archiver.status import StatusDisplay
    from archiver.state import sync_archive
    import archiver.preflight as preflight

    registry_path: Path = ctx.obj["registry_path"]
    drives_path: Path = ctx.obj["drives_path"]
    verbose: bool = ctx.obj["verbose"]
    reg, state = _load(registry_path, drives_path)

    # All runtime paths derived from D5 — nothing written to the root SSD.
    d5 = _d5_path(reg)
    tmp_dir     = d5 / ".tmp"
    logs_dir    = d5 / "logs"
    archive_dir = d5 / "archive"
    index_path  = archive_dir / "checksums" / "global_index.jsonl"
    status_path = Path(status_out) if status_out else (d5 / "STATUS.md")

    _setup_logging(verbose, log_dir=logs_dir if not dry_run else None)

    # Warn if root SSD is unexpectedly low
    root_warn = _check_root_ssd_space()
    if root_warn:
        console.print(f"[yellow]⚠ {root_warn}[/]")

    hf_token = os.environ.get("HF_TOKEN")

    console.print("[bold]Running pre-flight checks…[/]")
    try:
        warnings, token_results = preflight.run_all(reg, hf_token)
    except preflight.PreflightError as e:
        console.print(f"[bold red]Pre-flight FAILED:[/] {e}")
        sys.exit(1)

    for w in warnings:
        console.print(f"[yellow]⚠ {w}[/]")

    # Create D5 subdirectories only after pre-flight confirms D5 is mounted
    for d in [tmp_dir, logs_dir, archive_dir, archive_dir / "checksums"]:
        d.mkdir(parents=True, exist_ok=True)

    # Select models
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
        _print_download_plan(models, reg, d5)
        return

    status_display = StatusDisplay(
        registry=reg,
        state=state,
        status_md_path=status_path,
        total_bytes=0,
    )

    with Aria2Manager(tmp_dir=tmp_dir) as aria2:
        downloader = Downloader(
            aria2=aria2,
            tmp_dir=tmp_dir,
            archive_index_path=index_path,
            hf_token=hf_token,
            dry_run=False,
        )

        def do_download(model):
            return downloader.download_model(model)

        replica_roots = [
            d.mount_point for label, d in reg.drives.items() if label != "d5"
        ]

        def on_complete(model, manifest):
            save_registry(reg, registry_path)
            sync_archive(archive_dir, replica_roots)
            status_display.update(scheduler._stats)

        scheduler = DriveScheduler(
            registry=reg,
            state=state,
            download_fn=do_download,
            get_speed_fn=aria2.aggregate_speed_mbps,
            on_model_complete=on_complete,
            on_status_update=status_display.update,
            token_accessible=token_results,
            max_parallel_drives=max_parallel_drives,
            bandwidth_cap_mbps=bandwidth_cap,
        )
        scheduler.build_queue(models)

        state.start_run()
        status_display.start()
        try:
            final_stats = scheduler.run()
        finally:
            status_display.stop()
            state.end_run(final_stats.__dict__ if final_stats else {})

    n_ok = len(final_stats.completed) if final_stats else 0
    n_fail = len(final_stats.failed) if final_stats else 0
    console.print(f"\n[bold]Done:[/] {n_ok} complete, {n_fail} failed")
    if n_fail:
        sys.exit(1)


# ------------------------------------------------------------------
# verify
# ------------------------------------------------------------------

@cli.command("verify")
@click.argument("model_id", default="")
@click.option("--all", "verify_all", is_flag=True)
@click.option("--tier", type=click.Choice(["A", "B", "C", "D"]))
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
# list
# ------------------------------------------------------------------

@cli.command("list")
@click.option("--tier", type=click.Choice(["A", "B", "C", "D"]))
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
              help="Output path [default: <d5>/STATUS.md]")
@click.pass_context
def cmd_report(ctx: click.Context, output: Optional[str]) -> None:
    """Regenerate STATUS.md from run_state.json without downloading."""
    from archiver.status import StatusDisplay

    registry_path: Path = ctx.obj["registry_path"]
    drives_path: Path = ctx.obj["drives_path"]
    reg, state = _load(registry_path, drives_path)

    out_path = Path(output) if output else (_d5_path(reg) / "STATUS.md")
    display = StatusDisplay(registry=reg, state=state, status_md_path=out_path)
    display._write_status_md()
    console.print(f"[green]STATUS.md written → {out_path}[/]")


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


def _print_download_plan(models, reg, d5: Path) -> None:
    table = Table(title="Download Plan (dry run)")
    table.add_column("Model", style="cyan")
    table.add_column("Tier", width=4)
    table.add_column("Drive", width=4)
    table.add_column("Priority", width=4)
    table.add_column("Auth")
    for m in models:
        table.add_row(
            m.id,
            m.tier,
            m.drive.upper(),
            str(m.priority),
            "yes" if m.requires_auth else "no",
        )
    console.print(table)
    console.print(f"\n[dim]{len(models)} model(s) would be downloaded[/]")
    console.print(f"\n[dim]Runtime paths (all on D5):[/]")
    console.print(f"  tmp:        {d5 / '.tmp'}")
    console.print(f"  logs:       {d5 / 'logs'}")
    console.print(f"  archive:    {d5 / 'archive'}")
    console.print(f"  state:      {d5 / 'run_state.json'}")
    console.print(f"  STATUS.md:  {d5 / 'STATUS.md'}")
