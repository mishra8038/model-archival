"""
CLI entry point for the model-fingerprints tool.

Commands:
  fingerprints run      — Crawl all repos in the registry (resumable, concurrent)
  fingerprints status   — Show crawl progress summary
  fingerprints show     — Print the fingerprint for a specific repo
  fingerprints verify   — Check a local file against a stored fingerprint
"""

from __future__ import annotations

import hashlib
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from .crawler import Crawler
from .models import Registry, ModelEntry
from .state import RunState, STATUS_COMPLETE, STATUS_FAILED, STATUS_SKIPPED, STATUS_PENDING
from .storage import append_global_index, load_fingerprint, write_fingerprint

console = Console()


def _find_registry() -> Path:
    candidate = Path(__file__).parents[3] / "config" / "registry.yaml"
    if candidate.exists():
        return candidate
    return Path("config/registry.yaml")


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)-8s %(message)s", datefmt="%H:%M:%S")
    # Suppress noisy HTTP logs from httpx / huggingface_hub unless verbose
    if not verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("huggingface_hub").setLevel(logging.WARNING)


def _get_token() -> Optional[str]:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        token_file = Path.home() / ".hf_token"
        if token_file.exists():
            token = token_file.read_text().strip() or None
    return token


def _resolve_output(output: str) -> Path:
    p = Path(output)
    if p.name != "model-checksums":
        return p / "model-checksums"
    return p


@click.group()
@click.option("--registry", default=str(_find_registry()), show_default=True,
              help="Path to registry.yaml")
@click.option("--output", "-o", default="/mnt/models/d1",
              show_default=True,
              help="Root output directory (model-checksums/ created inside)")
@click.option("--verbose", "-v", is_flag=True)
@click.pass_context
def cli(ctx: click.Context, registry: str, output: str, verbose: bool) -> None:
    """Model fingerprint harvester — SHA-256 hashes for LLM weight files."""
    _setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["registry_path"] = Path(registry)
    ctx.obj["output_root"]   = _resolve_output(output)
    ctx.obj["verbose"]       = verbose


@cli.command()
@click.option("--tier",        default=None, help="Filter by tier (A/B/C/D)")
@click.option("--family",      default=None, help="Filter by family (deepseek/llama/...)")
@click.option("--importance",  default=None, help="Filter by importance (critical/high/medium)")
@click.option("--workers", "-j", default=1, show_default=True,
              help="Concurrent crawl workers")
@click.option("--dry-run",     is_flag=True, help="List what would be crawled without running")
@click.option("--force",       is_flag=True, help="Re-crawl repos already marked complete")
@click.pass_context
def run(
    ctx: click.Context,
    tier: Optional[str],
    family: Optional[str],
    importance: Optional[str],
    workers: int,
    dry_run: bool,
    force: bool,
) -> None:
    """Crawl repos and save SHA-256 fingerprints. No weights are downloaded."""
    registry_path: Path = ctx.obj["registry_path"]
    output_root: Path   = ctx.obj["output_root"]

    reg = Registry.load(registry_path)
    token = _get_token()
    models = reg.filter(tier=tier, importance=importance, family=family)

    if not models:
        console.print("[yellow]No models matched the filter criteria.[/]")
        return

    output_root.mkdir(parents=True, exist_ok=True)
    state = RunState(output_root / "run_state.json")
    index_path = output_root / "index.jsonl"

    console.rule("[bold]model-fingerprints[/]")
    console.print(f"Registry : {registry_path}")
    console.print(f"Output   : {output_root}")
    console.print(f"Models   : {len(models)}")
    console.print(f"Workers  : {workers}")
    console.print(f"HF token : {'[green]present[/]' if token else '[red]missing — gated repos will be skipped[/]'}")
    console.print()

    if dry_run:
        t = Table("Repo", "Tier", "Importance", "Auth", "Status")
        for m in models:
            t.add_row(
                m.hf_repo, m.tier, m.importance,
                "yes" if m.requires_auth else "no",
                state.get_status(m.hf_repo),
            )
        console.print(t)
        return

    # Filter out already-complete unless --force
    to_crawl = [
        m for m in models
        if force or state.get_status(m.hf_repo) != STATUS_COMPLETE
    ]
    skipped_complete = len(models) - len(to_crawl)
    if skipped_complete:
        console.print(f"[dim]Skipping {skipped_complete} already-complete repos (use --force to re-crawl)[/]\n")

    n_done = n_skip = n_fail = 0

    def _crawl_one(model: ModelEntry) -> tuple[ModelEntry, str, str]:
        """Returns (model, status, message)."""
        if model.requires_auth and not token:
            return model, "skipped", "no HF token"
        try:
            crawler = Crawler(hf_token=token)
            repo_fp = crawler.crawl(model.hf_repo)
            write_fingerprint(repo_fp, model, output_root)
            append_global_index(index_path, repo_fp, model)
            state.set_complete(model.hf_repo, repo_fp.crawled_at, len(repo_fp.files))
            size = f"{repo_fp.total_size_bytes / 1024**3:.1f} GB"
            return model, "done", f"{len(repo_fp.files)} files  {size}"
        except PermissionError as e:
            state.set_skipped(model.hf_repo, str(e))
            return model, "skipped", str(e)
        except FileNotFoundError as e:
            state.set_failed(model.hf_repo, str(e))
            return model, "failed", str(e)
        except Exception as e:
            state.set_failed(model.hf_repo, str(e))
            logging.exception("Error crawling %s", model.hf_repo)
            return model, "failed", str(e)

    total = len(to_crawl)
    done_count = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_crawl_one, m): m for m in to_crawl}
        for future in as_completed(futures):
            model, status, msg = future.result()
            done_count += 1
            prefix = f"[{done_count}/{total}]"
            if status == "done":
                console.print(f"[green]{prefix} ✓  {model.hf_repo}  ({msg})[/]")
                n_done += 1
            elif status == "skipped":
                console.print(f"[yellow]{prefix} –  {model.hf_repo}  ({msg})[/]")
                n_skip += 1
            else:
                console.print(f"[red]{prefix} ✗  {model.hf_repo}  ({msg})[/]")
                n_fail += 1

    console.rule()
    console.print(
        f"Done.  "
        f"Crawled: [green]{n_done}[/]  "
        f"Skipped: [yellow]{n_skip}[/]  "
        f"Failed: [red]{n_fail}[/]"
    )


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show crawl progress for all repos in the registry."""
    registry_path: Path = ctx.obj["registry_path"]
    output_root: Path   = ctx.obj["output_root"]

    reg = Registry.load(registry_path)
    state = RunState(output_root / "run_state.json")

    t = Table(title="Fingerprint status")
    t.add_column("Repo", style="cyan", no_wrap=True)
    t.add_column("Tier", width=5)
    t.add_column("Importance", width=10)
    t.add_column("Status", width=9)
    t.add_column("Files", width=6)
    t.add_column("Crawled at", width=17)

    counts = {STATUS_PENDING: 0, STATUS_COMPLETE: 0, STATUS_FAILED: 0, STATUS_SKIPPED: 0}
    for model in reg.models:
        s = state.get_status(model.hf_repo)
        entry = state.all_entries().get(model.hf_repo, {})
        files = str(entry.get("file_count", "—"))
        crawled = (entry.get("crawled_at") or "")[:16]
        color = {"complete": "green", "failed": "red", "skipped": "yellow"}.get(s, "dim")
        t.add_row(model.hf_repo, model.tier, model.importance, f"[{color}]{s}[/]", files, crawled)
        counts[s] = counts.get(s, 0) + 1

    console.print(t)
    console.print(
        f"\nTotal: {len(reg.models)}  "
        f"[green]complete: {counts[STATUS_COMPLETE]}[/]  "
        f"[dim]pending: {counts[STATUS_PENDING]}[/]  "
        f"[yellow]skipped: {counts[STATUS_SKIPPED]}[/]  "
        f"[red]failed: {counts[STATUS_FAILED]}[/]"
    )


@cli.command()
@click.argument("hf_repo")
@click.pass_context
def show(ctx: click.Context, hf_repo: str) -> None:
    """Print the stored fingerprint for a specific HF repo."""
    output_root: Path = ctx.obj["output_root"]
    repo_dir = output_root / hf_repo.replace("/", "__")
    md_path = repo_dir / "fingerprint.md"
    if md_path.exists():
        console.print(md_path.read_text())
    elif (repo_dir / "fingerprint.json").exists():
        import json
        console.print(json.dumps(load_fingerprint(repo_dir), indent=2))
    else:
        console.print(f"[red]No fingerprint found for {hf_repo}[/]")
        sys.exit(1)


@cli.command()
@click.argument("hf_repo")
@click.argument("file_path", type=click.Path(exists=True))
@click.pass_context
def verify(ctx: click.Context, hf_repo: str, file_path: str) -> None:
    """Verify a local file against the stored fingerprint for HF_REPO."""
    output_root: Path = ctx.obj["output_root"]
    repo_dir = output_root / hf_repo.replace("/", "__")
    fp = load_fingerprint(repo_dir)
    if fp is None:
        console.print(f"[red]No fingerprint found for {hf_repo}[/]")
        sys.exit(1)

    target = Path(file_path)
    matches = [f for f in fp.get("files", []) if f["filename"].endswith(target.name)]
    if not matches:
        console.print(f"[red]No fingerprint entry found for '{target.name}'[/]")
        sys.exit(1)

    console.print(f"Computing SHA-256 of {target} ...")
    h = hashlib.sha256()
    with open(target, "rb") as fh:
        for chunk in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    actual = h.hexdigest()

    ok = any(actual == m["sha256"] for m in matches)
    for m in matches:
        console.print(f"  Expected : {m['sha256']}")
    console.print(f"  Actual   : {actual}")

    if ok:
        console.print(f"[green]✓ PASS — {target.name}[/]")
    else:
        console.print(f"[red]✗ FAIL — {target.name}[/]")
        sys.exit(1)
