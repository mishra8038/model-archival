"""
Fingerprint storage.

On-disk layout under the output root (e.g. /mnt/models/d1/model-checksums/):

  model-checksums/
  ├── index.jsonl                              # one line per repo (upserted on each run)
  ├── deepseek-ai__DeepSeek-V3/
  │   ├── fingerprint.json                     # full structured data
  │   ├── fingerprint.md                       # human-readable reference card
  │   └── sha256sums.txt                       # plain  sha256  filename  lines
  └── ...

fingerprint.json schema  (schema_version 2.0):
  {
    "schema_version":   "2.0",
    "hf_repo":          "deepseek-ai/DeepSeek-V3",
    "hf_url":           "https://huggingface.co/deepseek-ai/DeepSeek-V3",

    // Release identification — the primary key for mirror verification
    "release_tag":      "main",          // git tag or "main" if no formal release
    "is_head_fallback": true,            // true when no formal tag exists
    "commit_sha":       "e815299b...",   // commit at crawl time (informational)

    // Crawl metadata
    "crawled_at":       "2026-03-09T...",
    "file_count":       163,
    "total_size_bytes": 685123456789,
    "total_size_human": "638.1 GB",

    // Classification
    "family":           "deepseek",
    "tier":             "A",
    "importance":       "critical",
    "licence":          "MIT",
    "requires_auth":    false,

    // Per-file integrity records — the core verification payload
    "files": [
      {
        "filename":   "model-00001-of-00163.safetensors",
        "sha256":     "abc123...",           // SHA-256 of raw file bytes
        "size_bytes": 9876543210,
        "size_human": "9.2 GB",
        "source_url": "https://huggingface.co/deepseek-ai/DeepSeek-V3/resolve/<commit>/model-00001..."
      },
      ...
    ]
  }

sha256sums.txt format (standard sha256sum-compatible):
  abc123...  model-00001-of-00163.safetensors
  def456...  model-00002-of-00163.safetensors
  ...

  Verify with:  sha256sum --check sha256sums.txt
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from .crawler import ReleaseFingerprint
from .models import ModelEntry

log = logging.getLogger(__name__)

SCHEMA_VERSION = "2.0"


def _human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} PB"


def write_fingerprint(
    rel_fp: ReleaseFingerprint,
    model: ModelEntry,
    output_root: Path,
) -> Path:
    """
    Write fingerprint.json, fingerprint.md, and sha256sums.txt for one release.
    All writes are atomic (tmp → rename).  Returns the fingerprint.json path.
    """
    repo_dir = output_root / model.output_dir_name
    repo_dir.mkdir(parents=True, exist_ok=True)

    file_list = [
        {
            "filename":   f.filename,
            "sha256":     f.sha256,
            "size_bytes": f.size_bytes,
            "size_human": _human_bytes(f.size_bytes),
            "source_url": f.source_url,
        }
        for f in sorted(rel_fp.files, key=lambda x: x.filename)
    ]

    fp_data: dict = {
        "schema_version":   SCHEMA_VERSION,

        # Identity
        "hf_repo":          rel_fp.hf_repo,
        "hf_url":           f"https://huggingface.co/{rel_fp.hf_repo}",

        # Release — primary key for mirror verification
        "release_tag":      rel_fp.release_tag,
        "is_head_fallback": rel_fp.is_head_fallback,
        "commit_sha":       rel_fp.commit_sha,  # informational, not the primary key

        # Crawl metadata
        "crawled_at":       rel_fp.crawled_at,
        "file_count":       len(file_list),
        "total_size_bytes": rel_fp.total_size_bytes,
        "total_size_human": _human_bytes(rel_fp.total_size_bytes),

        # Classification
        "family":           model.family,
        "tier":             model.tier,
        "importance":       model.importance,
        "licence":          model.licence,
        "requires_auth":    model.requires_auth,
        "notes":            model.notes,
        "parent_model":     model.parent_model,
        "method":           model.method,

        # Model metadata
        "params_b":         model.params_b,
        "arch":             model.arch,
        "hf_downloads":     model.hf_downloads,
        "hf_likes":         model.hf_likes,

        # Benchmark scores (Open LLM Leaderboard 2) — omit block if no data
        **({"benchmarks": {
            "lb_score":    model.lb_score,
            "lb_ifeval":   model.lb_ifeval,
            "lb_bbh":      model.lb_bbh,
            "lb_math":     model.lb_math,
            "lb_gpqa":     model.lb_gpqa,
            "lb_musr":     model.lb_musr,
            "lb_mmlu_pro": model.lb_mmlu_pro,
        }} if model.lb_score > 0 else {}),

        # Core verification payload
        "files": file_list,
    }

    fp_path = repo_dir / "fingerprint.json"
    _atomic_write(fp_path, json.dumps(fp_data, indent=2))

    _atomic_write(repo_dir / "fingerprint.md", _render_markdown(fp_data))
    _atomic_write(repo_dir / "sha256sums.txt", _render_sha256sums(file_list))

    return fp_path


def append_global_index(
    index_path: Path,
    rel_fp: ReleaseFingerprint,
    model: ModelEntry,
) -> None:
    """
    Upsert a compact one-line record into the global index.jsonl.

    Idempotent: existing entry for this hf_repo is replaced, not duplicated.
    """
    index_path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "hf_repo":          rel_fp.hf_repo,
        "release_tag":      rel_fp.release_tag,
        "is_head_fallback": rel_fp.is_head_fallback,
        "family":           model.family,
        "tier":             model.tier,
        "importance":       model.importance,
        "crawled_at":       rel_fp.crawled_at,
        "file_count":       len(rel_fp.files),
        "total_size_bytes": rel_fp.total_size_bytes,
        "total_size_human": _human_bytes(rel_fp.total_size_bytes),
    }

    existing: list[dict] = []
    if index_path.exists():
        for line in index_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("hf_repo") != rel_fp.hf_repo:
                    existing.append(entry)
            except json.JSONDecodeError:
                pass
    existing.append(record)

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


# ── Internal ──────────────────────────────────────────────────────────────────

def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _render_sha256sums(file_list: list[dict]) -> str:
    """Standard sha256sum-compatible format:  <hash>  <filename>"""
    lines = [f"{f['sha256']}  {f['filename']}" for f in file_list]
    return "\n".join(lines) + "\n"


def _render_markdown(fp: dict) -> str:
    tag        = fp["release_tag"]
    is_fallback = fp.get("is_head_fallback", False)
    tag_note   = " *(no formal release — HEAD snapshot)*" if is_fallback else ""
    hf_url     = fp["hf_url"]
    commit     = fp["commit_sha"]

    file_rows = "\n".join(
        f"| `{f['filename']}` | `{f['sha256']}` | {f['size_human']} | [↓]({f['source_url']}) |"
        for f in fp.get("files", [])
    )

    benchmarks = fp.get("benchmarks", {})
    bench_section = ""
    if benchmarks:
        bench_section = f"""
## Benchmark Scores (Open LLM Leaderboard 2)

| Metric | Score |
|--------|-------|
| Average | {benchmarks.get('lb_score', '—')} |
| IFEval | {benchmarks.get('lb_ifeval', '—')} |
| BBH | {benchmarks.get('lb_bbh', '—')} |
| MATH | {benchmarks.get('lb_math', '—')} |
| GPQA | {benchmarks.get('lb_gpqa', '—')} |
| MuSR | {benchmarks.get('lb_musr', '—')} |
| MMLU-Pro | {benchmarks.get('lb_mmlu_pro', '—')} |
"""

    parent_line = ""
    if fp.get("parent_model"):
        parent_line = f"| Parent model | [{fp['parent_model']}](https://huggingface.co/{fp['parent_model']}) |\n"
    method_line = f"| Method | {fp['method']} |\n" if fp.get("method") else ""
    notes_section = f"\n## Notes\n\n{fp['notes']}\n" if fp.get("notes") else ""

    return f"""# {fp['hf_repo']} — Integrity Fingerprint

> **Purpose:** Verify a copy of this model obtained from any source (mirror,
> archive, torrent) against the hashes recorded here at crawl time.

## Release

| Field | Value |
|-------|-------|
| HuggingFace repo | [{fp['hf_repo']}]({hf_url}) |
| Release tag | `{tag}`{tag_note} |
| Commit at crawl | `{commit[:16]}…` |
| Crawled at | {fp['crawled_at']} |
| File count | {fp['file_count']} |
| Total size | {fp['total_size_human']} |
| Family | {fp['family']} |
| Tier | {fp['tier']} |
| Licence | {fp['licence']} |
| Token-gated | {'Yes' if fp['requires_auth'] else 'No'} |
{parent_line}{method_line}
{bench_section}{notes_section}
## File Hashes

| Filename | SHA-256 | Size | URL |
|----------|---------|------|-----|
{file_rows}

## How to Verify

```bash
# Verify a single downloaded file:
echo "<sha256>  <filename>" | sha256sum --check

# Verify all files at once using the companion sha256sums.txt:
sha256sum --check sha256sums.txt

# Or using jq directly from fingerprint.json:
jq -r '.files[] | .sha256 + "  " + .filename' fingerprint.json | sha256sum --check
```
"""
