"""CLI for the full-stack software archive."""

from __future__ import annotations

import hashlib
import json
import shlex
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import click
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DESTINATION = Path("/mnt/models/d5/full-stack-archives")
MANIFEST_FILES = [
    "README.md",
    "BOM.md",
    "BOM-GAPS.md",
    "epochs.yaml",
    "compatibility-matrix.yaml",
    "projects.yaml",
    "download-manifest.yaml",
]
LAYOUT_DIRS = [
    "manifests",
    "manifests/checksums",
    "manifests/source",
    "indexes",
    "os/ubuntu-18.04.6",
    "os/ubuntu-20.04.6",
    "os/ubuntu-22.04.4",
    "os/ubuntu-24.04.1",
    "os/ubuntu-24.04.2",
    "nvidia/drivers/381",
    "nvidia/drivers/384",
    "nvidia/drivers/387",
    "nvidia/drivers/390",
    "nvidia/drivers/396",
    "nvidia/drivers/410",
    "nvidia/drivers/418",
    "nvidia/drivers/430",
    "nvidia/drivers/440",
    "nvidia/drivers/450",
    "nvidia/drivers/470",
    "nvidia/drivers/525",
    "nvidia/drivers/535",
    "nvidia/drivers/550",
    "nvidia/drivers/570",
    "nvidia/cuda/10.2",
    "nvidia/cuda/11.3",
    "nvidia/cuda/11.8",
    "nvidia/cuda/12.1",
    "nvidia/cuda/12.4",
    "nvidia/cuda/12.8",
    "nvidia/cudnn",
    "nvidia/nccl",
    "nvidia/tensorrt",
    "compilers/gcc/7",
    "compilers/gcc/8",
    "compilers/gcc/9",
    "compilers/gcc/10",
    "compilers/gcc/11",
    "compilers/gcc/13",
    "compilers/cpp",
    "compilers/cpp/llvm",
    "compilers/cpp/cmake",
    "compilers/cpp/ninja",
    "compilers/go",
    "compilers/java",
    "compilers/java/openjdk",
    "compilers/java/maven",
    "compilers/java/gradle",
    "compilers/rust",
    "python/3.8",
    "python/3.9",
    "python/3.10",
    "python/3.11",
    "python/3.12",
    "wheels/e0-cu102-py38",
    "wheels/e1-cu113-py39",
    "wheels/e2-cu118-py310",
    "wheels/e3-cu121-py311",
    "wheels/e4-cu124-py311",
    "wheels/e4-cu128-py312",
    "sdists",
    "packages/debs",
    "packages/rpms",
    "packages/arch",
    "repos",
    "source-archives",
    "containers",
    "containers/k3s",
    "containers/helm",
    "containers/containerd",
    "containers/nerdctl",
    "docs",
    "docs/catalog",
    "docs/compatibility",
    "docs/rebuild-guides",
    "logs",
    "state",
]
DOWNLOAD_STATE_PATH = Path("state/download-state.json")
WHEEL_REPORT_PATH = Path("state/wheel-download-report.json")


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        data = yaml.safe_load(handle)
    return data or {}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(content)
    tmp.replace(path)


def _sync_manifests(destination: Path) -> None:
    target_dir = destination / "manifests" / "source"
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename in MANIFEST_FILES:
        src = PROJECT_ROOT / filename
        if src.exists():
            _atomic_write(target_dir / filename, src.read_text())


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_checksum_outputs(destination: Path, state: dict[str, Any]) -> None:
    json_path = destination / DOWNLOAD_STATE_PATH
    _atomic_write(json_path, json.dumps(state, indent=2, sort_keys=True) + "\n")

    lines = []
    for rel_path, meta in sorted(state.get("files", {}).items()):
        lines.append(f"{meta['sha256']}  {rel_path}")
    _atomic_write(destination / "manifests" / "checksums" / "local-sha256sums.txt", "\n".join(lines) + ("\n" if lines else ""))


def _refresh_checksums(destination: Path) -> None:
    lines: list[str] = []
    for path in sorted(destination.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(destination)
        if rel_path.as_posix() in {
            "manifests/checksums/local-sha256sums.txt",
            "state/download-state.json",
            "state/wheel-download-report.json",
        }:
            continue
        if path.name.endswith(".aria2"):
            continue
        lines.append(f"{_sha256_file(path)}  {rel_path.as_posix()}")
    _atomic_write(destination / "manifests" / "checksums" / "local-sha256sums.txt", "\n".join(lines) + ("\n" if lines else ""))


def _is_optional_item(item: dict[str, Any], url: str, rel_path: str) -> bool:
    if item.get("optional"):
        return True
    soft_suffixes = (
        "license.txt",
        ".md5sum",
        ".sha256sum",
        ".asc",
        ".sig",
        ".sigstore",
    )
    if rel_path.endswith(soft_suffixes) or url.endswith(soft_suffixes):
        return True
    return False


def _download_with_tool(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    aria2c = shutil.which("aria2c")
    if aria2c:
        subprocess.run(
            [
                aria2c,
                "--continue=true",
                "--auto-file-renaming=false",
                "--allow-overwrite=true",
                "--summary-interval=0",
                "--console-log-level=warn",
                "--dir",
                str(target.parent),
                "--out",
                target.name,
                url,
            ],
            check=True,
        )
        return

    curl = shutil.which("curl")
    if curl:
        subprocess.run(
            [
                curl,
                "-fL",
                "-C",
                "-",
                "--output",
                str(target),
                url,
            ],
            check=True,
        )
        return

    wget = shutil.which("wget")
    if wget:
        subprocess.run(
            [
                wget,
                "-c",
                "-O",
                str(target),
                url,
            ],
            check=True,
        )
        return

    raise click.ClickException("Need one of: aria2c, curl, or wget")


def _select_bundles(
    manifest: dict[str, Any], groups: tuple[str, ...], ids: tuple[str, ...]
) -> list[dict[str, Any]]:
    bundles = manifest.get("bundles", [])
    if groups:
        allowed_groups = set(groups)
        bundles = [bundle for bundle in bundles if bundle.get("group") in allowed_groups]
    if ids:
        allowed_ids = set(ids)
        bundles = [bundle for bundle in bundles if bundle.get("id") in allowed_ids]
    return bundles


def _parse_requirements_file(path: Path) -> tuple[list[str], list[str]]:
    options: list[str] = []
    requirements: list[str] = []
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("--"):
            options.extend(shlex.split(line))
        else:
            requirements.append(line)
    return options, requirements


def _ensure_pip() -> None:
    check = subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if check.returncode == 0:
        return
    subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"], check=True)


def _wheel_target_info(requirements_path: Path) -> tuple[str, str]:
    name = requirements_path.stem.replace("requirements-", "")
    py_part = next(part for part in name.split("-") if part.startswith("py"))
    py_digits = py_part[2:]
    if len(py_digits) == 2:
        python_version = f"{py_digits[0]}.{py_digits[1]}"
        abi = f"cp{py_digits}"
    else:
        python_version = f"{py_digits[0]}.{py_digits[1:]}"
        abi = f"cp{py_digits}"
    return python_version, abi


def _normalize_epoch_key(value: str) -> str:
    return value.lower().replace("_", "-")


def _compatibility_summary(matrix: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Compatibility Summary",
        "",
        "Projects and releases that are sensitive to OS, compiler, Python, CUDA, and Torch compatibility.",
        "",
    ]
    for item in matrix.get("projects", []):
        lines.append(f"## {item['project']}")
        lines.append("")
        for release in item.get("releases", []):
            epochs = ", ".join(release.get("supported_epochs", [])) or "-"
            python = ", ".join(release.get("python", [])) or "-"
            gcc = ", ".join(release.get("gcc", [])) or "-"
            cuda = ", ".join(release.get("cuda", [])) or "-"
            torch = ", ".join(release.get("torch", [])) or "-"
            lines.append(
                f"- `{release['version']}`: epochs={epochs}; python={python}; gcc={gcc}; cuda={cuda}; torch={torch}"
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _epoch_software_matrix(matrix: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Epoch Software Matrix",
        "",
        "Required software anchors for each compatibility epoch.",
        "",
    ]
    for epoch_id, entry in matrix.get("epoch_requirements", {}).items():
        lines.append(f"## {epoch_id} - {entry.get('role', '')}".rstrip())
        lines.append("")
        lines.append(f"- OS: {', '.join(f'`{item}`' for item in entry.get('os', []))}")
        lines.append(f"- Driver: {', '.join(f'`{item}`' for item in entry.get('driver', []))}")
        lines.append(f"- CUDA: {', '.join(f'`{item}`' for item in entry.get('cuda', []))}")
        lines.append(f"- GCC: {', '.join(f'`{item}`' for item in entry.get('gcc', []))}")
        lines.append(f"- Python: {', '.join(f'`{item}`' for item in entry.get('python', []))}")
        lines.append("- Required software:")
        for item in entry.get("required_software", []):
            lines.append(f"  - `{item}`")
        notes = entry.get("notes", [])
        if notes:
            lines.append("- Notes:")
            for note in notes:
                lines.append(f"  - {note}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _projects_by_category(projects_doc: dict[str, Any]) -> str:
    category_map = {item["id"]: item["description"] for item in projects_doc.get("categories", [])}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in projects_doc.get("projects", []):
        grouped[item["category"]].append(item)

    lines = ["# Projects By Category", ""]
    for category_id, items in sorted(grouped.items()):
        lines.append(f"## {category_id}")
        description = category_map.get(category_id)
        if description:
            lines.append("")
            lines.append(description)
        lines.append("")
        for item in sorted(items, key=lambda entry: entry["id"]):
            epochs = ", ".join(item.get("supported_epochs", []))
            lines.append(f"- `{item['id']}` ({item['priority']}, epochs: {epochs})")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _package_targets(projects_doc: dict[str, Any]) -> str:
    lines = [
        "# Package Targets",
        "",
        "Desired distro package forms for each archived project family.",
        "",
    ]
    for item in projects_doc.get("projects", []):
        package_names = item.get("package_names", {})
        lines.append(f"## {item['id']}")
        lines.append("")
        for label, key in [
            ("Debian/Ubuntu", "debian_family"),
            ("RPM", "rpm_family"),
            ("Arch", "arch_linux"),
        ]:
            names = package_names.get(key, [])
            rendered = ", ".join(f"`{name}`" for name in names) if names else "_No package names recorded yet_"
            lines.append(f"- {label}: {rendered}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _inventory_json(
    epochs: dict[str, Any], matrix: dict[str, Any], projects_doc: dict[str, Any], destination: Path
) -> str:
    project_count = len(projects_doc.get("projects", []))
    category_counts = Counter(item["category"] for item in projects_doc.get("projects", []))
    compatibility_count = len(matrix.get("projects", []))
    payload = {
        "project_root": str(PROJECT_ROOT),
        "default_destination": str(destination),
        "epoch_ids": [epoch["id"] for epoch in epochs.get("epochs", [])],
        "project_count": project_count,
        "compatibility_project_count": compatibility_count,
        "category_counts": dict(sorted(category_counts.items())),
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _load_documents() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    epochs = _read_yaml(PROJECT_ROOT / "epochs.yaml")
    matrix = _read_yaml(PROJECT_ROOT / "compatibility-matrix.yaml")
    projects_doc = _read_yaml(PROJECT_ROOT / "projects.yaml")
    return epochs, matrix, projects_doc


def _bootstrap_destination(destination: Path) -> None:
    epochs, matrix, projects_doc = _load_documents()

    for relative in LAYOUT_DIRS:
        (destination / relative).mkdir(parents=True, exist_ok=True)

    _sync_manifests(destination)

    _atomic_write(destination / "indexes" / "compatibility-summary.md", _compatibility_summary(matrix))
    _atomic_write(destination / "indexes" / "epoch-software-matrix.md", _epoch_software_matrix(matrix))
    _atomic_write(destination / "indexes" / "projects-by-category.md", _projects_by_category(projects_doc))
    _atomic_write(destination / "indexes" / "package-targets.md", _package_targets(projects_doc))
    _atomic_write(destination / "docs" / "compatibility" / "compatibility-summary.md", _compatibility_summary(matrix))
    _atomic_write(destination / "docs" / "compatibility" / "epoch-software-matrix.md", _epoch_software_matrix(matrix))
    _atomic_write(destination / "docs" / "catalog" / "projects-by-category.md", _projects_by_category(projects_doc))
    _atomic_write(destination / "docs" / "catalog" / "package-targets.md", _package_targets(projects_doc))
    _atomic_write(destination / "state" / "inventory.json", _inventory_json(epochs, matrix, projects_doc, destination))


@click.group()
def cli() -> None:
    """Manage the full-stack software archive."""


@cli.command("summary")
def summary() -> None:
    """Print a compact manifest summary."""
    epochs, matrix, projects_doc = _load_documents()
    click.echo(f"Epochs: {', '.join(epoch['id'] for epoch in epochs.get('epochs', []))}")
    click.echo(f"Compatibility-tracked projects: {len(matrix.get('projects', []))}")
    click.echo(f"Archive catalog projects: {len(projects_doc.get('projects', []))}")


@cli.command("bootstrap-d5")
@click.option(
    "--destination",
    type=click.Path(path_type=Path),
    default=DEFAULT_DESTINATION,
    show_default=True,
    help="Archive root on D5.",
)
def bootstrap_d5(destination: Path) -> None:
    """Create the D5 archive layout and sync manifest/index files."""
    _bootstrap_destination(destination)
    click.echo(f"Bootstrapped full-stack archive at {destination}")


@cli.command("download-direct")
@click.option(
    "--manifest",
    type=click.Path(path_type=Path),
    default=PROJECT_ROOT / "download-manifest.yaml",
    show_default=True,
    help="Pinned direct-download manifest.",
)
@click.option(
    "--destination",
    type=click.Path(path_type=Path),
    default=DEFAULT_DESTINATION,
    show_default=True,
    help="Archive root on D5.",
)
@click.option("--group", "groups", multiple=True, help="Only download bundles in this group.")
@click.option("--id", "ids", multiple=True, help="Only download a specific bundle id.")
@click.option("--limit-bundles", type=int, default=None, help="Download only the first N selected bundles.")
@click.option("--continue-on-error", is_flag=True, help="Keep going if one bundle fails.")
def download_direct(
    manifest: Path,
    destination: Path,
    groups: tuple[str, ...],
    ids: tuple[str, ...],
    limit_bundles: int | None,
    continue_on_error: bool,
) -> None:
    """Download direct artifacts idempotently and resumably."""
    _bootstrap_destination(destination)
    manifest_doc = _read_yaml(manifest)
    bundles = _select_bundles(manifest_doc, groups, ids)
    if limit_bundles is not None:
        bundles = bundles[:limit_bundles]
    if not bundles:
        raise click.ClickException("No bundles matched the requested filters.")

    state = _read_json(destination / DOWNLOAD_STATE_PATH)
    state.setdefault("files", {})
    state["manifest"] = str(manifest)

    for bundle in bundles:
        click.echo(f"==> {bundle['id']} ({bundle.get('group', 'ungrouped')})")
        try:
            for item in bundle.get("items", []):
                rel_path = item["path"]
                url = item["url"]
                target = destination / rel_path
                control = target.with_suffix(target.suffix + ".aria2")
                if target.exists() and target.stat().st_size > 0 and not control.exists():
                    click.echo(f"skip  {rel_path}")
                else:
                    click.echo(f"fetch {rel_path}")
                    try:
                        _download_with_tool(url, target)
                    except Exception:
                        if _is_optional_item(item, url, rel_path):
                            click.echo(f"warn  optional missing: {rel_path}", err=True)
                            continue
                        raise

                state["files"][rel_path] = {
                    "url": url,
                    "size": target.stat().st_size,
                    "sha256": _sha256_file(target),
                }
                _write_checksum_outputs(destination, state)
        except Exception as exc:
            if not continue_on_error:
                raise
            click.echo(f"error {bundle['id']}: {exc}", err=True)

    click.echo(f"Downloaded {len(bundles)} bundle(s) into {destination}")


@cli.command("refresh-checksums")
@click.option(
    "--destination",
    type=click.Path(path_type=Path),
    default=DEFAULT_DESTINATION,
    show_default=True,
    help="Archive root on D5.",
)
def refresh_checksums(destination: Path) -> None:
    """Recompute the local SHA-256 manifest for all archived files."""
    _refresh_checksums(destination)
    click.echo(f"Refreshed local checksums under {destination}")


@cli.command("download-wheelhouse")
@click.option(
    "--requirements-dir",
    type=click.Path(path_type=Path),
    default=PROJECT_ROOT / "requirements",
    show_default=True,
    help="Directory containing per-epoch requirements files.",
)
@click.option(
    "--epoch",
    "epochs",
    multiple=True,
    help="Epoch or requirements stem to download, e.g. E2 or e2-cu118-py310.",
)
@click.option(
    "--destination",
    type=click.Path(path_type=Path),
    default=DEFAULT_DESTINATION,
    show_default=True,
    help="Archive root on D5.",
)
@click.option("--continue-on-error", is_flag=True, default=True, help="Continue when one package has no matching wheel.")
def download_wheelhouse(
    requirements_dir: Path,
    epochs: tuple[str, ...],
    destination: Path,
    continue_on_error: bool,
) -> None:
    """Download wheelhouses per epoch using pinned requirement files."""
    _bootstrap_destination(destination)
    requirement_files = sorted(requirements_dir.glob("requirements-*.txt"))
    if not requirement_files:
        raise click.ClickException(f"No requirements files found in {requirements_dir}")

    selected: list[Path] = []
    wanted = {_normalize_epoch_key(item) for item in epochs}
    for path in requirement_files:
        stem_key = _normalize_epoch_key(path.stem.replace("requirements-", ""))
        epoch_key = _normalize_epoch_key(path.stem.split("-")[1]) if "-" in path.stem else stem_key
        if not wanted or stem_key in wanted or epoch_key in wanted:
            selected.append(path)

    if not selected:
        raise click.ClickException("No requirements files matched the requested epochs.")

    _ensure_pip()
    report: dict[str, Any] = _read_json(destination / WHEEL_REPORT_PATH)
    report.setdefault("epochs", {})

    for req_path in selected:
        name = req_path.stem.replace("requirements-", "")
        python_version, abi = _wheel_target_info(req_path)
        wheel_dir = destination / "wheels" / name
        wheel_dir.mkdir(parents=True, exist_ok=True)
        options, requirements = _parse_requirements_file(req_path)
        epoch_report = report["epochs"].setdefault(name, {"downloaded": [], "failed": []})
        click.echo(f"==> wheelhouse {name}")

        for requirement in requirements:
            click.echo(f"wheel {requirement}")
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--dest",
                str(wheel_dir),
                "--exists-action",
                "i",
                "--only-binary",
                ":all:",
                "--platform",
                "manylinux2014_x86_64",
                "--implementation",
                "cp",
                "--python-version",
                python_version,
                "--abi",
                abi,
            ]
            cmd.extend(options)
            cmd.append(requirement)
            try:
                subprocess.run(cmd, check=True)
                if requirement not in epoch_report["downloaded"]:
                    epoch_report["downloaded"].append(requirement)
            except Exception as exc:
                if requirement not in epoch_report["failed"]:
                    epoch_report["failed"].append(requirement)
                if not continue_on_error:
                    raise
                click.echo(f"warn  wheel missing or failed: {requirement} ({exc})", err=True)

        _atomic_write(destination / WHEEL_REPORT_PATH, json.dumps(report, indent=2, sort_keys=True) + "\n")

    _refresh_checksums(destination)
    click.echo(f"Downloaded wheelhouse bundles into {destination}")


@cli.command("export-package-plans")
@click.option(
    "--destination",
    type=click.Path(path_type=Path),
    default=DEFAULT_DESTINATION,
    show_default=True,
    help="Archive root on D5.",
)
def export_package_plans(destination: Path) -> None:
    """Export deduplicated distro package lists from the project catalog."""
    _bootstrap_destination(destination)
    _, _, projects_doc = _load_documents()

    by_epoch: dict[str, dict[str, set[str]]] = defaultdict(lambda: {"debs": set(), "rpms": set(), "arch": set()})
    for item in projects_doc.get("projects", []):
        package_names = item.get("package_names", {})
        epochs = item.get("supported_epochs", [])
        for epoch in epochs:
            by_epoch[epoch]["debs"].update(package_names.get("debian_family", []))
            by_epoch[epoch]["rpms"].update(package_names.get("rpm_family", []))
            by_epoch[epoch]["arch"].update(package_names.get("arch_linux", []))

    for epoch, groups in by_epoch.items():
        for key, filename in [("debs", "debs.txt"), ("rpms", "rpms.txt"), ("arch", "arch.txt")]:
            body = "\n".join(sorted(groups[key])) + ("\n" if groups[key] else "")
            _atomic_write(destination / "packages" / key / f"{epoch.lower()}-{filename}", body)

    click.echo(f"Exported package plans into {destination}/packages")


if __name__ == "__main__":
    cli()
