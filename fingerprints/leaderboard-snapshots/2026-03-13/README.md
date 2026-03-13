# Open LLM Leaderboard Snapshot — 2026-03-13

## Snapshot metadata

| Field | Value |
|---|---|
| **Snapshot date** | `2026-03-13` |
| **Snapshot timestamp (UTC)** | `2026-03-13T15:54:03+00:00` |
| **Source dataset** | [`open-llm-leaderboard/contents`](https://huggingface.co/datasets/open-llm-leaderboard/contents) |
| **Total models** | 4,576 |
| **Files** | `snapshot.json` (full data), `leaderboard.csv` (tabular) |

## Purpose

This directory contains a frozen point-in-time snapshot of the
[Open LLM Leaderboard 2](https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard)
benchmark results, merged with live HuggingFace metadata (downloads, likes, gated status)
fetched on the same date.

Models are routinely removed from the leaderboard (authors delete repos, HF delists
flagged entries). This snapshot preserves the ranking state as it existed on
`2026-03-13` so future model selection and integrity verification can reference it.

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
| 1 | `MaziyarPanahi/calme-3.2-instruct-78b` | 52.08 | 77.97B | 0 |
| 2 | `MaziyarPanahi/calme-3.1-instruct-78b` | 51.29 | 77.97B | 0 |
| 3 | `dfurman/CalmeRys-78B-Orpo-v0.1` | 51.23 | 77.97B | 0 |
| 4 | `MaziyarPanahi/calme-2.4-rys-78b` | 50.77 | 77.97B | 0 |
| 5 | `huihui-ai/Qwen2.5-72B-Instruct-abliterated` | 48.11 | 72.71B | 0 |
| 6 | `Qwen/Qwen2.5-72B-Instruct` | 47.98 | 72.71B | 0 |
| 7 | `MaziyarPanahi/calme-2.1-qwen2.5-72b` | 47.86 | 72.7B | 0 |
| 8 | `newsbang/Homer-v1.0-Qwen2.5-72B` | 47.46 | 72.71B | 0 |
| 9 | `ehristoforu/qwen2.5-test-32b-it` | 47.37 | 32.76B | 0 |
| 10 | `Saxo/Linkbricks-Horizon-AI-Avengers-V1-32B` | 47.34 | 32.76B | 0 |

## Top 10 by HF downloads (with leaderboard entry)

| Rank | Model | Downloads | Score |
|---|---|---|---|


## Files in this directory

```
snapshot.json    — Full JSON dump: all 4,576 models with every field
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
