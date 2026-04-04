# Ollama library metadata snapshot (2026-04-02)

Automated crawl of public pages on [ollama.com](https://ollama.com/library). **No model weights** were downloaded.

## Files

| File | Description |
|------|-------------|
| `snapshot.json` | Full dump: API mirrors, model family list, per-tag rows (site metadata + optional OCI manifest/layer digests) |

## SHA-256 and verifying a GGUF from elsewhere

When **registry manifests** were fetched (default), each tag includes:

- **`manifest_sha256`** — SHA-256 of the raw manifest JSON body (matches the site’s 12-char `digest_prefix` as a prefix).
- **`model_layer_digests`** — full `sha256:…` digests for layers with media type `application/vnd.ollama.image.model` (the stored weight blob; usually one). Compare with:

```bash
sha256sum /path/to/model.gguf
# compare the 64 hex chars to the value after "sha256:" in snapshot.json
```

Non-GGUF / multi-blob models may use other layer types; use the `layers` list. Digests are **Ollama registry blobs**; if upstream repackaged the file, the hash may differ from a random mirror’s GGUF—then prefer a **Hugging Face** LFS fingerprint from this repo’s `fingerprints/` HF crawler.

## Limitations

- HTML layout may change; this snapshot depends on current ollama.com markup.
- `api/tags` and `v1/models` on the website list a **small subset** compared to the full `/library` catalog.
- Registry layout or auth could change; manifest fetch uses public `registry.ollama.ai` OCI endpoints.
- Re-run `scripts/snapshot_ollama_library.py` periodically for point-in-time provenance.

Generated at (UTC): `2026-04-02T17:59:50.307498+00:00`
