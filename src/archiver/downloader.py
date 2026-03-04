"""
Per-model download orchestration.

Two download paths are used depending on how the file is stored on HF:

  LFS files  (legacy, most models in this registry)
    → Resolve CDN URL via HF API → submit to aria2c for resumable multi-connection download.
    → aria2c writes a <filename>.aria2 control file alongside the partial download in .tmp/.
      That control file records which byte ranges have already been received. On any restart
      (network drop, process kill, reboot) the next run starts aria2c with --continue=true,
      finds the partial file + control file in the same .tmp/ path, and resumes byte-exactly
      from where it stopped. Nothing is re-downloaded.
    → The Authorization header is sent on the initial HF request only; not forwarded to the
      CDN redirect (S3/R2 reject requests with both a pre-signed URL and an Authorization
      header). aria2's default cross-origin redirect behaviour is correct here.
    → The HF resolve URL is re-fetched immediately before each aria2 submission because
      CDN pre-signed tokens expire in ~1 hour.

  XET files  (new storage backend, default since May 2025; Llama 4, Qwen 3, future models)
    → aria2 cannot speak the two-stage CAS reconstruction protocol.
    → Use huggingface_hub.hf_hub_download() which calls hf_xet internally.
    → hf_xet does its own internal chunked download with partial state tracked in a
      .incomplete/ cache directory managed by the library.

Resume across process restarts (the most important case):
    LFS:  partial file + .aria2 control file persist in d5/.tmp/<model_id>/
          → next run's aria2 daemon finds them automatically via --continue=true
    XET:  hf_xet's incomplete cache persists across restarts (library-managed)
    Both: run_state.json records per-model status → models marked complete are skipped
          entirely; files with a .sha256 sidecar are skipped at the file level.

Idempotency:
    If a file already exists at its final location AND has a matching .sha256 sidecar,
    it is unconditionally skipped — even if run_state.json was lost or reset.
"""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from typing import Optional

from huggingface_hub import HfApi, hf_hub_download, hf_hub_url
from huggingface_hub.utils import EntryNotFoundError, RepositoryNotFoundError

from archiver.aria2_manager import Aria2Manager
from archiver.models import ModelEntry
from archiver.verifier import (
    sha256_file,
    read_sidecar,
    write_sidecar,
    write_manifest,
    write_descriptor,
    append_global_index,
)

log = logging.getLogger(__name__)

MAX_RETRIES = 5
RETRY_BACKOFF = [30, 60, 120, 300, 600]   # seconds between retries: 30s, 1m, 2m, 5m, 10m


class DownloadError(RuntimeError):
    pass


class AuthError(DownloadError):
    """HTTP 401/403 — token missing or invalid. Do not retry."""


class Downloader:
    def __init__(
        self,
        aria2: Aria2Manager,
        tmp_dir: Path,
        archive_index_path: Path,
        hf_token: Optional[str] = None,
        dry_run: bool = False,
    ) -> None:
        self.aria2 = aria2
        self.tmp_dir = tmp_dir
        self.archive_index_path = archive_index_path
        self.hf_token = hf_token
        self.dry_run = dry_run
        self._api = HfApi(token=hf_token)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def download_model(
        self,
        model: ModelEntry,
        on_file_progress=None,
        on_file_complete=None,
    ) -> dict:
        """
        Download all files for *model*.
        Returns the manifest dict on success.
        Raises DownloadError on unrecoverable failure.
        """
        log.info("Starting download: %s (tier=%s drive=%s)", model.id, model.tier, model.drive)

        if model.model_dir is None:
            raise DownloadError(f"Cannot determine model_dir for {model.id} — drive_path not set")

        # Fast-path: if manifest.json already exists and every file listed in it has
        # a matching .sha256 sidecar, the model is fully complete — skip the HF API
        # call entirely and return immediately. This is the primary guard against
        # re-downloading already-complete models when run_state.json is unavailable.
        existing_manifest = _check_manifest_complete(model.model_dir)
        if existing_manifest:
            log.info("SKIP %s — manifest.json present and all sidecars verified", model.id)
            model.commit_sha = existing_manifest.get("commit_sha")
            # Back-fill descriptor if this model was archived before DESCRIPTOR files were added
            if not (model.model_dir / "DESCRIPTOR.json").exists():
                write_descriptor(
                    model_id=model.id,
                    hf_repo=model.hf_repo,
                    commit_sha=model.commit_sha or "",
                    tier=model.tier,
                    licence=model.licence,
                    requires_auth=model.requires_auth,
                    notes=model.notes,
                    files=existing_manifest.get("files", []),
                    dest_dir=model.model_dir,
                )
            return existing_manifest

        try:
            repo_files = self._resolve_files(model)
        except (RepositoryNotFoundError, EntryNotFoundError) as e:
            raise DownloadError(f"Cannot resolve HF repo {model.hf_repo}: {e}") from e

        if not repo_files:
            raise DownloadError(f"No files found in {model.hf_repo}")

        commit_sha = repo_files[0]["commit_sha"]
        model.commit_sha = commit_sha

        dest_dir = model.model_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        if self.dry_run:
            lfs_count = sum(1 for f in repo_files if f["storage"] == "lfs")
            xet_count = sum(1 for f in repo_files if f["storage"] == "xet")
            total = sum(f["size"] for f in repo_files)
            log.info(
                "[DRY RUN] %s → %d files (%.1f GB): %d LFS (aria2) + %d XET (hf_hub)",
                model.id, len(repo_files), total / 1024**3, lfs_count, xet_count,
            )
            return {}

        completed_files = []
        for file_info in repo_files:
            result = self._download_file_with_retry(
                model=model,
                file_info=file_info,
                dest_dir=dest_dir,
                on_progress=on_file_progress,
            )
            completed_files.append(result)
            if on_file_complete:
                on_file_complete(model, file_info["filename"], result)

        manifest = write_manifest(
            model_id=model.id,
            hf_repo=model.hf_repo,
            commit_sha=commit_sha,
            tier=model.tier,
            files=completed_files,
            dest_dir=dest_dir,
        )
        write_descriptor(
            model_id=model.id,
            hf_repo=model.hf_repo,
            commit_sha=commit_sha,
            tier=model.tier,
            licence=model.licence,
            requires_auth=model.requires_auth,
            notes=model.notes,
            files=completed_files,
            dest_dir=dest_dir,
        )
        append_global_index(self.archive_index_path, manifest)

        latest = dest_dir.parent / "latest"
        if latest.is_symlink() or latest.exists():
            latest.unlink()
        latest.symlink_to(dest_dir.name)

        log.info(
            "✓ Completed %s: %d files, %.1f GB",
            model.id,
            len(completed_files),
            manifest["total_size_bytes"] / 1024**3,
        )
        return manifest

    # ------------------------------------------------------------------
    # File resolution
    # ------------------------------------------------------------------

    def _resolve_files(self, model: ModelEntry) -> list[dict]:
        """
        Query the HF API for the model's file list.
        Returns list of dicts: {filename, url, size, commit_sha, lfs_sha256, storage, _hf_repo}
        storage = "lfs" | "xet" | "direct"
        """
        revision = model.commit_sha or "main"

        repo_info = self._api.repo_info(
            repo_id=model.hf_repo,
            revision=revision,
            files_metadata=True,
        )
        commit_sha = repo_info.sha or revision

        files = []
        for sibling in (repo_info.siblings or []):
            fname = sibling.rfilename

            # Filter by file type
            if model.tier in ("A", "B", "D"):
                if not _is_weight_file(fname) and not _is_config_file(fname):
                    continue
            if model.quant_levels:
                if not any(q.upper() in fname.upper() for q in model.quant_levels):
                    if not _is_config_file(fname):
                        continue

            # Detect storage backend.
            # sibling.lfs is populated for Git LFS files; None for XET and small direct files.
            lfs_info = getattr(sibling, "lfs", None)
            if lfs_info is not None:
                storage = "lfs"
                lfs_sha256 = getattr(lfs_info, "sha256", None)
            else:
                size = sibling.size or 0
                storage = "xet" if size > 10 * 1024 * 1024 else "direct"
                lfs_sha256 = None

            url = hf_hub_url(
                repo_id=model.hf_repo,
                filename=fname,
                revision=commit_sha,
            )

            files.append({
                "filename": fname,
                "url": url,
                "size": sibling.size or 0,
                "commit_sha": commit_sha,
                "lfs_sha256": lfs_sha256,
                "storage": storage,
                "_hf_repo": model.hf_repo,
            })

        return files

    # ------------------------------------------------------------------
    # Download dispatch with retry
    # ------------------------------------------------------------------

    def _download_file_with_retry(
        self,
        model: ModelEntry,
        file_info: dict,
        dest_dir: Path,
        on_progress=None,
    ) -> dict:
        filename = file_info["filename"]
        final_path = dest_dir / filename

        # File-level idempotency: if the final file exists and has a matching .sha256
        # sidecar, skip unconditionally. This is the check that makes re-runs safe even
        # if run_state.json was lost.
        if final_path.exists():
            stored = read_sidecar(final_path)
            if stored:
                log.debug("SKIP %s (already verified at final path)", filename)
                return {
                    "path": filename,
                    "sha256": stored,
                    "size_bytes": final_path.stat().st_size,
                }

        # Deterministic tmp path — same across restarts so aria2 finds its .aria2 control file.
        tmp_subdir = self.tmp_dir / model.id.replace("/", "_")
        tmp_subdir.mkdir(parents=True, exist_ok=True)

        last_error: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            if attempt > 0:
                backoff = RETRY_BACKOFF[min(attempt - 1, len(RETRY_BACKOFF) - 1)]
                log.warning("Retry %d/%d for %s in %ds", attempt, MAX_RETRIES - 1, filename, backoff)
                time.sleep(backoff)

            try:
                if file_info["storage"] == "lfs":
                    digest = self._download_lfs(
                        file_info=file_info,
                        tmp_dir=tmp_subdir,
                        final_path=final_path,
                        on_progress=on_progress,
                    )
                else:
                    digest = self._download_via_hub(
                        model=model,
                        file_info=file_info,
                        tmp_dir=tmp_subdir,
                        final_path=final_path,
                    )
                return {
                    "path": filename,
                    "sha256": digest,
                    "size_bytes": final_path.stat().st_size,
                }
            except AuthError:
                raise
            except Exception as e:
                last_error = e
                log.error("Error downloading %s (attempt %d): %s", filename, attempt + 1, e)
                # Do NOT delete the partial file in tmp — aria2 needs it for resume.
                # Only clean up a corrupted file that landed at the final path.
                if final_path.exists():
                    final_path.unlink()

        raise DownloadError(
            f"Failed to download {filename} after {MAX_RETRIES} attempts: {last_error}"
        ) from last_error

    # ------------------------------------------------------------------
    # LFS path — aria2c (resumable)
    # ------------------------------------------------------------------

    def _download_lfs(
        self,
        file_info: dict,
        tmp_dir: Path,
        final_path: Path,
        on_progress=None,
    ) -> str:
        """
        Download a Git LFS file via aria2c.

        Resume mechanics:
          aria2c writes two files to tmp_dir:
            <filename>        — the partial data received so far
            <filename>.aria2  — control file: records which 32 MB pieces are complete
          When aria2c starts with --continue=true and finds both files at the expected
          path, it sends HTTP Range requests for only the missing pieces. No already-
          downloaded data is re-fetched.

          Because the HF resolve URL redirects to a CDN pre-signed URL that expires in
          ~1 hour, we always call hf_hub_url() fresh immediately before submitting to
          aria2. The stable /resolve/ URL is what we hand to aria2; HF issues a fresh
          CDN redirect on demand at download time. The .aria2 control file records
          completed byte ranges, not the URL, so a fresh URL is fine on every attempt.
        """
        filename = file_info["filename"]

        fresh_url = hf_hub_url(
            repo_id=file_info["_hf_repo"],
            filename=filename,
            revision=file_info["commit_sha"],
        )

        task = self.aria2.add_download(
            url=fresh_url,
            dest_dir=tmp_dir,
            filename=filename,
            model_id=str(tmp_dir),
            hf_token=self.hf_token,
        )

        log.info("DOWNLOAD (LFS/aria2) %s → %s", filename, tmp_dir)
        self.aria2.wait_for_completion(task, on_progress=on_progress)

        tmp_path = tmp_dir / filename
        if not tmp_path.exists():
            raise DownloadError(f"aria2 completed but file not found: {tmp_path}")

        actual = sha256_file(tmp_path)
        expected = file_info.get("lfs_sha256")
        if expected and actual != expected:
            tmp_path.unlink()
            # Also remove the .aria2 control file so the next attempt starts fresh.
            control = tmp_dir / (filename + ".aria2")
            if control.exists():
                control.unlink()
            raise DownloadError(
                f"Checksum mismatch for {filename}: expected {expected}, got {actual}"
            )

        final_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(tmp_path), final_path)
        # Remove the now-stale .aria2 control file (download is complete).
        control = tmp_dir / (filename + ".aria2")
        if control.exists():
            control.unlink()
        write_sidecar(final_path, actual)
        log.info("OK (LFS) %s  sha256=%s…", filename, actual[:12])
        return actual

    # ------------------------------------------------------------------
    # XET / direct path — huggingface_hub native
    # ------------------------------------------------------------------

    def _download_via_hub(
        self,
        model: ModelEntry,
        file_info: dict,
        tmp_dir: Path,
        final_path: Path,
    ) -> str:
        """
        Download a XET or small direct file via hf_hub_download().

        hf_xet (the Rust library called internally) manages its own partial state in a
        .incomplete/ directory inside the cache. On restart it resumes from the last
        completed chunk boundary. This is not as fine-grained as aria2's 32 MB pieces
        but still avoids a full re-download for large XET files.
        """
        filename = file_info["filename"]
        storage = file_info["storage"]
        log.info("DOWNLOAD (%s/hub) %s", storage.upper(), filename)

        cached = hf_hub_download(
            repo_id=model.hf_repo,
            filename=filename,
            revision=file_info["commit_sha"],
            token=self.hf_token,
            local_dir=str(tmp_dir),
        )

        tmp_path = Path(cached)
        if not tmp_path.exists():
            raise DownloadError(f"hf_hub_download returned path that does not exist: {cached}")

        actual = sha256_file(tmp_path)
        expected = file_info.get("lfs_sha256")
        if expected and actual != expected:
            tmp_path.unlink()
            raise DownloadError(
                f"Checksum mismatch for {filename}: expected {expected}, got {actual}"
            )

        final_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(tmp_path), final_path)
        write_sidecar(final_path, actual)
        log.info("OK (%s) %s  sha256=%s…", storage.upper(), filename, actual[:12])
        return actual


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_WEIGHT_EXTENSIONS = {".safetensors", ".bin", ".pt", ".pth", ".gguf", ".ggml"}
_CONFIG_EXTENSIONS = {".json", ".txt", ".model", ".tiktoken", ".py"}
_CONFIG_NAMES = {
    "config.json", "tokenizer.json", "tokenizer_config.json",
    "special_tokens_map.json", "generation_config.json",
    "vocab.json", "merges.txt", "tokenizer.model",
}


def _is_weight_file(name: str) -> bool:
    return Path(name).suffix.lower() in _WEIGHT_EXTENSIONS


def _is_config_file(name: str) -> bool:
    base = Path(name).name
    return base in _CONFIG_NAMES or Path(name).suffix.lower() in _CONFIG_EXTENSIONS


def _check_manifest_complete(model_dir: Path) -> Optional[dict]:
    """
    Return the manifest dict if:
      1. manifest.json exists in model_dir, AND
      2. every file listed in the manifest exists at its final path, AND
      3. every such file has a .sha256 sidecar (written only after successful verify)

    Returns None if any condition fails — triggering a normal download pass.
    The sidecar check is intentionally lightweight (existence only, not re-hash)
    because the sidecar is only written after a successful SHA-256 verification
    at download time. A full re-hash is available via `archiver verify`.
    """
    manifest_path = model_dir / "manifest.json"
    if not manifest_path.exists():
        return None

    try:
        import json
        manifest = json.loads(manifest_path.read_text())
    except Exception:
        return None

    for entry in manifest.get("files", []):
        file_path = model_dir / entry["path"]
        if not file_path.exists():
            return None
        sidecar = file_path.with_suffix(file_path.suffix + ".sha256")
        if not sidecar.exists():
            return None

    return manifest if manifest.get("files") else None
