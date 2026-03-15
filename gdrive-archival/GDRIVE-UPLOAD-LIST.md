# GDrive critical backup list

GDrive is more reliable than our local disks. This list is the backup we can't live without — **base (pre-trained) models only**, so we preserve foundations for fine-tuning and inference without depending on instruct variants.

It is used when `upload_selection` is **not** set in `config.yaml`.

**Policy:**
- **Base models only** — no instruct; save the pre-trained base when available (Qwen2.5 3B/7B/14B/32B/72B, Gemma-27b-pt).
- **model_ids_gguf** — empty by default; registry GGUF are instruct quants. Add base GGUF here when available.
- **Lean on smaller** — all listed bases are &lt;200 GB except 72B (~135 GB).

Edit `model_ids_gguf` and `model_ids_full` in `config.yaml` to add more bases (e.g. Llama-3.1-405B, DeepSeek-V3-Base) or restore GGUF/instruct if you change policy. To switch to budget-based selection (fill up to 3 TB from D2/D3 by size), uncomment `upload_selection` and the explicit lists will be ignored.
