#!/usr/bin/env python3
"""Build config/final_registry.yaml from run_state pending+failed+in_progress, merged with registries.

- Drops models whose run_state ``total_bytes`` exceeds ``--max-bytes-gib`` (binary GiB, default 60).
- Maps known-dead HF ids to replacements (404 / renamed).
- Drops failed rows with no replacement and no resolvable size that are known removed from HF.
- Drive policy: default ``drive: d5``; up to ``--max-d1-exceptions`` models (default 3) that are
  ``pending``/``in_progress`` and tied to D1 (merged or run_state ``drive``) keep ``drive: d1``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

# (failed id -> replacement id) for 404 / wrong-id rows still present in run_state
REPLACEMENTS: dict[str, str] = {
    "Salesforce/CoDA-1.7B-Base": "Salesforce/CoDA-v0-Base",
    "Salesforce/CoDA-1.7B-Instruct": "Salesforce/CoDA-v0-Instruct",
    "Skywork/Skywork-Reward-Llama-3.1-70B": "Skywork/Skywork-Reward-Llama-3.1-8B-v0.2",
    # Renamed / alternate publisher rows (registry.yaml documents these)
    "bartowski/gemma-3-27b-it-GGUF": "bartowski/google_gemma-3-27b-it-GGUF",
    # Pending huihui *-GGUF ids → tensorblock GGUF mirrors already in main registry
    "huihui-ai/DeepSeek-R1-Distill-Llama-70B-abliterated-GGUF": (
        "tensorblock/DeepSeek-R1-Distill-Llama-70B-abliterated-GGUF"
    ),
    "huihui-ai/DeepSeek-R1-Distill-Qwen-32B-abliterated-GGUF": (
        "tensorblock/DeepSeek-R1-Distill-Qwen-32B-abliterated-GGUF"
    ),
    "huihui-ai/Llama-3.3-70B-Instruct-abliterated-GGUF": "tensorblock/Llama-3.3-70B-Instruct-abliterated-GGUF",
    "huihui-ai/Mistral-Small-24B-abliterated-GGUF": (
        "tensorblock/Mistral-Small-24B-Instruct-2501-abliterated-GGUF"
    ),
}

# Do not carry these failed ids forward (no maintained HF equivalent in scope)
DROP_FAILED_IDS: frozenset[str] = frozenset(
    {
        "mistralai/Leanstral-120B-A6B",
        "mosaicml/mpt-7b",
        "mosaicml/mpt-7b-instruct",
        "mosaicml/mpt-30b",
        "mosaicml/mpt-30b-instruct",
    }
)

# Pending / failed rows with missing total_bytes but known to exceed policy cap (~67 GiB class)
FORCE_EXCLUDE_IDS: frozenset[str] = frozenset(
    {
        "Qwen/Qwen3.5-35B-A3B",
        "Qwen/Qwen3.5-35B-A3B-Base",
    }
)

# No HF replacement; legacy notes 404 — do not queue
DROP_RAW_IDS: frozenset[str] = frozenset(
    {
        "NovaSky-Berkeley/Sky-T1-32B-Preview",
    }
)

# Final slice drive policy: default **d5** for new destinations. At most
# ``FINAL_REGISTRY_MAX_D1_EXCEPTIONS`` rows may stay on **d1**: models whose
# run_state status is ``pending`` or ``in_progress`` and whose work is tied to
# D1 (``run_state["drive"] == "d1"`` or merged registry ``drive: d1`` before policy).
FINAL_REGISTRY_MAX_D1_EXCEPTIONS = 3

# Minimal rows when id is missing from merged YAML (drive/tier from run_state + policy)
FALLBACK_REGISTRY_ROWS: dict[str, dict] = {
    "bartowski/Mistral-7B-Instruct-v0.3-GGUF": {
        "id": "bartowski/Mistral-7B-Instruct-v0.3-GGUF",
        "hf_repo": "bartowski/Mistral-7B-Instruct-v0.3-GGUF",
        "tier": "C",
        "drive": "d3",
        "priority": 2,
        "licence": "Apache-2.0",
        "requires_auth": False,
        "commit_sha": None,
        "quant_levels": ["Q4_K_M"],
        "notes": "Bartowski GGUF quant of Mistral-7B-Instruct-v0.3; not in main YAML — "
        "queued from final_registry builder.",
    },
    "tiiuae/Falcon3-10B-Instruct": {
        "id": "tiiuae/Falcon3-10B-Instruct",
        "hf_repo": "tiiuae/Falcon3-10B-Instruct",
        "tier": "B",
        "drive": "d1",
        "priority": 2,
        "licence": "Apache-2.0",
        "requires_auth": False,
        "commit_sha": None,
        "notes": "TII Falcon3 10B instruct; queued from final_registry (was network-failed).",
    },
    "upstage/solar-pro-preview-instruct": {
        "id": "upstage/solar-pro-preview-instruct",
        "hf_repo": "upstage/solar-pro-preview-instruct",
        "tier": "B",
        "drive": "d1",
        "priority": 2,
        "licence": "Apache-2.0",
        "requires_auth": False,
        "commit_sha": None,
        "notes": "Upstage Solar Pro preview instruct; queued from final_registry (was DNS-failed).",
    },
}


def _bytes_gib(n: int) -> float:
    return n / (1024**3)


def _state_row(models_state: dict, mid: str) -> dict:
    """Resolve run_state entry for ``mid``, including legacy keys before REPLACEMENTS."""
    r = models_state.get(mid)
    if isinstance(r, dict) and r:
        return r
    for old, new in REPLACEMENTS.items():
        if new == mid:
            r2 = models_state.get(old)
            if isinstance(r2, dict) and r2:
                return r2
    return {}


def _apply_final_registry_drive_policy(
    out_rows: list[dict],
    models_state: dict,
    *,
    max_d1: int = FINAL_REGISTRY_MAX_D1_EXCEPTIONS,
) -> None:
    """
    Set ``drive`` on each row: default d5; up to ``max_d1`` models that are
    pending/in_progress on d1 keep drive d1 (stable order by priority, id).
    """
    active = frozenset({"pending", "in_progress"})
    candidates: list[tuple[int, str, dict]] = []
    for entry in out_rows:
        mid = entry["id"]
        st = _state_row(models_state, mid)
        status = st.get("status", "")
        if status not in active:
            continue
        merged_was_d1 = entry.get("drive") == "d1"
        state_on_d1 = st.get("drive") == "d1"
        if not (merged_was_d1 or state_on_d1):
            continue
        pr = entry.get("priority", 99)
        if not isinstance(pr, int):
            pr = 99
        candidates.append((pr, mid, entry))
    candidates.sort(key=lambda t: (t[0], t[1]))
    keep_d1 = {t[1] for t in candidates[:max_d1]}
    for entry in out_rows:
        entry["drive"] = "d1" if entry["id"] in keep_d1 else "d5"


def merge_registry_rows(repo_root: Path) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for name in ("config/registry.yaml", "config/registry-specialists.yaml", "config/registry-legacy.yaml"):
        p = repo_root / name
        if not p.exists():
            continue
        doc = yaml.safe_load(p.read_text()) or {}
        for row in doc.get("models", []):
            merged[row["id"]] = dict(row)
    return merged


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", type=Path, required=True, help="Path to run_state.json")
    ap.add_argument("--out", type=Path, default=Path("config/final_registry.yaml"))
    ap.add_argument("--max-bytes-gib", type=float, default=60.0, help="Exclude if total_bytes > this many binary GiB")
    ap.add_argument(
        "--max-d1-exceptions",
        type=int,
        default=FINAL_REGISTRY_MAX_D1_EXCEPTIONS,
        metavar="N",
        help="Max models that may keep drive: d1 (pending/in_progress on D1 only); rest → d5",
    )
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    limit = int(args.max_bytes_gib * (1024**3))

    state = json.loads(Path(args.state).read_text())
    models_state: dict = state.get("models", {})

    raw_ids: set[str] = set()
    for mid, row in models_state.items():
        if not isinstance(row, dict):
            continue
        if row.get("status") in ("pending", "failed", "in_progress"):
            raw_ids.add(mid)

    mapped: set[str] = set()
    dropped_size: list[tuple[str, int]] = []
    dropped_no_carry: list[str] = []

    for mid in sorted(raw_ids):
        if mid in DROP_RAW_IDS:
            dropped_no_carry.append(mid)
            continue
        if mid in DROP_FAILED_IDS:
            dropped_no_carry.append(mid)
            continue
        if mid in FORCE_EXCLUDE_IDS:
            dropped_size.append((mid, -1))
            continue
        target = REPLACEMENTS.get(mid, mid)
        if target in FORCE_EXCLUDE_IDS:
            dropped_size.append((target, -1))
            continue
        tb = models_state.get(mid, {}).get("total_bytes")
        if isinstance(tb, int) and tb > limit:
            dropped_size.append((mid, tb))
            continue
        mapped.add(target)

    merged = merge_registry_rows(repo_root)
    missing: list[str] = []
    out_rows: list[dict] = []
    for mid in sorted(mapped):
        row = merged.get(mid) or FALLBACK_REGISTRY_ROWS.get(mid)
        if not row:
            missing.append(mid)
            continue
        entry = {k: v for k, v in row.items() if k != "legacy"}
        note = entry.get("notes") or ""
        tag = "[final_registry] pending+failed slice; max %.0f GiB HF sum from prior run_state" % args.max_bytes_gib
        entry["notes"] = f"{tag}. {note}".strip()
        out_rows.append(entry)

    _apply_final_registry_drive_policy(out_rows, models_state, max_d1=max(0, args.max_d1_exceptions))
    n_d1 = sum(1 for e in out_rows if e.get("drive") == "d1")
    print("drive policy: d1 retention =", n_d1, " remainder d5 =", len(out_rows) - n_d1)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        yaml.safe_dump({"models": out_rows}, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    print("run_state pending+failed raw ids:", len(raw_ids))
    print("dropped (known removed / no replacement):", len(dropped_no_carry), dropped_no_carry)
    print("dropped (total_bytes > %.0f GiB or force-exclude):" % args.max_bytes_gib, len(dropped_size))
    for mid, tb in dropped_size[:20]:
        if tb < 0:
            print(f"  {mid}  (policy force-exclude)")
        else:
            print(f"  {mid}  {_bytes_gib(tb):.1f} GiB")
    if len(dropped_size) > 20:
        print("  ...", len(dropped_size) - 20, "more")
    print("replacements applied:", {k: v for k, v in REPLACEMENTS.items() if k in raw_ids})
    if missing:
        print("WARNING — ids not in registry.yaml ∪ registry-specialists.yaml:", missing)
    print("final_registry models:", len(out_rows))
    print("wrote", args.out.resolve())


if __name__ == "__main__":
    main()
