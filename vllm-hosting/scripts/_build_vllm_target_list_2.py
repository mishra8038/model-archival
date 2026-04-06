#!/usr/bin/env python3
"""Build vllm-target-list-2.yaml from vllm-archive-manifest-pared-by-family.yaml.

Removes:
  - Explicit operator prune list (see PRUNE_HF_REPOS).
  - All math-oriented models (Mathstral, OlympicCoder, Qwen*-Math*, deepseek-math,
    NuminaMath, MetaMath, WizardMath, OpenMath-Nemotron, MAmmoTH2, etc.).
  - Smaller legal encoders (see LEGAL_PRUNE_HF_REPOS); keeps **pile-of-law/legalbert-large-1.7M-2** only.
  - Any row whose **covers_ollama_tags** intersects **ollama-hosting/registry/TARGET_QUEUE_ORDERED.txt**
    (Ollama pull queue) — avoids duplicating weights already pulled as Ollama blobs.

Run from repo root:
  python3 vllm-hosting/scripts/_build_vllm_target_list_2.py
"""
from __future__ import annotations

import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "vllm-hosting/config/vllm-archive-manifest-pared-by-family.yaml"
DST = ROOT / "vllm-hosting/config/vllm-target-list-2.yaml"
OLLAMA_QUEUE_TXT = ROOT / "ollama-hosting/registry/TARGET_QUEUE_ORDERED.txt"

# nlpaueb Legal-BERT base/small — drop in favour of Pile-of-Law LegalBERT-large.
LEGAL_PRUNE_HF_REPOS: frozenset[str] = frozenset(
    {
        "nlpaueb/legal-bert-base-uncased",
        "nlpaueb/legal-bert-small-uncased",
    }
)

PRUNE_HF_REPOS: frozenset[str] = frozenset(
    {
        "google/gemma-4-26B-A4B-it",
        "mistralai/Mistral-Small-24B-Instruct-2501",
        "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
        "microsoft/Phi-4",
        "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "Qwen/Qwen2.5-VL-32B-Instruct",
        "Qwen/Qwen3-30B-A3B-Instruct-2507",
        "Qwen/QwQ-32B",
    }
)

# Explicit math / olympiad / tool-math lines (beyond substring rules below).
MATH_HF_REPOS: frozenset[str] = frozenset(
    {
        "mistralai/Mathstral-7B-v0.1",
        "open-r1/OlympicCoder-7B",
        "open-r1/OlympicCoder-32B",
        "Qwen/Qwen2.5-Math-7B-Instruct",
        "Qwen/Qwen2.5-Math-1.5B-Instruct",
        "deepseek-ai/deepseek-math-7b-instruct",
        "Qwen/Qwen2-Math-7B-Instruct",
        "AI-MO/NuminaMath-7B-TIR",
        "AI-MO/NuminaMath-7B-CoT",
        "qingy2019/Qwen2.5-Math-14B-Instruct",
        "meta-math/MetaMath-Mistral-7B",
        "WizardLMTeam/WizardMath-7B-V1.1",
        "nvidia/OpenMath-Nemotron-1.5B",
        "nvidia/OpenMath-Nemotron-7B",
        "TIGER-Lab/MAmmoTH2-8B",
    }
)

_MATH_TOKENS = re.compile(
    r"(^|/)(math|numina|olympiccoder|metamath|wizardmath|openmath|mammoth|"
    r"deepseek-math|qwen2\.5-math|qwen2-math)(/|$|-)",
    re.IGNORECASE,
)


def load_ollama_queue_tags(path: pathlib.Path) -> frozenset[str]:
    """Ollama library tags from TARGET_QUEUE_ORDERED.txt (one per line)."""
    if not path.is_file():
        return frozenset()
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.add(s)
    return frozenset(out)


def entry_covers_ollama_queue(entry: dict, ollama_tags: frozenset[str]) -> bool:
    raw = entry.get("covers_ollama_tags")
    if not raw:
        return False
    for t in raw:
        if not isinstance(t, str):
            continue
        if t.strip() in ollama_tags:
            return True
    return False


def is_math_model(hf_repo: str) -> bool:
    if hf_repo in MATH_HF_REPOS:
        return True
    slug = hf_repo.split("/")[-1]
    if _MATH_TOKENS.search(hf_repo) or _MATH_TOKENS.search(slug):
        return True
    low = hf_repo.lower()
    if "numinamath" in low or "olympiccoder" in low or "mammoth2" in low:
        return True
    return False


def main() -> int:
    if not SRC.is_file():
        print(f"missing {SRC}", file=sys.stderr)
        return 1
    doc = yaml.safe_load(SRC.read_text(encoding="utf-8"))
    entries_in = doc.get("entries") or []
    if not OLLAMA_QUEUE_TXT.is_file():
        print(f"warning: missing {OLLAMA_QUEUE_TXT} — Ollama-tag dedupe skipped", file=sys.stderr)
    ollama_tags = load_ollama_queue_tags(OLLAMA_QUEUE_TXT)

    kept: list[dict] = []
    for e in entries_in:
        repo = e["hf_repo"]
        if repo in PRUNE_HF_REPOS:
            continue
        if is_math_model(repo):
            continue
        if repo in LEGAL_PRUNE_HF_REPOS:
            continue
        if entry_covers_ollama_queue(e, ollama_tags):
            continue
        kept.append(dict(e))

    # Stable order: core_queue, uncensored, specialist; then disk desc, repo name
    def sort_key(x: dict) -> tuple[int, float, str]:
        cat = str(x.get("target_category") or "")
        o = 0 if cat == "core_queue" else 1 if cat == "uncensored" else 2
        return (o, -float(x.get("approx_disk_gib") or 0), x["hf_repo"])

    kept.sort(key=sort_key)

    for i, e in enumerate(kept, start=1):
        e["pull_order"] = i * 10

    total = round(sum(float(e.get("approx_disk_gib") or 0) for e in kept), 1)
    out = {
        "schema_version": doc.get("schema_version", 2),
        "description": (
            "vLLM target list 2: derived from vllm-archive-manifest-pared-by-family.yaml "
            "minus explicit prunes (incl. **google/gemma-4-26B-A4B-it**), math-specialist models, "
            "small legal encoders, and any HF row whose **covers_ollama_tags** hits "
            "**ollama-hosting/registry/TARGET_QUEUE_ORDERED.txt** (skip duplicating Ollama pulls)."
        ),
        "updated_note": "Regenerate: python3 vllm-hosting/scripts/_build_vllm_target_list_2.py",
        "source_manifest": str(SRC.relative_to(ROOT)),
        "ollama_queue_tag_source": str(OLLAMA_QUEUE_TXT.relative_to(ROOT)),
        "policy": doc.get("policy"),
        "default_archive_root": doc.get("default_archive_root"),
        "bandwidth_mib_per_s_default": doc.get("bandwidth_mib_per_s_default"),
        "approx_total_disk_gib_sum": total,
        "approx_total_disk_gib_disclaimer": doc.get("approx_total_disk_gib_disclaimer"),
        "entries": kept,
    }

    DST.parent.mkdir(parents=True, exist_ok=True)
    with DST.open("w", encoding="utf-8") as f:
        yaml.dump(out, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000)
    print(f"Wrote {DST} ({len(kept)} entries, ~{total} GiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
