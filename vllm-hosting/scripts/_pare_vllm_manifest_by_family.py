#!/usr/bin/env python3
"""One model per family for core_queue + uncensored (largest approx_disk_gib ≤ cap).

Specialist entries are kept verbatim (size/family exceptions).

Run from repo root:
  python3 vllm-hosting/scripts/_pare_vllm_manifest_by_family.py

Reads:  vllm-hosting/config/vllm-archive-manifest.yaml
Writes: vllm-hosting/config/vllm-archive-manifest-pared-by-family.yaml
"""
from __future__ import annotations

import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "vllm-hosting/config/vllm-archive-manifest.yaml"
DST = ROOT / "vllm-hosting/config/vllm-archive-manifest-pared-by-family.yaml"
MAX_GIB = 120.0

# Omit from pared core/uncensored (covered by specialist instruct checkpoint).
SKIP_REPOS: frozenset[str] = frozenset({"bigcode/starcoder2-15b"})

# Source manifest lists this under core_queue; treat as uncensored in pared output.
FORCE_TARGET_CATEGORY: dict[str, str] = {
    "huihui-ai/Dolphin3.0-Llama3.1-8B-abliterated": "uncensored",
}

# core_queue + uncensored: hf_repo -> family_id (same id => pick one winner by max approx_disk_gib)
FAMILY_BY_REPO: dict[str, str] = {
    # DeepSeek
    "deepseek-ai/deepseek-coder-6.7b-instruct": "deepseek_coder_dense",
    "deepseek-ai/deepseek-coder-33b-instruct": "deepseek_coder_dense",
    "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct": "deepseek_coder_moe_lite",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B": "deepseek_r1_qwen",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B": "deepseek_r1_qwen",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B": "deepseek_r1_qwen",
    "deepseek-ai/DeepSeek-R1-Distill-Llama-8B": "deepseek_r1_llama",
    # Qwen — split coder / chat / 3.5 / VL / reasoning / embedding
    "Qwen/Qwen2.5-Coder-7B-Instruct": "qwen25_coder",
    "Qwen/Qwen2.5-Coder-14B-Instruct": "qwen25_coder",
    "Qwen/Qwen2.5-Coder-32B-Instruct": "qwen25_coder",
    "Qwen/Qwen3-4B-Instruct-2507": "qwen3_chat",
    "Qwen/Qwen3-8B": "qwen3_chat",
    "Qwen/Qwen3-14B": "qwen3_chat",
    "Qwen/Qwen3-30B-A3B-Instruct-2507": "qwen3_chat",
    "Qwen/Qwen3-32B": "qwen3_chat",
    "Qwen/Qwen3.5-9B": "qwen35_chat",
    "Qwen/Qwen3.5-27B": "qwen35_chat",
    "Qwen/Qwen3.5-35B-A3B": "qwen35_chat",
    "Qwen/Qwen2.5-VL-7B-Instruct": "qwen25_vl",
    "Qwen/Qwen2.5-VL-32B-Instruct": "qwen25_vl",
    "Qwen/QwQ-32B": "qwen_qwq",
    "Qwen/Qwen3-Embedding-4B": "qwen_embedding",
    # Meta Llama instruct (single family: prefer largest checkpoint in manifest)
    "meta-llama/Meta-Llama-3.1-8B-Instruct": "meta_llama_instruct",
    "meta-llama/Llama-3.2-3B-Instruct": "meta_llama_instruct",
    # Mistral product lines
    "mistralai/Mixtral-8x7B-Instruct-v0.1": "mistral_mixtral_8x7",
    "mistralai/Mistral-Small-24B-Instruct-2501": "mistral_small_24b",
    "mistralai/Mathstral-7B-v0.1": "mistral_mathstral",
    "microsoft/Phi-4": "microsoft_phi",
    # Gemma: one generative chat line (largest hostable in manifest; 31B remains excluded)
    "google/gemma-4-E2B-it": "gemma_generative_chat",
    "google/gemma-4-E4B-it": "gemma_generative_chat",
    "google/gemma-4-26B-A4B-it": "gemma_generative_chat",
    "google/gemma-3-27b-it": "gemma_generative_chat",
    "google/gemma-3-4b-it": "gemma_generative_chat",
    "google/medgemma-4b-it": "gemma_med",
    "google/embeddinggemma-300m": "gemma_text_embedding",
    # Dolphin (censored): one winner across dphn + cognitivecomputations lines
    "dphn/dolphin-2.6-mistral-7b": "dolphin_censored",
    "dphn/dolphin-2.7-mixtral-8x7b": "dolphin_censored",
    "cognitivecomputations/Dolphin3.0-Llama3.1-8B": "dolphin_censored",
    "huihui-ai/Dolphin3.0-Llama3.1-8B-abliterated": "uncensored_dolphin3_abl",
    "mlabonne/NeuralDaredevil-8B-abliterated": "neuraldaredevil",
    # Embedding families (core)
    "BAAI/bge-m3": "baai_bge_dense",
    "BAAI/bge-large-en-v1.5": "baai_bge_dense",
    "ibm-granite/granite-embedding-107m-multilingual": "ibm_granite_embed",
    "nomic-ai/nomic-embed-text-v1.5": "nomic_embed",
    "Snowflake/snowflake-arctic-embed-m-long": "snowflake_embed_mlong",
    "mixedbread-ai/mxbai-embed-large-v1": "mixedbread_embed",
    # Uncensored — each its own family
    "huihui-ai/DeepSeek-R1-Distill-Qwen-32B-abliterated": "uncensored_r1_qwen32_abl",
    "huihui-ai/Mistral-Small-24B-Instruct-2501-abliterated": "uncensored_mistral24_abl",
    "huihui-ai/Qwen2.5-14B-Instruct-abliterated-v2": "uncensored_qwen25_14_abl",
    "FINGU-AI/RomboUltima-32B": "uncensored_rombo32",
}


def main() -> int:
    if not SRC.is_file():
        print(f"missing {SRC}", file=sys.stderr)
        return 1
    with SRC.open() as f:
        doc = yaml.safe_load(f)
    entries: list[dict] = doc.get("entries") or []
    cap = float(doc.get("policy", {}).get("max_approx_disk_gib_per_model") or MAX_GIB)

    specialist: list[dict] = [dict(e) for e in entries if e.get("target_category") == "specialist"]
    rest = [e for e in entries if e.get("target_category") != "specialist"]

    winners: dict[str, dict] = {}
    missing_family: list[str] = []
    for e in rest:
        repo = e["hf_repo"]
        if repo in SKIP_REPOS:
            continue
        gib = float(e.get("approx_disk_gib") or 0.0)
        if gib > cap:
            missing_family.append(f"{repo} (over cap {cap})")
            continue
        fam = FAMILY_BY_REPO.get(repo)
        if fam is None:
            missing_family.append(repo)
            continue
        cur = winners.get(fam)
        if cur is None or gib > float(cur.get("approx_disk_gib") or 0):
            ee = dict(e)
            fix_cat = FORCE_TARGET_CATEGORY.get(repo)
            if fix_cat is not None:
                ee["target_category"] = fix_cat
            ee["notes"] = (ee.get("notes") or "").strip()
            suffix = f" [pared: family={fam}, largest≤{cap} GiB]"
            ee["notes"] = (ee["notes"] + suffix).strip() if ee["notes"] else suffix.strip()
            winners[fam] = ee

    if missing_family:
        print("Unmapped or over-cap (fix FAMILY_BY_REPO):", file=sys.stderr)
        for m in missing_family:
            print(f"  {m}", file=sys.stderr)
        return 1

    def _cat_order(c: str) -> int:
        return 0 if c == "core_queue" else 1 if c == "uncensored" else 2

    pared_core_uncensored = sorted(
        winners.values(),
        key=lambda x: (
            _cat_order(str(x.get("target_category") or "")),
            -float(x.get("approx_disk_gib") or 0),
            x["hf_repo"],
        ),
    )
    out_entries = pared_core_uncensored + specialist

    total = round(sum(float(e.get("approx_disk_gib") or 0) for e in out_entries), 1)
    out_doc = {
        "schema_version": doc.get("schema_version", 2),
        "description": (
            "Pared from vllm-archive-manifest.yaml: one model per family for "
            "core_queue + uncensored (largest approx_disk_gib within policy cap). "
            "All specialist rows kept. Gemma generative: largest hostable in manifest is "
            "gemma-4-26B-A4B-it (gemma-4-31B-it stays in excluded_over_limit)."
        ),
        "updated_note": "Regenerate: python3 vllm-hosting/scripts/_pare_vllm_manifest_by_family.py",
        "source_manifest": str(SRC.relative_to(ROOT)),
        "policy": doc.get("policy"),
        "default_archive_root": doc.get("default_archive_root"),
        "bandwidth_mib_per_s_default": doc.get("bandwidth_mib_per_s_default"),
        "approx_total_disk_gib_sum": total,
        "approx_total_disk_gib_disclaimer": doc.get("approx_total_disk_gib_disclaimer"),
        "entries": out_entries,
    }

    DST.parent.mkdir(parents=True, exist_ok=True)
    with DST.open("w") as f:
        yaml.dump(
            out_doc,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=1000,
        )
    print(f"Wrote {DST} ({len(out_entries)} entries, ~{total} GiB sum)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
