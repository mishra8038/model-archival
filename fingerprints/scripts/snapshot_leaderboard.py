"""
snapshot_leaderboard.py — Archive a point-in-time snapshot of the Open LLM
Leaderboard 2 dataset plus live HuggingFace model metadata.

Output (written to --output-dir):
  leaderboard-snapshots/
    YYYY-MM-DD/
      snapshot.json          Full machine-readable dump (all models + metadata)
      leaderboard.csv        Tabular view sorted by lb_score desc
      README.md              Human-readable summary with methodology note

Usage:
  uv run python scripts/snapshot_leaderboard.py
  uv run python scripts/snapshot_leaderboard.py --output-dir /mnt/models/d1/model-checksums
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write *content* to *path* via a sibling .tmp then atomic rename."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding=encoding)
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------
try:
    import pyarrow.parquet as pq
    import requests
    import yaml
    from huggingface_hub import HfApi
except ImportError as e:
    sys.exit(f"Missing dependency: {e}\nRun: uv sync")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
LEADERBOARD_DATASET = "open-llm-leaderboard/contents"
LEADERBOARD_PARQUET = "data/train-00000-of-00001.parquet"

SCORE_COLS = [
    ("Average ⬆️",        "lb_score"),
    ("IFEval",            "lb_ifeval"),
    ("BBH",               "lb_bbh"),
    ("MATH Lvl 5",        "lb_math"),
    ("GPQA",              "lb_gpqa"),
    ("MUSR",              "lb_musr"),
    ("MMLU-PRO",          "lb_mmlu_pro"),
]

HF_META_COLS = [
    "Type", "Architecture", "Weight type", "Precision",
    "Hub License", "#Params (B)", "Hub ❤️", "Generation",
    "Flagged", "MoE", "Merged", "Chat Template",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _round(v, n=4):
    try:
        return round(float(v), n)
    except (TypeError, ValueError):
        return None


def _safe(v):
    """Convert to a JSON-safe primitive."""
    if v is None:
        return None
    if isinstance(v, float) and (v != v):  # NaN
        return None
    try:
        import numpy as np  # noqa: F401
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return None if (v != v) else float(v)
        if isinstance(v, (np.bool_,)):
            return bool(v)
    except ImportError:
        pass
    return v


def fetch_leaderboard(cache_dir: Path) -> list[dict]:
    """Download (or use cache) and parse the Open LLM Leaderboard 2 Parquet."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    # hf_hub_download mirrors the remote path under local_dir
    parquet_path = cache_dir / LEADERBOARD_PARQUET

    if not parquet_path.exists():
        print("Downloading leaderboard Parquet …")
        from huggingface_hub import hf_hub_download
        hf_hub_download(
            repo_id=LEADERBOARD_DATASET,
            filename=LEADERBOARD_PARQUET,
            repo_type="dataset",
            local_dir=str(cache_dir),
        )

    print(f"Reading {parquet_path} …")
    table = pq.read_table(str(parquet_path))
    df = table.to_pydict()
    n = len(next(iter(df.values())))

    rows = []
    for i in range(n):
        row = {k: _safe(v[i]) for k, v in df.items()}
        rows.append(row)

    print(f"  {len(rows):,} leaderboard entries")
    return rows


def fetch_hf_metadata(repos: list[str], token: str | None) -> dict[str, dict]:
    """Fetch live HF metadata for each repo: downloads, likes, gated, pipeline_tag."""
    api = HfApi(token=token)
    meta: dict[str, dict] = {}

    print(f"Fetching live HF metadata for {len(repos):,} repos …")
    done = 0
    for repo in repos:
        try:
            info = api.repo_info(repo_id=repo, repo_type="model")
            meta[repo] = {
                "hf_downloads":   getattr(info, "downloads", 0) or 0,
                "hf_likes":       getattr(info, "likes", 0) or 0,
                "hf_gated":       bool(getattr(info, "gated", False)),
                "pipeline_tag":   getattr(info, "pipeline_tag", None),
                "last_modified":  str(getattr(info, "lastModified", "") or ""),
                "card_data":      None,  # skip — too large
            }
        except Exception as e:
            meta[repo] = {"error": str(e)[:120]}
        done += 1
        if done % 100 == 0:
            print(f"  {done}/{len(repos)} …", flush=True)

    print(f"  Done — {len(meta):,} entries fetched")
    return meta


def build_snapshot(lb_rows: list[dict], hf_meta: dict[str, dict]) -> list[dict]:
    """Merge leaderboard rows with live HF metadata into unified records."""
    records = []

    for row in lb_rows:
        # 'fullname' = clean 'org/repo'; 'eval_name' = run id (includes precision suffix)
        repo = row.get("fullname", "") or row.get("eval_name", "") or ""
        meta = hf_meta.get(repo, {})

        record: dict = {
            "hf_repo": repo,
            "eval_name": row.get("eval_name"),   # preserves the unique run id
            "model_sha": row.get("Model sha"),   # commit sha at eval time
            # ── Benchmark scores ───────────────────────────────────────────
            "lb_score":       _round(row.get("Average ⬆️")),
            "lb_ifeval":      _round(row.get("IFEval")),
            "lb_bbh":         _round(row.get("BBH")),
            "lb_math":        _round(row.get("MATH Lvl 5")),
            "lb_gpqa":        _round(row.get("GPQA")),
            "lb_musr":        _round(row.get("MUSR")),
            "lb_mmlu_pro":    _round(row.get("MMLU-PRO")),
            # ── Raw (unnormalized) benchmark scores ────────────────────────
            "lb_ifeval_raw":  _round(row.get("IFEval Raw")),
            "lb_bbh_raw":     _round(row.get("BBH Raw")),
            "lb_math_raw":    _round(row.get("MATH Lvl 5 Raw")),
            "lb_gpqa_raw":    _round(row.get("GPQA Raw")),
            "lb_musr_raw":    _round(row.get("MUSR Raw")),
            "lb_mmlu_pro_raw":_round(row.get("MMLU-PRO Raw")),
            # ── Model metadata from leaderboard ───────────────────────────
            "type":           row.get("Type"),
            "arch":           row.get("Architecture"),
            "weight_type":    row.get("Weight type"),
            "precision":      row.get("Precision"),
            "licence":        row.get("Hub License"),
            "params_b":       _round(row.get("#Params (B)"), 2),
            "hf_likes_lb":    _round(row.get("Hub ❤️"), 0),
            "flagged":        row.get("Flagged"),
            "available_on_hub": row.get("Available on the hub"),
            "is_moe":         row.get("MoE"),
            "is_merged":      row.get("Merged"),
            "chat_template":  row.get("Chat Template"),
            "co2_cost_kg":    _round(row.get("CO₂ cost (kg)"), 4),
            # ── Live HF metadata (populated when --no-hf-meta not set) ───
            "hf_downloads":   meta.get("hf_downloads", 0),
            "hf_likes":       meta.get("hf_likes", 0),
            "hf_gated":       meta.get("hf_gated", False),
            "pipeline_tag":   meta.get("pipeline_tag"),
            "last_modified":  meta.get("last_modified"),
            "hf_fetch_error": meta.get("error"),
        }
        records.append(record)

    # Sort by lb_score desc (None last), then downloads desc
    records.sort(key=lambda r: (-(r["lb_score"] or -999), -(r["hf_downloads"] or 0)))
    return records


def write_outputs(records: list[dict], out_dir: Path, snapshot_ts: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── snapshot.json ──────────────────────────────────────────────────────
    envelope = {
        "schema_version":  "1.0",
        "snapshot_date":   snapshot_ts[:10],
        "snapshot_ts":     snapshot_ts,
        "source_dataset":  f"https://huggingface.co/datasets/{LEADERBOARD_DATASET}",
        "total_models":    len(records),
        "description": (
            "Point-in-time archive of the Open LLM Leaderboard 2 "
            "(open-llm-leaderboard/contents) merged with live HuggingFace model "
            "metadata (downloads, likes, gated status). "
            "Scores are as published on the leaderboard at snapshot time."
        ),
        "columns": {
            "hf_repo":       "HuggingFace repo (org/name) — clean identifier",
            "eval_name":     "Leaderboard run id (may include precision suffix)",
            "model_sha":     "Git commit SHA at time of leaderboard evaluation",
            "lb_score":      "Leaderboard average score (0–100)",
            "lb_ifeval":     "IFEval benchmark (normalised)",
            "lb_bbh":        "BBH benchmark (normalised)",
            "lb_math":       "MATH Level 5 (normalised)",
            "lb_gpqa":       "GPQA benchmark (normalised)",
            "lb_musr":       "MUSR benchmark (normalised)",
            "lb_mmlu_pro":   "MMLU-PRO (normalised)",
            "lb_*_raw":      "Unnormalised (0–1) benchmark score",
            "co2_cost_kg":   "Estimated CO₂ cost of the evaluation run (kg)",
            "hf_downloads":  "HF download count at snapshot time",
            "hf_likes":      "HF likes at snapshot time",
            "hf_gated":      "True if HF token + licence acceptance required",
        },
        "models": records,
    }
    json_path = out_dir / "snapshot.json"
    _atomic_write_text(json_path, json.dumps(envelope, indent=2, ensure_ascii=False))
    print(f"  Wrote {json_path}  ({json_path.stat().st_size // 1024} KB)")

    # ── leaderboard.csv ────────────────────────────────────────────────────
    csv_cols = [
        "hf_repo", "lb_score", "lb_ifeval", "lb_bbh", "lb_math",
        "lb_gpqa", "lb_musr", "lb_mmlu_pro",
        "params_b", "arch", "type", "precision", "is_moe", "is_merged",
        "licence", "hf_gated", "hf_downloads", "hf_likes", "last_modified",
    ]
    import io
    csv_path = out_dir / "leaderboard.csv"
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=csv_cols, extrasaction="ignore")
    w.writeheader()
    for r in records:
        w.writerow(r)
    _atomic_write_text(csv_path, buf.getvalue())
    print(f"  Wrote {csv_path}  ({csv_path.stat().st_size // 1024} KB)")

    # ── README.md ──────────────────────────────────────────────────────────
    top10 = [r for r in records if r.get("lb_score")][:10]
    top10_md = "\n".join(
        f"| {i+1} | `{r['hf_repo']}` | {r['lb_score']:.2f} | "
        f"{r.get('params_b') or '?'}B | {r.get('hf_downloads', 0):,} |"
        for i, r in enumerate(top10)
    )
    top_by_dl = sorted(
        [r for r in records if (r.get("hf_downloads") or 0) > 0],
        key=lambda r: -(r.get("hf_downloads") or 0),
    )[:10]
    top_dl_md = "\n".join(
        f"| {i+1} | `{r['hf_repo']}` | {r.get('hf_downloads', 0):,} | "
        f"{r['lb_score']:.2f} |"
        for i, r in enumerate(top_by_dl)
    )

    readme = f"""# Open LLM Leaderboard Snapshot — {snapshot_ts[:10]}

## Snapshot metadata

| Field | Value |
|---|---|
| **Snapshot date** | `{snapshot_ts[:10]}` |
| **Snapshot timestamp (UTC)** | `{snapshot_ts}` |
| **Source dataset** | [`open-llm-leaderboard/contents`](https://huggingface.co/datasets/open-llm-leaderboard/contents) |
| **Total models** | {len(records):,} |
| **Files** | `snapshot.json` (full data), `leaderboard.csv` (tabular) |

## Purpose

This directory contains a frozen point-in-time snapshot of the
[Open LLM Leaderboard 2](https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard)
benchmark results, merged with live HuggingFace metadata (downloads, likes, gated status)
fetched on the same date.

Models are routinely removed from the leaderboard (authors delete repos, HF delists
flagged entries). This snapshot preserves the ranking state as it existed on
`{snapshot_ts[:10]}` so future model selection and integrity verification can reference it.

## Benchmarks

| Benchmark | Description |
|---|---|
| **lb_score** | Leaderboard average (0–100, higher is better) |
| **IFEval** | Instruction-following evaluation |
| **BBH** | Big-Bench Hard — complex reasoning |
| **MATH Lvl 5** | Hardest MATH competition problems |
| **GPQA** | Graduate-level science Q&A |
| **MUSR** | Multi-step soft reasoning |
| **MMLU-PRO** | Massive Multitask Language Understanding (Pro) |

## Top 10 by leaderboard score

| Rank | Model | Score | Params | Downloads |
|---|---|---|---|---|
{top10_md}

## Top 10 by HF downloads (with leaderboard entry)

| Rank | Model | Downloads | Score |
|---|---|---|---|
{top_dl_md}

## Files in this directory

```
snapshot.json    — Full JSON dump: all {len(records):,} models with every field
leaderboard.csv  — CSV: key columns, sorted by lb_score desc
README.md        — This file
```

## How to use

```python
import json
data = json.loads(open("snapshot.json").read())
models = data["models"]

# Top models by score
top = sorted(models, key=lambda m: -(m["lb_score"] or 0))[:20]

# Find a specific model
deepseek = next(m for m in models if m["hf_repo"] == "deepseek-ai/DeepSeek-R1")
```
"""
    readme_path = out_dir / "README.md"
    _atomic_write_text(readme_path, readme)
    print(f"  Wrote {readme_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Archive an Open LLM Leaderboard snapshot")
    parser.add_argument(
        "--output-dir", "-o",
        default="/mnt/models/d1/model-checksums",
        help="Root output directory (a dated subdirectory is created inside)",
    )
    parser.add_argument(
        "--no-hf-meta",
        action="store_true",
        help="Skip live HF metadata fetch (faster, leaderboard data only)",
    )
    parser.add_argument(
        "--cache-dir",
        default=str(Path.home() / ".cache" / "model-archival" / "leaderboard"),
        help="Directory to cache the downloaded Parquet file",
    )
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        hf_token_file = Path.home() / ".hf_token"
        if hf_token_file.exists():
            token = hf_token_file.read_text().strip() or None

    snapshot_ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    snapshot_date = snapshot_ts[:10]

    out_dir = Path(args.output_dir) / "leaderboard-snapshots" / snapshot_date

    print("=" * 70)
    print(f"Open LLM Leaderboard Snapshot — {snapshot_ts}")
    print(f"Output: {out_dir}")
    print("=" * 70)

    # 1. Fetch leaderboard Parquet
    lb_rows = fetch_leaderboard(Path(args.cache_dir))

    # 2. Optionally fetch live HF metadata
    if args.no_hf_meta:
        hf_meta: dict = {}
        print("Skipping live HF metadata (--no-hf-meta)")
    else:
        repos = [
            row.get(next(
                (c for c in row if "model" in c.lower() and "name" in c.lower()),
                list(row.keys())[0]
            ), "")
            for row in lb_rows
        ]
        repos = [r for r in repos if r]
        hf_meta = fetch_hf_metadata(repos, token)

    # 3. Merge and sort
    print("Merging leaderboard + HF metadata …")
    records = build_snapshot(lb_rows, hf_meta)

    # 4. Write outputs
    print(f"Writing outputs to {out_dir} …")
    write_outputs(records, out_dir, snapshot_ts)

    # 5. Summary
    scored = [r for r in records if r.get("lb_score")]
    gated  = [r for r in records if r.get("hf_gated")]
    print()
    print("=" * 70)
    print(f"Snapshot complete.")
    print(f"  Total models  : {len(records):,}")
    print(f"  With LB score : {len(scored):,}")
    print(f"  Gated (auth)  : {len(gated):,}")
    print(f"  Saved to      : {out_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
