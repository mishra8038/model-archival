#!/usr/bin/env python3
"""
Build registry.yaml from HuggingFace leaderboard + download rankings.

Outputs config/registry.yaml with full metadata per model:
  - benchmark scores (IFEval, BBH, MATH, GPQA, MUSR, MMLU-PRO, Average)
  - download count, likes, parameter count
  - architecture, licence, gated status
  - family, tier, importance classification
  - snapshot_date (when this registry was generated)

Run:
  uv run python scripts/build_registry.py
  uv run python scripts/build_registry.py --min-relevance 8 --limit 500
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from huggingface_hub import HfApi, hf_hub_download
import pyarrow.parquet as pq

ROOT = Path(__file__).parents[1]
OUT  = ROOT / "config" / "registry.yaml"


def _atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write *content* to *path* via a sibling .tmp file then atomic rename."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding=encoding)
    tmp.replace(path)

# ── Noise filters ─────────────────────────────────────────────────────────────
SKIP_AUTHORS = {
    'trl-internal-testing', 'peft-internal-testing', 'RedHatAI',
    'lmstudio-community', 'mlx-community', 'hugging-quants',
    'casperhansen', 'TheBloke', 'MaziyarPanahi', 'QuantTrio',
    'bullpoint', 'NexVeridian', 'kosbu', 'GadflyII', 'kaitchup',
    'unslothai',
}
SKIP_SUFFIXES = [
    '-AWQ', '-GPTQ', '-bnb-4bit', '-bnb-8bit', '-FP8-dynamic',
    '-quantized', '-MLX', '-NVFP4', '-4bit', '-8bit', '-6bit',
    '-5bit', '-exl2', '-imatrix', '-GGUF',
]
SKIP_NAME_RE = re.compile(
    r'^(1|2|lambda|vram-\d+|aws|other|repeat|tiny-random|tiny-gpt'
    r'|stories\d+|hmellor|unslothai)$', re.I
)


def is_noise(repo_id: str) -> bool:
    author, _, name = repo_id.partition('/')
    if author in SKIP_AUTHORS:
        return True
    nl = name.lower()
    for s in SKIP_SUFFIXES:
        if nl.endswith(s.lower()):
            return True
    if SKIP_NAME_RE.match(name):
        return True
    # obvious test/tiny repos
    if 'tiny-random' in nl or 'tiny-gpt' in nl:
        return True
    return False


# ── Family classifier ─────────────────────────────────────────────────────────
FAMILY_RULES = [
    (r'llama|llama-?2|llama-?3', 'llama'),
    (r'deepseek', 'deepseek'),
    (r'qwen', 'qwen'),
    (r'mistral|mixtral|codestral|devstral|pixtral', 'mistral'),
    (r'gemma', 'gemma'),
    (r'phi-?[1-9]|phi_[1-9]', 'phi'),
    (r'falcon', 'falcon'),
    (r'bloom|bloomz', 'bloom'),
    (r'olmo|tulu', 'olmo'),
    (r'gpt-?neox|pythia|gpt-?j|gpt-?neo', 'eleutherai'),
    (r'gpt2|gpt-?2', 'gpt2'),
    (r'opt\b', 'opt'),
    (r'cohere|c4ai|command-?r|aya\b', 'cohere'),
    (r'vicuna|alpaca', 'llama'),
    (r'dolphin', 'dolphin'),
    (r'hermes', 'hermes'),
    (r'wizard', 'wizardlm'),
    (r'yi-?1|yi-?6|yi-?9|yi-?34', 'yi'),
    (r'internlm', 'internlm'),
    (r'baichuan', 'baichuan'),
    (r'solar\b|solar-', 'solar'),
    (r'exaone', 'exaone'),
    (r'stablelm|stable-?lm', 'stablelm'),
    (r'mamba', 'mamba'),
    (r'glm\b|glm-', 'glm'),
    (r'openelm', 'openelm'),
    (r'bge-|bge_', 'embeddings'),
    (r'e5-|e5_', 'embeddings'),
    (r'embed|embedding', 'embeddings'),
    (r'minimax|mini-?max', 'minimax'),
    (r'nemotron', 'nvidia'),
    (r'granite', 'ibm'),
    (r'llada', 'diffusion'),
    (r'minicpm', 'minicpm'),
    (r'smollm|smol-?lm', 'smollm'),
    (r'codellama|code-?llama', 'llama'),
    (r'codegen', 'codegen'),
    (r'starcoder|star-?coder', 'starcoder'),
    (r'replit', 'replit'),
]


def classify_family(repo_id: str) -> str:
    name = repo_id.lower()
    for pattern, family in FAMILY_RULES:
        if re.search(pattern, name):
            return family
    return 'other'


def classify_tier(repo_id: str, params: float, family: str) -> str:
    """A=flagship, B=code/specialist, C=quant(kept for manual), D=uncensored/abliterated."""
    name = repo_id.lower()
    if any(x in name for x in ['abliterated', 'ablated', 'uncensored', 'dolphin',
                                'hermes', 'lorablated', 'openhermes', 'wizard']):
        return 'D'
    if family in ('embeddings', 'codegen', 'starcoder', 'replit'):
        return 'B'
    if any(x in name for x in ['coder', 'code-', '-code', 'starcoder', 'codegen',
                                'codestral', 'devstral', 'deepcoder', 'math']):
        return 'B'
    return 'A'


def classify_importance(score: float, downloads: int, params: float) -> str:
    if score >= 40 or downloads >= 1_000_000 or params >= 65:
        return 'critical'
    if score >= 25 or downloads >= 100_000 or params >= 13:
        return 'high'
    return 'medium'


# ── Main ──────────────────────────────────────────────────────────────────────

CURATED_PATH = ROOT / "config" / "curated.yaml"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--min-relevance', type=float, default=6.0,
                        help='Minimum combined relevance score (default: 6.0)')
    parser.add_argument('--limit', type=int, default=0,
                        help='Cap number of models (0 = no limit)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print stats without writing registry.yaml')
    args = parser.parse_args()

    api = HfApi()
    snapshot_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    # ── Load leaderboard ──────────────────────────────────────────────────────
    print("Loading Open LLM Leaderboard 2 ...")
    lb_path = hf_hub_download(
        repo_id="open-llm-leaderboard/contents",
        repo_type="dataset",
        filename="data/train-00000-of-00001.parquet",
    )
    tbl = pq.read_table(lb_path).to_pydict()
    n = len(tbl['fullname'])

    leaderboard: dict[str, dict] = {}
    for i in range(n):
        repo = tbl['fullname'][i]
        if not tbl['Available on the hub'][i] or tbl['Flagged'][i]:
            continue
        avg = tbl['Average ⬆️'][i] or 0
        entry = {
            'score':    round(avg, 2),
            'ifeval':   round((tbl['IFEval'][i] or 0), 1),
            'bbh':      round((tbl['BBH'][i] or 0), 1),
            'math':     round((tbl['MATH Lvl 5'][i] or 0), 1),
            'gpqa':     round((tbl['GPQA'][i] or 0), 1),
            'musr':     round((tbl['MUSR'][i] or 0), 1),
            'mmlu_pro': round((tbl['MMLU-PRO'][i] or 0), 1),
            'params':   tbl['#Params (B)'][i] or 0,
            'arch':     tbl['Architecture'][i] or '',
            'licence':  (tbl['Hub License'][i] or 'unknown').lower(),
            'merged':   bool(tbl['Merged'][i]),
            'likes':    tbl['Hub ❤️'][i] or 0,
        }
        if repo not in leaderboard or avg > leaderboard[repo]['score']:
            leaderboard[repo] = entry

    print(f"  {len(leaderboard):,} leaderboard entries")

    # ── Load HF download rankings ─────────────────────────────────────────────
    print("Fetching HF download + popularity data ...")
    hf_data: dict[str, dict] = {}
    for tag in ["text-generation", "feature-extraction", "text2text-generation"]:
        for m in api.list_models(
            pipeline_tag=tag, sort="downloads", limit=3000,
            expand=["downloads", "likes", "gated", "pipeline_tag"],
        ):
            if is_noise(m.id):
                continue
            dl = getattr(m, 'downloads', 0) or 0
            if dl < 3000:
                continue
            if m.id not in hf_data:
                hf_data[m.id] = {
                    'downloads': dl,
                    'likes':     getattr(m, 'likes', 0) or 0,
                    'gated':     bool(getattr(m, 'gated', False)),
                    'pipeline':  tag,
                }
    print(f"  {len(hf_data):,} HF models (≥3k downloads)")

    # ── Merge and score ───────────────────────────────────────────────────────
    all_repos = set(leaderboard) | set(hf_data)
    candidates = []
    for repo in all_repos:
        if is_noise(repo):
            continue
        lb  = leaderboard.get(repo, {})
        hf  = hf_data.get(repo, {})
        score     = lb.get('score', 0)
        downloads = hf.get('downloads', 0)
        likes     = max(lb.get('likes', 0), hf.get('likes', 0))
        params    = lb.get('params', 0)
        gated     = hf.get('gated', False)

        # Combined relevance: weight benchmark score + log(downloads) + likes signal
        relevance = (
            score * 0.55
            + math.log10(downloads + 1) * 10 * 0.35
            + math.log10(likes + 1) * 5 * 0.10
        )

        if relevance < args.min_relevance:
            continue
        if params < 0.5 and downloads < 50_000:
            continue

        # Derive metadata
        family     = classify_family(repo)
        params_use = params if params else 0
        tier       = classify_tier(repo, params_use, family)
        importance = classify_importance(score, downloads, params_use)
        licence    = lb.get('licence') or 'unknown'
        arch       = lb.get('arch', '')
        merged     = lb.get('merged', False)

        candidates.append({
            'repo':       repo,
            'family':     family,
            'tier':       tier,
            'importance': importance,
            'licence':    licence,
            'gated':      gated,
            'arch':       arch,
            'merged':     merged,
            # Metrics for registry metadata
            'params_b':   round(params_use, 2),
            'downloads':  downloads,
            'likes':      likes,
            'lb_score':   score,
            'lb_ifeval':  lb.get('ifeval', 0),
            'lb_bbh':     lb.get('bbh', 0),
            'lb_math':    lb.get('math', 0),
            'lb_gpqa':    lb.get('gpqa', 0),
            'lb_musr':    lb.get('musr', 0),
            'lb_mmlu_pro':lb.get('mmlu_pro', 0),
            'relevance':  round(relevance, 2),
        })

    # Sort by relevance descending
    candidates.sort(key=lambda x: x['relevance'], reverse=True)

    if args.limit:
        candidates = candidates[:args.limit]

    print(f"\n{len(candidates):,} models selected for registry")
    print(f"  Importance breakdown: "
          f"critical={sum(1 for c in candidates if c['importance']=='critical')}, "
          f"high={sum(1 for c in candidates if c['importance']=='high')}, "
          f"medium={sum(1 for c in candidates if c['importance']=='medium')}")
    print(f"  Tier breakdown: "
          f"A={sum(1 for c in candidates if c['tier']=='A')}, "
          f"B={sum(1 for c in candidates if c['tier']=='B')}, "
          f"D={sum(1 for c in candidates if c['tier']=='D')}")
    print(f"  Gated: {sum(1 for c in candidates if c['gated'])}")

    if args.dry_run:
        print("\nTop 30:")
        for i, c in enumerate(candidates[:30], 1):
            print(f"  {i:3}. [{c['importance']:8}] score={c['lb_score']:5.1f} "
                  f"dl={c['downloads']:>10,} {c['repo']}")
        return

    # ── Write registry.yaml ───────────────────────────────────────────────────
    header = f"""\
# =============================================================================
# model-fingerprints registry — AUTO-GENERATED
#
# Generated: {snapshot_date}
# Source:    Open LLM Leaderboard 2 + HuggingFace download rankings
# Models:    {len(candidates)}
#
# Fields:
#   hf_repo        — HuggingFace repo (org/name)
#   family         — Model family (llama / qwen / deepseek / mistral / ...)
#   tier           — A=flagship, B=code/specialist, D=uncensored/abliterated
#   importance     — critical / high / medium
#   licence        — SPDX identifier or common name
#   requires_auth  — true if HF token needed
#   params_b       — parameter count in billions
#   arch           — model architecture (LlamaForCausalLM, etc.)
#   merged         — true if this is a weight-merged model
#   hf_downloads   — HF download count at registry generation time
#   hf_likes       — HF likes at registry generation time
#   lb_score       — Open LLM Leaderboard 2 average score (0–100)
#   lb_ifeval      — IFEval benchmark score
#   lb_bbh         — BBH benchmark score
#   lb_math        — MATH Level 5 score
#   lb_gpqa        — GPQA score
#   lb_musr        — MUSR score
#   lb_mmlu_pro    — MMLU-PRO score
#   registry_date  — date this registry entry was created
# =============================================================================

models:
"""

    # Build list of dicts and let PyYAML handle all quoting correctly
    model_dicts = []
    for c in candidates:
        entry = {
            'hf_repo':      c['repo'],
            'family':       c['family'],
            'tier':         c['tier'],
            'importance':   c['importance'],
            'licence':      c['licence'],
            'requires_auth': bool(c['gated']),
            'params_b':     c['params_b'],
            'merged':       bool(c['merged']),
            'hf_downloads': c['downloads'],
            'hf_likes':     c['likes'],
            'registry_date': snapshot_date,
        }
        if c['arch']:
            entry['arch'] = c['arch']
        if c['lb_score'] > 0:
            entry['lb_score']    = c['lb_score']
            entry['lb_ifeval']   = c['lb_ifeval']
            entry['lb_bbh']      = c['lb_bbh']
            entry['lb_math']     = c['lb_math']
            entry['lb_gpqa']     = c['lb_gpqa']
            entry['lb_musr']     = c['lb_musr']
            entry['lb_mmlu_pro'] = c['lb_mmlu_pro']
        model_dicts.append(entry)

    # ── Merge curated additions (GGUF quants, vision, new releases) ───────────
    curated_extra = []
    if CURATED_PATH.exists():
        curated = yaml.safe_load(CURATED_PATH.read_text()) or {}
        existing_repos = {m['hf_repo'] for m in model_dicts}
        for m in curated.get('models', []):
            if m['hf_repo'] not in existing_repos:
                curated_extra.append(m)
        if curated_extra:
            print(f"  + {len(curated_extra)} curated additions merged from {CURATED_PATH.name}")

    all_models = model_dicts + curated_extra
    header_updated = header.replace(
        f"# Models:    {len(candidates)}",
        f"# Models:    {len(all_models)} ({len(candidates)} leaderboard + {len(curated_extra)} curated)",
    )

    body = yaml.dump(
        {'models': all_models},
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )
    _atomic_write_text(OUT, header_updated + body)
    print(f"\nWrote {OUT}  ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
