"""Pre-flight checks run before any download begins."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Optional

import httpx
import psutil

from archiver.models import Registry

log = logging.getLogger(__name__)

MIN_FREE_ABORT_GB = 50          # abort if less than this free
MIN_FREE_WARN_PCT = 10          # warn if headroom below this %


class PreflightError(RuntimeError):
    """A critical pre-flight check failed — abort the run."""


class PreflightWarning(UserWarning):
    """A non-critical pre-flight issue — continue but warn."""


def check_aria2c() -> None:
    if not shutil.which("aria2c"):
        raise PreflightError(
            "aria2c not found in PATH.\n"
            "  Debian/Ubuntu: sudo apt install aria2\n"
            "  Arch:          sudo pacman -S aria2\n"
            "  Fedora:        sudo dnf install aria2"
        )
    log.info("✓ aria2c found: %s", shutil.which("aria2c"))


def check_network() -> None:
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.head("https://huggingface.co")
            resp.raise_for_status()
        log.info("✓ huggingface.co reachable (HTTP %d)", resp.status_code)
    except Exception as e:
        raise PreflightError(f"Cannot reach huggingface.co: {e}") from e


def check_drives(registry: Registry, skip_space_check: bool = False) -> list[str]:
    """
    Verify all drive mount points exist and are writable.
    Returns list of warning strings (non-fatal space warnings).
    If skip_space_check is True, do not abort on low free space (e.g. D2 full by design).
    """
    warnings = []
    missing = []

    for label, drive in registry.drives.items():
        mp = drive.mount_point
        if not mp.exists():
            missing.append(f"Drive {label}: mount point {mp} does not exist")
            continue
        test_file = mp / ".archiver_write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except OSError as e:
            missing.append(f"Drive {label}: mount point {mp} not writable: {e}")
            continue

        usage = psutil.disk_usage(str(mp))
        free_gb = usage.free / (1024 ** 3)
        free_pct = usage.free / usage.total * 100

        if not skip_space_check and free_gb < MIN_FREE_ABORT_GB:
            missing.append(
                f"Drive {label} ({mp}): only {free_gb:.1f} GB free — "
                f"below minimum {MIN_FREE_ABORT_GB} GB"
            )
        elif free_pct < MIN_FREE_WARN_PCT:
            warnings.append(
                f"Drive {label} ({mp}): {free_pct:.1f}% free ({free_gb:.0f} GB) — "
                "less than 10% headroom"
            )
        else:
            log.info("✓ Drive %s (%s): %.0f GB free (%.0f%%)", label, mp, free_gb, free_pct)

    if missing:
        raise PreflightError("Drive checks failed:\n" + "\n".join(f"  • {m}" for m in missing))

    return warnings


def check_hf_token(token: Optional[str], registry: Registry) -> dict[str, bool]:
    """
    Test the HF token against gated model repos.
    Returns {model_id: accessible}.
    If token is None, returns empty dict (no check, non-fatal).
    """
    if not token:
        gated = registry.gated()
        if gated:
            log.warning(
                "HF_TOKEN not set — %d gated models will be skipped: %s",
                len(gated),
                ", ".join(m.id for m in gated),
            )
        return {}

    results: dict[str, bool] = {}
    headers = {"Authorization": f"Bearer {token}"}
    for model in registry.gated():
        url = f"https://huggingface.co/api/models/{model.hf_repo}"
        try:
            with httpx.Client(timeout=15, headers=headers) as client:
                resp = client.get(url)
            ok = resp.status_code == 200
            results[model.id] = ok
            symbol = "✓" if ok else "✗"
            log.info("%s Token access for %s (HTTP %d)", symbol, model.id, resp.status_code)
        except Exception as e:
            results[model.id] = False
            log.warning("✗ Token check failed for %s: %s", model.id, e)

    failed = [mid for mid, ok in results.items() if not ok]
    if failed:
        log.warning(
            "Token cannot access %d model(s): %s — they will be skipped.",
            len(failed),
            ", ".join(failed),
        )
    return results


def check_registry(registry: Registry) -> None:
    errors = []
    for m in registry.models:
        if not m.hf_repo or "/" not in m.hf_repo:
            errors.append(f"{m.id}: invalid hf_repo '{m.hf_repo}'")
        if m.tier not in ("A", "B", "C", "D", "E", "F", "G"):
            errors.append(f"{m.id}: invalid tier '{m.tier}'")
        if m.priority not in (1, 2):
            errors.append(f"{m.id}: invalid priority {m.priority}")
        if m.drive not in registry.drives and registry.drives:
            errors.append(f"{m.id}: drive '{m.drive}' not in drives config")
    if errors:
        raise PreflightError(
            "Registry validation errors:\n" + "\n".join(f"  • {e}" for e in errors)
        )
    log.info("✓ Registry valid (%d models)", len(registry.models))


def run_all(
    registry: Registry,
    hf_token: Optional[str],
    skip_network: bool = False,
    skip_drive_space_check: bool = False,
) -> tuple[list[str], dict[str, bool]]:
    """
    Run all pre-flight checks.
    Returns (warnings, token_results).
    Raises PreflightError on any critical failure.
    """
    check_aria2c()
    check_registry(registry)
    if not skip_network:
        check_network()
    warnings = check_drives(registry, skip_space_check=skip_drive_space_check)
    token_results = check_hf_token(hf_token, registry)
    return warnings, token_results
