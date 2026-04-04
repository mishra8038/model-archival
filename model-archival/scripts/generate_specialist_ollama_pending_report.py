#!/usr/bin/env python3
"""Emit docs/SPECIALIST-HF-PENDING-OLLAMA.md from registries + failed-models-registry.

Enriches Ollama-oriented rows with approximate **download sizes** from
`registry.ollama.ai` image manifests (sum of layer + config sizes). Results are
cached under docs/data/ollama-registry-size-cache.json for offline regeneration.

  uv run python scripts/generate_specialist_ollama_pending_report.py
  uv run python scripts/generate_specialist_ollama_pending_report.py --offline
  uv run python scripts/generate_specialist_ollama_pending_report.py --refresh-sizes
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
import yaml

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / "config/registry-specialists.yaml"
MAIN_PATH = ROOT / "config/registry.yaml"
FAILED_PATH = ROOT / "config/failed-models-registry.yaml"
OUT_PATH = ROOT / "docs/SPECIALIST-HF-PENDING-OLLAMA.md"
CACHE_PATH = ROOT / "docs/data/ollama-registry-size-cache.json"

REGISTRY_MANIFEST_ACCEPT = "application/vnd.docker.distribution.manifest.v2+json"
REGISTRY_TMPL = "https://registry.ollama.ai/v2/library/{model}/manifests/{tag}"

OLLAMA_BRACKET = re.compile(r"\[ollama:([^\]]+)\]")
OLLAMA_TAG_LEGACY = re.compile(
    r"\[ollama:([A-Za-z0-9_.-]+):([A-Za-z0-9_.+-]+)\]",
)

QUANT_HINT = re.compile(
    r"(q\d+[_A-Z0-9]*|iq\d+[_A-Z0-9]*|fp8|fp16|bf16|f16|f32)",
    re.I,
)


def load_models(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text())
    return data.get("models") or []


def collect_failed_ids(doc: dict) -> set[str]:
    out: set[str] = set()
    for _cat, rows in (doc.get("categories") or {}).items():
        if not isinstance(rows, list):
            continue
        for r in rows:
            if isinstance(r, dict) and r.get("id"):
                out.add(r["id"])
    return out


def iter_failed_rows(doc: dict):
    for cat, rows in (doc.get("categories") or {}).items():
        if not isinstance(rows, list):
            continue
        for r in rows:
            if isinstance(r, dict) and r.get("id"):
                yield cat, r


def failure_lookup(failed_doc: dict) -> dict[str, tuple[str, dict]]:
    return {r["id"]: (cat, r) for cat, r in iter_failed_rows(failed_doc)}


def ollama_tags_from_notes(notes: str | None) -> list[str]:
    """Parse model:tag strings from [ollama:...] blocks (supports comma-separated tags)."""
    if not notes:
        return []
    seen: dict[str, None] = {}
    for m in OLLAMA_BRACKET.finditer(notes):
        inner = m.group(1).strip()
        for part in inner.split(","):
            part = part.strip()
            if ":" in part:
                seen[part.replace(" ", "")] = None
    for a, b in OLLAMA_TAG_LEGACY.findall(notes):
        seen[f"{a}:{b}"] = None
    return list(seen.keys())


def quant_from_tag(tag: str) -> str:
    m = QUANT_HINT.search(tag)
    return m.group(1).lower() if m else "—"


def human_bytes(n: float) -> str:
    for u in ("B", "KiB", "MiB", "GiB", "TiB"):
        if n < 1024.0 or u == "TiB":
            if u == "B":
                return f"{int(n)} B"
            return f"{n:.2f} {u}"
        n /= 1024.0
    return f"{n:.2f} TiB"


def manifest_total_bytes(data: dict[str, Any]) -> int:
    total = 0
    cfg = data.get("config")
    if isinstance(cfg, dict) and cfg.get("size") is not None:
        total += int(cfg["size"])
    for layer in data.get("layers") or []:
        if isinstance(layer, dict) and layer.get("size") is not None:
            total += int(layer["size"])
    return total


def registry_manifest_url(model: str, tag: str) -> str:
    m = quote(model.strip(), safe="-_.")
    t = quote(tag.strip(), safe="-_.+")
    return REGISTRY_TMPL.format(model=m, tag=t)


def load_size_cache() -> dict[str, Any]:
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text())
    except json.JSONDecodeError:
        return {}


def save_size_cache(cache: dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n")


def fetch_ollama_tag_size(
    client: httpx.Client,
    model: str,
    tag: str,
) -> tuple[int | None, str | None]:
    url = registry_manifest_url(model, tag)
    try:
        r = client.get(url, headers={"Accept": REGISTRY_MANIFEST_ACCEPT})
    except httpx.RequestError as e:
        return None, str(e)
    if r.status_code == 404:
        return None, "manifest unknown (check tag on ollama.com/library)"
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    try:
        data = r.json()
    except json.JSONDecodeError:
        return None, "invalid JSON"
    if not isinstance(data, dict):
        return None, "unexpected manifest shape"
    return manifest_total_bytes(data), None


def resolve_tag_sizes(
    tags: set[str],
    *,
    client: httpx.Client | None,
    cache: dict[str, Any],
    offline: bool,
    refresh: bool,
) -> dict[str, tuple[int | None, str | None]]:
    """Return descriptor -> (bytes, error_message)."""
    out: dict[str, tuple[int | None, str | None]] = {}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for desc in sorted(tags):
        if ":" not in desc:
            out[desc] = (None, "bad descriptor (expected model:tag)")
            continue
        model, tag = desc.split(":", 1)
        ent = cache.get(desc)
        if not refresh and isinstance(ent, dict):
            sb = ent.get("size_bytes")
            err = ent.get("error")
            if sb is not None:
                out[desc] = (int(sb), err)
                continue
            if offline and err:
                out[desc] = (None, err)
                continue
        if offline:
            out[desc] = (None, "offline (no cache)")
            continue
        assert client is not None
        nbytes, err = fetch_ollama_tag_size(client, model, tag)
        cache[desc] = {
            "size_bytes": nbytes,
            "error": err,
            "fetched_at_utc": now,
            "model": model,
            "tag": tag,
        }
        out[desc] = (nbytes, err)
    return out


def format_size_summary(
    tags: list[str],
    sizes: dict[str, tuple[int | None, str | None]],
) -> str:
    parts: list[str] = []
    for t in tags:
        nbytes, err = sizes.get(t, (None, None))
        if nbytes is not None:
            parts.append(f"`{t}` **~{human_bytes(float(nbytes))}**")
        elif err:
            parts.append(f"`{t}` _({err})_")
        else:
            parts.append(f"`{t}` _(—)_")
    return "; ".join(parts) if parts else "—"


def format_quant_summary(tags: list[str]) -> str:
    if not tags:
        return "—"
    return ", ".join(quant_from_tag(t) for t in tags)


def md_cell(s: str, max_len: int = 120) -> str:
    s = s.replace("|", "\\|").replace("\n", " ")
    if len(s) > max_len:
        s = s[: max_len - 3] + "..."
    return s


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--offline",
        action="store_true",
        help="Do not query registry.ollama.ai; use cache only.",
    )
    ap.add_argument(
        "--refresh-sizes",
        action="store_true",
        help="Refetch all Ollama tag sizes (ignore cached bytes).",
    )
    args = ap.parse_args()

    spec = {m["id"]: m for m in load_models(SPEC_PATH)}
    main_ids = {m["id"] for m in load_models(MAIN_PATH)}
    failed_doc = yaml.safe_load(FAILED_PATH.read_text())
    failed_ids = collect_failed_ids(failed_doc)
    flookup = failure_lookup(failed_doc)

    unified_ids = sorted(set(spec.keys()) | failed_ids, key=str.lower)

    # All [ollama:…] tags in specialist registry (for sizes).
    all_tags: set[str] = set()
    for m in spec.values():
        all_tags.update(ollama_tags_from_notes(m.get("notes")))

    cache = load_size_cache()
    client: httpx.Client | None = None
    if not args.offline:
        client = httpx.Client(timeout=60.0, follow_redirects=True)
    try:
        sizes = resolve_tag_sizes(
            all_tags,
            client=client,
            cache=cache,
            offline=args.offline,
            refresh=args.refresh_sizes,
        )
    finally:
        if client:
            client.close()

    if not args.offline:
        save_size_cache(cache)

    def row_sort_key(mid: str) -> tuple[int, str]:
        tags = ollama_tags_from_notes(spec[mid].get("notes")) if mid in spec else []
        best: int | None = None
        for t in tags:
            nbytes, _ = sizes.get(t, (None, None))
            if nbytes is not None:
                best = nbytes if best is None else min(best, nbytes)
        return (best if best is not None else 2**62, mid.lower())

    lines: list[str] = [
        "# Specialist models — HF trouble + Ollama-oriented pull list",
        "",
        "_Generated by `scripts/generate_specialist_ollama_pending_report.py`. "
        "Refresh after `uv run archiver failed-registry` and registry edits. "
        "Approximate **Ollama download sizes** come from summing `config` + `layers` sizes in the "
        "public **`registry.ollama.ai`** manifest for each `model:tag` (not the same as VRAM; use as a disk budget guide)._",
        "",
        "## How to read this table",
        "",
        "- **One row per HF `id`:** union of **`config/registry-specialists.yaml`** and every id in **`config/failed-models-registry.yaml`**.",
        "- **Specialist** / **Main reg** / **Failed reg:** whether the id appears in each source.",
        "- **HF failure:** populated when the id is in the failed-registry file (category + reason kind).",
        "- **Ollama columns** come from **`[ollama:…]`** in specialist `notes` only (no Ollama hints in main registry).",
        "- **Download size** ≈ on-disk size after `ollama pull` (manifest layer sum). **Quant** is inferred from the tag string.",
        "- **Cache:** `docs/data/ollama-registry-size-cache.json` — commit for reproducible docs without re-querying the registry.",
        "",
        "## Unified table (sorted by smallest known Ollama download, then id)",
        "",
        "| HF `id` | Specialist | Main reg | Failed reg | Tier | Drive | HF failure | Ollama tags | Quant | Approx Ollama download | `ollama pull` | Notes (trunc.) |",
        "|---------|------------|----------|------------|------|-------|------------|-------------|-------|------------------------|---------------|----------------|",
    ]

    n_spec = len(spec)
    n_failed_unique = len(failed_ids)
    n_union = len(unified_ids)

    for mid in sorted(unified_ids, key=row_sort_key):
        in_spec = mid in spec
        tags = ollama_tags_from_notes(spec[mid].get("notes")) if in_spec else []
        m = spec.get(mid, {})
        tier = m.get("tier", "")
        drive = m.get("drive", "")
        cat, frow = flookup.get(mid, ("", {}))
        if mid in failed_ids:
            if not tier:
                tier = str(frow.get("tier", "") or "")
            if not drive:
                drive = str(frow.get("registry_drive") or frow.get("drive") or "")
            reason = frow.get("reason_kind", "") or frow.get("failure_category", "")
            fail_cell = md_cell(f"{cat} / {reason}".strip(" /"), 80)
        else:
            fail_cell = "—"
        spec_cell = "yes" if in_spec else "no"
        main_cell = "yes" if mid in main_ids else "no"
        failed_cell = "yes" if mid in failed_ids else "no"
        tag_cell = ", ".join(f"`{t}`" for t in tags) if tags else "—"
        quant_cell = format_quant_summary(tags)
        size_cell = format_size_summary(tags, sizes)
        if tags:
            pull = ", ".join(f"`ollama pull {t}`" for t in tags)
        elif in_spec:
            pull = "_(see HF GGUF / Ollama library)_"
        else:
            pull = "—"
        notes_cell = (
            md_cell((m.get("notes") or "").replace("`", "'"), 90) if in_spec else "—"
        )
        lines.append(
            f"| `{mid}` | {spec_cell} | {main_cell} | {failed_cell} | {tier} | {drive} | {fail_cell} | "
            f"{tag_cell} | {quant_cell} | {size_cell} | {pull} | {notes_cell} |"
        )

    lines.extend(
        [
            "",
            "_Rows with **Failed reg** = no are specialist (or other) models not currently listed in "
            "`failed-models-registry.yaml`. Refresh that file with **`uv run archiver failed-registry`** "
            "on a host with current `run_state.json` so pending/in-progress VM trouble shows up here._",
            "",
        ]
    )

    OUT_PATH.write_text("\n".join(lines) + "\n")
    print(
        f"Wrote {OUT_PATH.relative_to(ROOT)} ({n_union} rows; {n_spec} specialist, {n_failed_unique} distinct failed ids)"
    )


if __name__ == "__main__":
    main()
