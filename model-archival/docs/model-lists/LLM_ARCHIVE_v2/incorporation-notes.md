# LLM_ARCHIVE_v2 Incorporation Notes

Date: 2026-03-21

## Incorporated into `model-archival/config/registry-specialists.yaml`

Added as useful, concrete specialist recommendations with valid HF repos and small-first priority:

- `Equall/Saul-7B-Instruct-v1` (legal)
- `mistralai/Mathstral-7B-v0.1` (math)
- `AI4Chem/ChemLLM-7B-Chat` (chemistry)
- `aaditya/Llama3-OpenBioLLM-8B` (biomedical)
- `jinaai/jina-embeddings-v3` (embeddings/classification)
- `dmis-lab/biobert-base-cased-v1.2` (biomedical classification)
- `microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext` (medical NLP classification)
- `cambridgeltl/SapBERT-from-PubMedBERT-fulltext` (entity linking/classification)

## Deprioritized in specialist registry

Large low-ROI specialist entries were kept but deprioritized to priority 4 on `d5`:

- `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-*`
- `xai-org/grok-2`

`nvidia/Llama-3_1-Nemotron-Ultra-253B-v1` was removed from specialists; it remains in main `registry.yaml` (drive `d1`).

## Not directly incorporated

Items without a concrete HF repo in v2 docs were not directly added:

- `Mol-Instructions`
- implicit/descriptor-only entries without repository IDs

Also, "Uncensored: Yes" claims in v2 were treated as advisory only. Registry inclusion relies on explicit model lineage/notes rather than claim text.
