#!/usr/bin/env python3
"""Regenerate vllm-immediate-targets.yaml — focused vLLM pull queue.

Selection rules (intentional):
  - **Parameters:** total model size **> 21B** (dense or MoE *total* params).
  - **Disk:** approximate full BF16/safetensors snapshot **< 120 GiB** per repo.
  - **Role:** ``general`` | ``specialist`` | ``uncensored`` (vLLM causal chat/code/VLM only).
  - **Scope:** drop small chat (≤21B), embeddings, encoders, and 7B/8B/14B specialists.

This is the **operator queue** for ``vllm_archive_pull_one.py`` (default manifest).
The wide catalog remains in ``_generate_vllm_manifest.py`` / ``vllm-archive-manifest.yaml``.
"""
from __future__ import annotations

import pathlib

import yaml

MAX_APPROX_DISK_GIB = 120.0
MIN_PARAMS_B = 21_000_000_000  # entries must satisfy params_b > this (strictly > 21B)

# pull_order: lower = sooner. Same schema keys as vllm-archive-manifest entries.
ENTRIES: list[dict] = [
    # --- immediate general (dense / instruct / MoE hostable) ---
    {
        "hf_repo": "mistralai/Mistral-Small-24B-Instruct-2501",
        "pull_order": 10,
        "approx_params_b": 24_000_000_000,
        "approx_disk_gib": 48.0,
        "gated": False,
        "target_category": "general",
        "covers_ollama_tags": [],
        "notes": "Strong mid general instruct; Apache-2.0.",
    },
    {
        "hf_repo": "Qwen/Qwen3.5-27B",
        "pull_order": 20,
        "approx_params_b": 27_000_000_000,
        "approx_disk_gib": 54.0,
        "gated": False,
        "target_category": "general",
        "covers_ollama_tags": [],
        "notes": "Dense frontier workhorse; pairs with Qwen3.5-35B MoE.",
    },
    {
        "hf_repo": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
        "pull_order": 30,
        "approx_params_b": 32_000_000_000,
        "approx_disk_gib": 62.0,
        "gated": False,
        "target_category": "general",
        "covers_ollama_tags": [],
        "notes": "Reasoning distill; default R1-32B line for vLLM.",
    },
    {
        "hf_repo": "Qwen/QwQ-32B",
        "pull_order": 40,
        "approx_params_b": 32_000_000_000,
        "approx_disk_gib": 62.0,
        "gated": False,
        "target_category": "general",
        "covers_ollama_tags": [],
        "notes": "Qwen reasoning / long CoT without R1 distill path.",
    },
    {
        "hf_repo": "Qwen/Qwen2.5-Coder-32B-Instruct",
        "pull_order": 50,
        "approx_params_b": 32_000_000_000,
        "approx_disk_gib": 62.0,
        "gated": False,
        "target_category": "general",
        "covers_ollama_tags": [],
        "notes": "Flagship open code instruct in the <120 GiB band.",
    },
    {
        "hf_repo": "deepseek-ai/deepseek-coder-33b-instruct",
        "pull_order": 60,
        "approx_params_b": 33_000_000_000,
        "approx_disk_gib": 62.0,
        "gated": False,
        "target_category": "general",
        "covers_ollama_tags": [],
        "notes": "Dense 33B coder; distinct from Qwen2.5-Coder-32B.",
    },
    {
        "hf_repo": "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
        "pull_order": 70,
        "approx_params_b": 64_000_000_000,
        "approx_disk_gib": 30.0,
        "gated": False,
        "target_category": "general",
        "covers_ollama_tags": [],
        "notes": "MoE (large total params, smaller active); strong code MoE under cap.",
    },
    {
        "hf_repo": "google/gemma-4-26B-A4B-it",
        "pull_order": 80,
        "approx_params_b": 26_000_000_000,
        "approx_disk_gib": 56.0,
        "gated": True,
        "target_category": "general",
        "covers_ollama_tags": [],
        "notes": "Gemma 4 MoE instruct multimodal; accept Gemma licence / HF_TOKEN.",
    },
    {
        "hf_repo": "google/gemma-3-27b-it",
        "pull_order": 90,
        "approx_params_b": 27_000_000_000,
        "approx_disk_gib": 54.0,
        "gated": True,
        "target_category": "general",
        "covers_ollama_tags": [],
        "notes": "Gemma-3 dense 27B instruct; gated.",
    },
    {
        "hf_repo": "Qwen/Qwen3.5-35B-A3B",
        "pull_order": 100,
        "approx_params_b": 35_000_000_000,
        "approx_disk_gib": 72.0,
        "gated": False,
        "target_category": "general",
        "covers_ollama_tags": [],
        "notes": "Qwen3.5 MoE instruct (~3B active); total param count >21B.",
    },
    {
        "hf_repo": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "pull_order": 110,
        "approx_params_b": 46_700_000_000,
        "approx_disk_gib": 87.0,
        "gated": False,
        "target_category": "general",
        "covers_ollama_tags": [],
        "notes": "Sparse MoE ~47B total; still under 120 GiB BF16-class snapshot.",
    },
    {
        "hf_repo": "Qwen/Qwen2.5-VL-32B-Instruct",
        "pull_order": 120,
        "approx_params_b": 32_000_000_000,
        "approx_disk_gib": 65.0,
        "gated": False,
        "target_category": "general",
        "covers_ollama_tags": [],
        "notes": "Vision-language; largest immediate VL in this band.",
    },
    # --- specialist (>21B only) ---
    {
        "hf_repo": "open-r1/OlympicCoder-32B",
        "pull_order": 200,
        "approx_params_b": 32_000_000_000,
        "approx_disk_gib": 62.0,
        "gated": False,
        "target_category": "specialist",
        "covers_ollama_tags": [],
        "notes": "Open R1 code/reasoning line at 32B.",
    },
    # --- uncensored / abliterated / merge (>21B) ---
    {
        "hf_repo": "huihui-ai/DeepSeek-R1-Distill-Qwen-32B-abliterated",
        "pull_order": 300,
        "approx_params_b": 32_000_000_000,
        "approx_disk_gib": 62.0,
        "gated": False,
        "target_category": "uncensored",
        "covers_ollama_tags": [],
        "notes": "Low-refusal R1 Qwen-32B; pair with official distill for A/B.",
    },
    {
        "hf_repo": "huihui-ai/Mistral-Small-24B-Instruct-2501-abliterated",
        "pull_order": 310,
        "approx_params_b": 24_000_000_000,
        "approx_disk_gib": 48.0,
        "gated": False,
        "target_category": "uncensored",
        "covers_ollama_tags": [],
        "notes": "Abliterated Mistral Small 24B vs censored mistralai checkpoint.",
    },
    {
        "hf_repo": "FINGU-AI/RomboUltima-32B",
        "pull_order": 320,
        "approx_params_b": 32_000_000_000,
        "approx_disk_gib": 62.0,
        "gated": False,
        "target_category": "uncensored",
        "covers_ollama_tags": [],
        "notes": "Merge / uncensored experimental 32B.",
    },
]


def main() -> None:
    for e in ENTRIES:
        if e["approx_disk_gib"] > MAX_APPROX_DISK_GIB:
            raise SystemExit(f"Exceeds {MAX_APPROX_DISK_GIB} GiB: {e['hf_repo']}")
        if e["approx_params_b"] <= MIN_PARAMS_B:
            raise SystemExit(f"Must be >21B params: {e['hf_repo']}")

    root = pathlib.Path(__file__).resolve().parents[1]
    out = root / "config" / "vllm-immediate-targets.yaml"

    sorted_entries = sorted(ENTRIES, key=lambda x: (x["pull_order"], x["hf_repo"]))
    total = round(sum(e["approx_disk_gib"] for e in sorted_entries), 1)

    doc = {
        "schema_version": 2,
        "description": "Focused vLLM pull queue: >21B parameters, <120 GiB per model, causal weights only.",
        "updated_note": "Regenerate: uv run python vllm-hosting/scripts/_generate_vllm_immediate_targets.py",
        "policy": {
            "max_approx_disk_gib_per_model": MAX_APPROX_DISK_GIB,
            "min_params_b": MIN_PARAMS_B,
            "roles": ["general", "specialist", "uncensored"],
        },
        "default_archive_root": "/mnt/models/d1/vllm",
        "approx_total_disk_gib_sum": total,
        "approx_total_disk_gib_disclaimer": "Order-of-magnitude per HF snapshot; MoE totals use published total parameter counts.",
        "entries": sorted_entries,
    }
    out.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"Wrote {out} ({len(sorted_entries)} repos, ~{total} GiB summed)")


if __name__ == "__main__":
    main()
