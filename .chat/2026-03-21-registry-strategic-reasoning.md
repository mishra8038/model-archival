# registry-specialists — strategic / game theory

Added 5 models to `model-archival/config/registry-specialists.yaml` after `DeepSeek-R1-Distill-Qwen-7B`:

- `deepseek-ai/DeepSeek-R1-Distill-Llama-8B` (d3, P2) — small strategic baseline
- `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B` (d3, P2) — mid R1-distill
- `mistralai/Mistral-Small-24B-Instruct-2501` (d5, P2) — dialogue/negotiation class; complements existing tensorblock abliterated GGUF
- `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` (d5, P3) — BF16 parent of 32B abliterated GGUF
- `Qwen/QwQ-32B` (d5, P3) — QwQ reasoning line

Notes use `[discipline:strategic_reasoning]` and `[game_theory]` where relevant.  
`SPECIALIST-LLM-LEADERS-UNCENSORED-STRATEGIC.md` §4 updated with this table.

HF API returned HTTP 200 for all five repo ids.
