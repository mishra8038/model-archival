#!/usr/bin/env python3
"""
Collect cross-leaderboard fingerprints by joining HF Open LLM Leaderboard
snapshots with LMSYS Chatbot Arena snapshots (when available).

Reads:
  - Latest HF snapshot: leaderboard-snapshots/YYYY-MM-DD/snapshot.json
  - Optional LMSYS snapshot: leaderboard-snapshots/lmsys/YYYY-MM-DD/snapshot.json

Writes (under --output-dir):
  - cross-leaderboard/YYYY-MM-DD/cross-leaderboard.json  (full envelope + models)
  - cross-leaderboard/YYYY-MM-DD/cross-leaderboard.csv   (tabular, key columns)

Usage (from fingerprints/):
  uv run python scripts/collect_cross_leaderboard.py
  uv run python scripts/collect_cross_leaderboard.py --hf-snapshot leaderboard-snapshots/2026-03-13/snapshot.json
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


def _atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding=encoding)
    tmp.replace(path)


def _find_latest_snapshot(root: Path, subdir: str) -> Path | None:
    """Return path to snapshot.json in the most recent dated subdir under root/subdir."""
    base = root / subdir
    if not base.exists():
        return None
    dates = [d.name for d in base.iterdir() if d.is_dir()]
    if not dates:
        return None
    dates.sort(reverse=True)
    candidate = base / dates[0] / "snapshot.json"
    return candidate if candidate.exists() else None


def load_hf_snapshot(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("models", [])


def load_lmsys_snapshot(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("models", [])


def normalise_hf_repo_from_arena(arena_model: dict) -> str | None:
    """Infer HuggingFace repo from Arena model_id or hf_repo. Returns None if not org/repo style."""
    hf = arena_model.get("hf_repo")
    if hf and "/" in str(hf):
        return str(hf).strip()
    mid = arena_model.get("model_id") or arena_model.get("modelId") or ""
    if "/" in str(mid):
        return str(mid).strip()
    return None


def join_snapshots(hf_models: list[dict], lmsys_models: list[dict] | None) -> list[dict]:
    """Merge HF leaderboard records with LMSYS Arena data keyed by hf_repo."""
    by_repo: dict[str, dict] = {}
    for r in hf_models:
        repo = r.get("hf_repo") or ""
        if not repo:
            continue
        row = dict(r)
        row["arena_elo"] = None
        row["arena_rank"] = None
        row["arena_games"] = None
        row["arena_win_rate"] = None
        row["arena_display_name"] = None
        by_repo[repo] = row

    if lmsys_models:
        for m in lmsys_models:
            repo = normalise_hf_repo_from_arena(m)
            if not repo:
                continue
            if repo in by_repo:
                by_repo[repo]["arena_elo"] = m.get("elo")
                by_repo[repo]["arena_rank"] = m.get("rank")
                by_repo[repo]["arena_games"] = m.get("games")
                by_repo[repo]["arena_win_rate"] = m.get("win_rate")
                by_repo[repo]["arena_display_name"] = m.get("display_name")
            else:
                by_repo[repo] = {
                    "hf_repo": repo,
                    "lb_score": None,
                    "lb_ifeval": None,
                    "lb_bbh": None,
                    "lb_math": None,
                    "lb_gpqa": None,
                    "lb_musr": None,
                    "lb_mmlu_pro": None,
                    "params_b": None,
                    "arch": None,
                    "licence": None,
                    "hf_downloads": None,
                    "hf_likes": None,
                    "hf_gated": None,
                    "arena_elo": m.get("elo"),
                    "arena_rank": m.get("rank"),
                    "arena_games": m.get("games"),
                    "arena_win_rate": m.get("win_rate"),
                    "arena_display_name": m.get("display_name"),
                }

    out = list(by_repo.values())
    out.sort(
        key=lambda r: (
            -(r.get("lb_score") or -999),
            -(r.get("arena_elo") or -999),
            -(r.get("hf_downloads") or 0),
        )
    )
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Join HF Open LLM Leaderboard + LMSYS Arena snapshots into cross-leaderboard fingerprints."
    )
    root = Path(__file__).resolve().parents[1]
    ap.add_argument(
        "--output-dir",
        "-o",
        default=str(root),
        help="Root output directory (default: fingerprints/)",
    )
    ap.add_argument(
        "--hf-snapshot",
        help="Path to HF snapshot.json (default: latest under leaderboard-snapshots/)",
    )
    ap.add_argument(
        "--lmsys-snapshot",
        help="Path to LMSYS snapshot.json (default: latest under leaderboard-snapshots/lmsys/)",
    )
    args = ap.parse_args()

    out_root = Path(args.output_dir).resolve()
    hf_path = Path(args.hf_snapshot).resolve() if args.hf_snapshot else _find_latest_snapshot(out_root, "leaderboard-snapshots")
    if not hf_path or not hf_path.exists():
        raise SystemExit("No HF snapshot found. Run snapshot_leaderboard.py first (from fingerprints/ with --output-dir .).")

    lmsys_path = None
    if args.lmsys_snapshot:
        lmsys_path = Path(args.lmsys_snapshot).resolve()
    else:
        lmsys_path = _find_latest_snapshot(out_root, "leaderboard-snapshots/lmsys")
    if lmsys_path and not lmsys_path.exists():
        lmsys_path = None

    print(f"HF snapshot:    {hf_path}")
    print(f"LMSYS snapshot: {lmsys_path or 'none'}")

    hf_models = load_hf_snapshot(hf_path)
    lmsys_models = load_lmsys_snapshot(lmsys_path) if lmsys_path and lmsys_path.exists() else None
    if lmsys_models is None:
        lmsys_models = []

    records = join_snapshots(hf_models, lmsys_models or None)
    snapshot_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = out_root / "cross-leaderboard" / snapshot_date
    out_dir.mkdir(parents=True, exist_ok=True)

    envelope = {
        "schema_version": "1.0",
        "snapshot_date": snapshot_date,
        "snapshot_ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": {
            "hf": str(hf_path),
            "lmsys": str(lmsys_path) if lmsys_path else None,
        },
        "total_models": len(records),
        "with_arena": sum(1 for r in records if r.get("arena_elo") is not None),
        "columns": {
            "hf_repo": "HuggingFace repo (org/name)",
            "lb_score": "HF Open LLM Leaderboard average (0–100)",
            "lb_ifeval": "IFEval", "lb_bbh": "BBH", "lb_math": "MATH Lvl 5",
            "lb_gpqa": "GPQA", "lb_musr": "MUSR", "lb_mmlu_pro": "MMLU-PRO",
            "params_b": "Parameters (billions)", "arch": "Architecture",
            "arena_elo": "LMSYS Chatbot Arena Elo",
            "arena_rank": "Arena rank", "arena_games": "Arena games",
            "arena_win_rate": "Arena win rate (%)",
        },
        "models": records,
    }

    json_path = out_dir / "cross-leaderboard.json"
    _atomic_write_text(json_path, json.dumps(envelope, indent=2, ensure_ascii=False))
    print(f"Wrote {json_path}  ({json_path.stat().st_size // 1024} KB)")

    csv_cols = [
        "hf_repo", "lb_score", "lb_ifeval", "lb_bbh", "lb_math",
        "lb_gpqa", "lb_musr", "lb_mmlu_pro",
        "params_b", "arch", "licence", "hf_downloads", "hf_likes", "hf_gated",
        "arena_elo", "arena_rank", "arena_games", "arena_win_rate", "arena_display_name",
    ]
    csv_path = out_dir / "cross-leaderboard.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=csv_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(records)
    print(f"Wrote {csv_path}  ({csv_path.stat().st_size // 1024} KB)")

    print(f"\nCross-leaderboard fingerprints: {len(records):,} models, {envelope['with_arena']:,} with Arena data")


if __name__ == "__main__":
    import sys
    try:
        main()
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.stderr.flush()
        raise
