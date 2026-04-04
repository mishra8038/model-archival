from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from gh_archival import __version__
from gh_archival.github_client import list_repos_for_snapshot, resolve_token
from gh_archival.rclone_sync import RcloneError, rclone_available, rclone_copy_local_to_remote
from gh_archival.snapshot import SnapshotError, clone_and_git_archive, clone_repo_tree, safe_archive_basename

console = Console(stderr=True)


def _git_available() -> bool:
    try:
        subprocess.run(
            ["git", "--version"],
            capture_output=True,
            check=True,
            timeout=10,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="gh-archival")
def cli() -> None:
    """Snapshot owned GitHub repositories and upload to Google Drive (or any rclone remote)."""


@cli.command("check")
def check_cmd() -> None:
    """Verify git, rclone (optional), and GitHub credentials."""
    ok = True
    if _git_available():
        console.print("[green]git[/green]: ok")
    else:
        console.print("[red]git[/red]: not found")
        ok = False
    if rclone_available():
        console.print("[green]rclone[/green]: ok")
    else:
        console.print("[yellow]rclone[/yellow]: not found (required for upload)")
    try:
        resolve_token(None)
        console.print("[green]GitHub token[/green]: ok (GITHUB_TOKEN or gh auth)")
    except RuntimeError as e:
        console.print(f"[red]GitHub token[/red]: {e}")
        ok = False
    raise SystemExit(0 if ok else 1)


@cli.command("list-repos")
@click.option(
    "--token",
    envvar="GITHUB_TOKEN",
    help="GitHub PAT (or set GITHUB_TOKEN / use gh auth token).",
)
@click.option(
    "--affiliation",
    default="owner",
    show_default=True,
    help="GitHub API user/repos affiliation filter.",
)
@click.option(
    "--any-default-branch",
    is_flag=True,
    help="Include repos whose default branch is not main.",
)
@click.option(
    "--include-forks/--no-include-forks",
    default=False,
    help="Include forked repositories.",
)
@click.option(
    "--include-archived/--no-include-archived",
    default=True,
    help="Include archived repositories.",
)
@click.option("--json", "as_json", is_flag=True, help="Print JSON array of full names.")
def list_repos_cmd(
    token: str | None,
    affiliation: str,
    any_default_branch: bool,
    include_forks: bool,
    include_archived: bool,
    as_json: bool,
) -> None:
    """List repositories that would be snapshotted."""
    tok = resolve_token(token)
    require = None if any_default_branch else "main"
    repos = list_repos_for_snapshot(
        tok,
        affiliation=affiliation,
        require_default_branch=require,
        include_forks=include_forks,
        include_archived=include_archived,
    )
    if as_json:
        click.echo(json.dumps([r.full_name for r in repos], indent=2))
        return
    for r in repos:
        click.echo(f"{r.full_name}\tbranch={r.default_branch}\tfork={r.is_fork}")


@cli.command("run")
@click.option(
    "--token",
    envvar="GITHUB_TOKEN",
    help="GitHub PAT (or GITHUB_TOKEN / gh auth token).",
)
@click.option(
    "--work-dir",
    type=click.Path(path_type=Path),
    default=lambda: Path.cwd() / "gh-archival-output",
    show_default="./gh-archival-output",
    help="Base directory for this run (snapshots + manifest).",
)
@click.option(
    "--affiliation",
    default="owner",
    show_default=True,
)
@click.option(
    "--any-default-branch",
    is_flag=True,
    help="Archive default branch even when it is not named main.",
)
@click.option(
    "--include-forks/--no-include-forks",
    default=False,
)
@click.option(
    "--include-archived/--no-include-archived",
    default=True,
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["tar", "dir"], case_sensitive=False),
    default="tar",
    show_default=True,
    help="tar: git archive per repo; dir: shallow clone with .git.",
)
@click.option(
    "--repo",
    "only_repo",
    multiple=True,
    help="Limit to one or more full names (repeatable), e.g. myuser/dotfiles.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="List actions only; no clone, no rclone.",
)
@click.option(
    "--skip-rclone",
    is_flag=True,
    help="Build local snapshot only; do not invoke rclone.",
)
@click.option(
    "--rclone-remote",
    envvar="GH_ARCHIVAL_RCLONE_REMOTE",
    default="",
    help='rclone destination, e.g. "gdrive:Backups/gh-archival".',
)
@click.option(
    "--rclone-path-suffix",
    default="",
    help="Append this path segment after the run id on the remote (optional).",
)
@click.option(
    "--rclone-arg",
    "rclone_extra",
    multiple=True,
    help="Extra args for rclone copy (repeatable), e.g. --rclone-arg=--transfers=8.",
)
def run_cmd(
    token: str | None,
    work_dir: Path,
    affiliation: str,
    any_default_branch: bool,
    include_forks: bool,
    include_archived: bool,
    fmt: str,
    only_repo: tuple[str, ...],
    dry_run: bool,
    skip_rclone: bool,
    rclone_remote: str,
    rclone_path_suffix: str,
    rclone_extra: tuple[str, ...],
) -> None:
    """Snapshot repos, write manifest, optionally rclone copy to a remote."""
    if not _git_available():
        raise click.ClickException("git is required")

    tok = resolve_token(token)
    require = None if any_default_branch else "main"
    repos = list_repos_for_snapshot(
        tok,
        affiliation=affiliation,
        require_default_branch=require,
        include_forks=include_forks,
        include_archived=include_archived,
    )
    if only_repo:
        want = {n.strip().lower() for n in only_repo if n.strip()}
        repos = [r for r in repos if r.full_name.lower() in want]
        missing = want - {r.full_name.lower() for r in repos}
        if missing:
            raise click.ClickException(f"Repos not in filtered set: {sorted(missing)}")

    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    snap_root = Path(work_dir).resolve() / "snapshots" / run_id
    manifest_path = Path(work_dir).resolve() / "snapshots" / f"manifest-{run_id}.json"

    if dry_run:
        console.print(f"Would snapshot {len(repos)} repos into [cyan]{snap_root}[/cyan]")
        for r in repos:
            console.print(f"  - {r.full_name} @ {r.default_branch}")
        if not skip_rclone and rclone_remote.strip():
            dest = rclone_remote.rstrip("/") + "/" + run_id
            if rclone_path_suffix.strip():
                dest = dest.rstrip("/") + "/" + rclone_path_suffix.strip().strip("/")
            console.print(f"Would rclone copy -> [cyan]{dest}[/cyan]")
        elif not skip_rclone:
            console.print("[yellow]No --rclone-remote; upload skipped[/yellow]")
        return

    snap_root.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    failures: list[str] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Archiving", total=len(repos))
        for repo in repos:
            progress.update(task, description=f"[cyan]{repo.full_name}[/cyan]")
            base = safe_archive_basename(repo.full_name)
            rec: dict = {
                "full_name": repo.full_name,
                "default_branch": repo.default_branch,
                "format": fmt,
                "status": "ok",
                "path": None,
                "error": None,
            }
            try:
                if fmt == "tar":
                    out = snap_root / f"{base}.tar.gz"
                    clone_and_git_archive(repo, tok, out)
                    rec["path"] = str(out.relative_to(snap_root))
                else:
                    out_dir = snap_root / base
                    clone_repo_tree(repo, tok, out_dir)
                    rec["path"] = str(out_dir.relative_to(snap_root))
            except SnapshotError as e:
                rec["status"] = "failed"
                rec["error"] = str(e)
                failures.append(str(e))
            results.append(rec)
            progress.advance(task)

    manifest = {
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "repo_count": len(repos),
        "format": fmt,
        "results": results,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_m = manifest_path.with_suffix(".json.tmp")
    tmp_m.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    tmp_m.replace(manifest_path)
    console.print(f"Wrote [green]{manifest_path}[/green]")

    if failures:
        console.print(f"[yellow]{len(failures)} repo(s) failed[/yellow]")

    if skip_rclone or dry_run:
        return

    remote = rclone_remote.strip()
    if not remote:
        console.print("[yellow]No --rclone-remote / GH_ARCHIVAL_RCLONE_REMOTE; skip upload[/yellow]")
        return

    if not rclone_available():
        raise click.ClickException("rclone not found; install or use --skip-rclone")

    dest = remote.rstrip("/") + "/" + run_id
    if rclone_path_suffix.strip():
        dest = dest.rstrip("/") + "/" + rclone_path_suffix.strip().strip("/")

    extra = list(rclone_extra)
    try:
        rclone_copy_local_to_remote(snap_root, dest, dry_run=False, extra_args=extra)
    except RcloneError as e:
        raise click.ClickException(str(e)) from e
    console.print(f"Uploaded snapshot to [green]{dest}[/green]")


def main() -> None:
    cli()
