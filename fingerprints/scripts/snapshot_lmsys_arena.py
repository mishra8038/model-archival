"""
snapshot_lmsys_arena.py — Archive a point-in-time snapshot of the LMSYS
Chatbot Arena leaderboard into the fingerprints folder.

This script is intentionally agnostic about the exact JSON source. You can:

  1. Point it at a JSON HTTP endpoint (e.g. an internal scraper or Apify actor)
     that returns a list of model entries.
  2. Or point it at a local JSON file you have exported from a scraper.

Each entry SHOULD contain at least the following keys (extra keys are preserved):
  - model_id        — arena identifier (e.g. "meta-llama/Llama-3.3-70B-Instruct")
  - display_name    — human-readable name
  - organization    — model owner / org (if available)
  - elo             — Elo rating
  - rank            — rank on the leaderboard (1 = best)
  - games           — number of arena games
  - win_rate        — win rate in [0, 1] or [0, 100]

We write an envelope `snapshot.json` under:

  fingerprints/leaderboard-snapshots/lmsys/YYYY-MM-DD/snapshot.json

with this structure:

  {
    "schema_version": "1.0",
    "snapshot_date": "YYYY-MM-DD",
    "snapshot_ts":   "YYYY-MM-DDTHH:MM:SSZ",
    "source":        "<URL-or-path-you-used>",
    "total_models":  <N>,
    "columns": {...},   # column documentation
    "models": [ {...}, ... ]  # one entry per arena model
  }

Usage examples:

  # From a JSON URL (e.g. your own scraper endpoint)
  uv run python fingerprints/scripts/snapshot_lmsys_arena.py \
    --source-url https://example.com/chatbot-arena-leaderboard.json

  # From a local JSON file
  uv run python fingerprints/scripts/snapshot_lmsys_arena.py \
    --source-file /path/to/arena-leaderboard.json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write *content* to *path* via a sibling .tmp then atomic rename."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding=encoding)
    tmp.replace(path)


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _try_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _normalise_win_rate(v: Any) -> Optional[float]:
    """Return win rate as a 0–100 float, if possible."""
    w = _try_float(v)
    if w is None:
        return None
    # Heuristic: values <= 1 are treated as 0–1 fraction
    if 0 <= w <= 1:
        return round(w * 100.0, 4)
    return round(w, 4)


def _guess_hf_repo(model_id: str) -> Optional[str]:
    """
    Try to infer a Hugging Face repo id from the arena model id.

    Many arena ids are already of the form "org/repo". If that pattern is not
    present, we leave this as None and keep only the arena identifier.
    """
    if "/" in model_id:
        return model_id
    return None


@dataclass
class ArenaModelRecord:
    """Normalised view of a single LMSYS Arena model entry."""

    model_id: str                   # Raw arena identifier
    display_name: str               # Human-readable name
    organization: Optional[str]     # Owning org, if known
    hf_repo: Optional[str]          # Best-effort HF repo guess
    elo: Optional[float]           # Elo rating
    rank: Optional[int]            # Rank (1 = best)
    games: Optional[int]           # Number of games played
    win_rate: Optional[float]      # Win rate in [0, 100]
    raw: Dict[str, Any]            # Full original JSON entry


def load_source(args: argparse.Namespace) -> List[Dict[str, Any]]:
    if args.source_file:
        path = Path(args.source_file)
        if not path.exists():
            raise SystemExit(f"source file not found: {path}")
        print(f"Reading arena JSON from file: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "models" in data:
            data = data["models"]
        if not isinstance(data, list):
            raise SystemExit("Expected a JSON list (or an object with 'models' list).")
        return data

    if args.source_url:
        try:
            import requests  # type: ignore
        except ImportError as e:
            raise SystemExit(f"Missing dependency: {e}\nRun: uv sync in fingerprints/") from e

        print(f"Fetching arena JSON from URL: {args.source_url}")
        resp = requests.get(args.source_url, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "models" in data:
            data = data["models"]
        if not isinstance(data, list):
            raise SystemExit("Expected a JSON list (or an object with 'models' list).")
        return data

    raise SystemExit("You must specify either --source-url or --source-file.")


def normalise_records(entries: List[Dict[str, Any]]) -> List[ArenaModelRecord]:
    records: List[ArenaModelRecord] = []

    for entry in entries:
        # Be tolerant to different key naming schemes.
        model_id = (
            entry.get("model_id")
            or entry.get("modelId")
            or entry.get("id")
            or entry.get("name")
        )
        if not model_id:
            # Skip entries without a stable identifier.
            continue

        display_name = (
            entry.get("display_name")
            or entry.get("displayName")
            or entry.get("name")
            or str(model_id)
        )

        organization = (
            entry.get("organization")
            or entry.get("org")
            or entry.get("provider")
        )

        elo = _try_float(
            entry.get("elo")
            or entry.get("elo_rating")
            or entry.get("rating")
        )

        rank_raw = (
            entry.get("rank")
            or entry.get("position")
        )
        try:
            rank = int(rank_raw) if rank_raw is not None else None
        except (TypeError, ValueError):
            rank = None

        games_raw = (
            entry.get("games")
            or entry.get("num_games")
            or entry.get("n_games")
        )
        try:
            games = int(games_raw) if games_raw is not None else None
        except (TypeError, ValueError):
            games = None

        win_rate = _normalise_win_rate(
            entry.get("win_rate")
            or entry.get("winRate")
            or entry.get("winrate")
        )

        hf_repo = _guess_hf_repo(str(model_id))

        records.append(
            ArenaModelRecord(
                model_id=str(model_id),
                display_name=str(display_name),
                organization=str(organization) if organization is not None else None,
                hf_repo=hf_repo,
                elo=elo,
                rank=rank,
                games=games,
                win_rate=win_rate,
                raw=entry,
            )
        )

    # Sort best-first by Elo (desc), then by games (desc).
    records.sort(
        key=lambda r: (-(r.elo or -9999.0), -(r.games or 0)),
    )
    return records


def write_snapshot(
    records: List[ArenaModelRecord],
    output_root: Path,
    source: str,
) -> Path:
    snapshot_date = _today_date()
    snapshot_ts = _now_utc_iso()

    out_dir = output_root / "leaderboard-snapshots" / "lmsys" / snapshot_date
    out_dir.mkdir(parents=True, exist_ok=True)

    # Envelope
    envelope = {
        "schema_version": "1.0",
        "snapshot_date": snapshot_date,
        "snapshot_ts": snapshot_ts,
        "source": source,
        "total_models": len(records),
        "columns": {
            "model_id": "Raw LMSYS arena model identifier.",
            "display_name": "Human-readable model name as shown on the leaderboard.",
            "organization": "Model owner / organization, when available.",
            "hf_repo": "Best-effort Hugging Face repo id (org/name) parsed from model_id.",
            "elo": "Elo rating as reported by the arena.",
            "rank": "Leaderboard rank (1 = best).",
            "games": "Number of games played in the arena.",
            "win_rate": "Win rate as a percentage in [0, 100].",
            "raw": "Original JSON leaderboard entry for this model.",
        },
        "models": [asdict(r) for r in records],
    }

    json_path = out_dir / "snapshot.json"
    _atomic_write_text(json_path, json.dumps(envelope, indent=2, ensure_ascii=False))
    print(f"Wrote {json_path}  ({json_path.stat().st_size // 1024} KB)")
    return json_path


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Snapshot the LMSYS Chatbot Arena leaderboard into fingerprints/ "
            "for future offline analysis."
        )
    )
    parser.add_argument(
        "--source-url",
        help="HTTP URL returning JSON list of arena models (or object with 'models' list).",
    )
    parser.add_argument(
        "--source-file",
        help="Local JSON file containing a list of arena models.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parents[1]),
        help="Root output directory (defaults to the fingerprints/ project root).",
    )

    args = parser.parse_args(argv)

    if not args.source_url and not args.source_file:
        parser.print_help()
        raise SystemExit(
            "\nError: you must provide either --source-url or --source-file."
        )

    output_root = Path(args.output_dir)
    print(f"Output root: {output_root}")

    entries = load_source(args)
    print(f"Loaded {len(entries)} raw entries")

    records = normalise_records(entries)
    print(f"Normalised to {len(records)} model records")

    source_desc = args.source_url or str(args.source_file)
    write_snapshot(records, output_root=output_root, source=source_desc)


if __name__ == "__main__":
    main()

