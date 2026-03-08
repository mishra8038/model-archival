"""
Fingerprint storage.

On-disk layout under the output root (e.g. /mnt/models/d1/model-checksums/):

  model-checksums/
  ├── index.jsonl                         # append-only global index, one line per repo
  ├── deepseek-ai__DeepSeek-V3/
  │   ├── fingerprint.json                # structured data
  │   └── fingerprint.md                  # human-readable
  ├── meta-llama__Llama-3.3-70B-Instruct/
  │   └── ...
  └── ...

fingerprint.json schema:
  {
    "schema_version": "1.1",
    "hf_repo":        "deepseek-ai/DeepSeek-V3",
    "hf_url":         "https://huggingface.co/deepseek-ai/DeepSeek-V3",
    "family":         "deepseek",
    "tier":           "A",
    "importance":     "critical",
    "licence":        "MIT",
    "requires_auth":  false,
    "notes":          "",
    "parent_model":   null,
    "method":         null,
    "commit_sha":     "e815299b...",
    "crawled_at":     "2026-03-08T...",
    "file_count":     163,
    "total_size_bytes": 685123456789,
    "total_size_human": "638.1 GB",
    "files": [
      {"filename": "model-00001-of-00163.safetensors", "sha256": "abc...", "size_bytes": 9876543210, "size_human": "9.2 GB"},
      ...
    ]
  }
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from .crawler import RepoFingerprint
from .models import ModelEntry

log = logging.getLogger(__name__)

SCHEMA_VERSION = "1.1"


def _human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} PB"


def write_fingerprint(
    repo_fp: RepoFingerprint,
    model: ModelEntry,
    output_root: Path,
) -> Path:
    """Write fingerprint.json and fingerprint.md for one repo. Returns the json path."""
    repo_dir = output_root / model.output_dir_name
    repo_dir.mkdir(parents=True, exist_ok=True)

    file_list = [
        {
            "filename": f.filename,
            "sha256": f.sha256,
            "size_bytes": f.size_bytes,
            "size_human": _human_bytes(f.size_bytes),
        }
        for f in sorted(repo_fp.files, key=lambda x: x.filename)
    ]

    fp_data = {
        "schema_version": SCHEMA_VERSION,
        # Identity
        "hf_repo": repo_fp.hf_repo,
        "hf_url": f"https://huggingface.co/{repo_fp.hf_repo}",
        "hf_commit_url": f"https://huggingface.co/{repo_fp.hf_repo}/tree/{repo_fp.commit_sha}",
        # Classification
        "family": model.family,
        "tier": model.tier,
        "importance": model.importance,
        "licence": model.licence,
        "requires_auth": model.requires_auth,
        "notes": model.notes,
        "parent_model": model.parent_model,
        "method": model.method,
        # Model metadata (for selection / comparison)
        "params_b": model.params_b,
        "arch": model.arch,
        "merged": model.merged,
        "hf_downloads": model.hf_downloads,
        "hf_likes": model.hf_likes,
        "registry_date": model.registry_date,
        # Benchmark scores (Open LLM Leaderboard 2)
        "benchmarks": {
            "lb_score":    model.lb_score,
            "lb_ifeval":   model.lb_ifeval,
            "lb_bbh":      model.lb_bbh,
            "lb_math":     model.lb_math,
            "lb_gpqa":     model.lb_gpqa,
            "lb_musr":     model.lb_musr,
            "lb_mmlu_pro": model.lb_mmlu_pro,
        } if model.lb_score > 0 else {},
        # Fingerprint snapshot
        "commit_sha": repo_fp.commit_sha,
        "crawled_at": repo_fp.crawled_at,
        "file_count": len(file_list),
        "total_size_bytes": repo_fp.total_size_bytes,
        "total_size_human": _human_bytes(repo_fp.total_size_bytes),
        "files": file_list,
    }

    fp_path = repo_dir / "fingerprint.json"
    _atomic_write(fp_path, json.dumps(fp_data, indent=2))
    _atomic_write(repo_dir / "fingerprint.md", _render_markdown(fp_data, model))

    return fp_path


def append_global_index(index_path: Path, repo_fp: RepoFingerprint, model: ModelEntry) -> None:
    """Upsert a compact one-line record into the global index.jsonl.

    Idempotent: if an entry for this hf_repo already exists it is replaced
    in-place (via a full rewrite of the file) so re-runs don't produce
    duplicate lines.
    """
    index_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "hf_repo": repo_fp.hf_repo,
        "family": model.family,
        "tier": model.tier,
        "importance": model.importance,
        "commit_sha": repo_fp.commit_sha,
        "crawled_at": repo_fp.crawled_at,
        "file_count": len(repo_fp.files),
        "total_size_bytes": repo_fp.total_size_bytes,
        "total_size_human": _human_bytes(repo_fp.total_size_bytes),
    }

    # Load existing lines, replace matching repo, append if new
    existing: list[dict] = []
    if index_path.exists():
        for line in index_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("hf_repo") != repo_fp.hf_repo:
                    existing.append(entry)
            except json.JSONDecodeError:
                pass  # skip malformed lines silently
    existing.append(record)

    # Write atomically so a concurrent read never sees a truncated file
    tmp = index_path.with_suffix(".jsonl.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for entry in existing:
            f.write(json.dumps(entry) + "\n")
    tmp.replace(index_path)


def load_fingerprint(repo_dir: Path) -> Optional[dict]:
    fp_path = repo_dir / "fingerprint.json"
    if not fp_path.exists():
        return None
    return json.loads(fp_path.read_text())


def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _render_markdown(fp: dict, model: ModelEntry) -> str:
    tier_labels = {
        "A": "Tier A — Major flagship model",
        "B": "Tier B — Code-specialist model",
        "C": "Tier C — Quantized GGUF",
        "D": "Tier D — Uncensored / abliterated variant",
    }
    file_rows = "\n".join(
        f"| `{f['filename']}` | `{f['sha256']}` | {f['size_human']} |"
        for f in fp.get("files", [])
    )
    parent_line = (
        f"| Parent model | [{model.parent_model}](https://huggingface.co/{model.parent_model}) |\n"
        if model.parent_model else ""
    )
    method_line = f"| Method | {model.method} |\n" if model.method else ""
    notes_section = f"\n## Notes\n\n{fp['notes']}\n" if fp.get("notes") else ""

    return f"""# {fp['hf_repo']} — Fingerprint

## Identity

| Field | Value |
|-------|-------|
| HuggingFace repo | [{fp['hf_repo']}]({fp['hf_url']}) |
| Pinned commit | [`{fp['commit_sha'][:12]}…`]({fp['hf_commit_url']}) |
| Family | {fp['family']} |
| Tier | {tier_labels.get(fp['tier'], fp['tier'])} |
| Importance | {fp['importance']} |
| Licence | {fp['licence']} |
| Token-gated | {'Yes' if fp['requires_auth'] else 'No'} |
{parent_line}{method_line}
## Snapshot

| Field | Value |
|-------|-------|
| Crawled at | {fp['crawled_at']} |
| Commit | `{fp['commit_sha'][:16]}…` |
| File count | {fp['file_count']} |
| Total size | {fp['total_size_human']} |
{notes_section}
## File Hashes

| Filename | SHA-256 | Size |
|----------|---------|------|
{file_rows}

## How to verify

```bash
# Verify a single file:
echo "<sha256>  <filename>" | sha256sum --check

# Verify all files in a directory:
jq -r '.files[] | .sha256 + "  " + .filename' fingerprint.json | sha256sum --check
```
"""
