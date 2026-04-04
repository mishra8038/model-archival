"""
snapshot_ollama_library.py — Archive Ollama.com public library metadata (no weights).

Sources (all read-only HTTP GET):
  - https://ollama.com/api/tags          — JSON; small curated set + partial digests
  - https://ollama.com/v1/models         — OpenAI-style JSON model list
  - https://ollama.com/library           — HTML; all library model families (~200+)
  - https://ollama.com/library/<name>/tags — HTML; tags per family with 12-hex digest
    prefix, human-readable size, context window
  - https://registry.ollama.ai/v2/library/<model>/manifests/<tag> — OCI manifest JSON
    (default). Yields full manifest SHA-256 (hash of response body) and per-layer
    digests. The primary weight blob uses media type application/vnd.ollama.image.model;
    its digest is the SHA-256 of the blob bytes as stored by Ollama (typically the
    raw GGUF file). Verify a local .gguf with: sha256sum file.gguf  (compare hex to
    the digest after the sha256: prefix).

Use --no-manifests for a faster crawl (HTML + site JSON only).

Output (written under --output-dir):
  ollama-library/
    YYYY-MM-DD/
      snapshot.json   — unified machine-readable dump
      README.md       — methodology and limitations

Usage:
  cd fingerprints && uv run python scripts/snapshot_ollama_library.py
  uv run python scripts/snapshot_ollama_library.py --output-dir /mnt/models/d3/archive
  uv run python scripts/snapshot_ollama_library.py --max-models 5   # smoke test
  uv run python scripts/snapshot_ollama_library.py --no-manifests   # skip registry
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import httpx

BASE = "https://ollama.com"
REGISTRY = "https://registry.ollama.ai"
MANIFEST_ACCEPT = "application/vnd.docker.distribution.manifest.v2+json"
MT_OLLAMA_MODEL_LAYER = "application/vnd.ollama.image.model"
LIBRARY_RE = re.compile(r'href="/library/([^":/]+)"')
# One table row on /library/<model>/tags (mobile block has digest • size • context)
TAG_CHUNK_RE = re.compile(
    r'<span class="font-mono">\s*(?P<digest>[0-9a-f]{12})\s*</span>\s*•\s*'
    r'(?P<size>[0-9.]+\s*(?:GB|MB|KB))\s*•\s*'
    r'(?P<context>[^•<]+)',
    re.IGNORECASE,
)
HREF_MODEL_TAG_RE = re.compile(r'href="/library/(?P<base>[^":/]+):(?P<tag>[^"]+)"')


def _atomic_write_json(path: Path, data: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _atomic_write_text(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def fetch_text(client: httpx.Client, url: str, timeout: float) -> str:
    r = client.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text


def discover_library_models(html: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for m in LIBRARY_RE.finditer(html):
        name = m.group(1).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name)
    out.sort()
    return out


def parse_tags_page(html: str, model_base: str) -> list[dict]:
    """Extract tag rows that belong to *model_base* (one HTML row group at a time)."""
    rows: list[dict] = []
    seen_tag: set[str] = set()
    for chunk in html.split('<div class="group px-4 py-3">'):
        if model_base not in chunk:
            continue
        hm = HREF_MODEL_TAG_RE.search(chunk)
        if not hm or hm.group("base") != model_base:
            continue
        tag = hm.group("tag")
        if tag in seen_tag:
            continue
        dm = TAG_CHUNK_RE.search(chunk)
        if not dm:
            continue
        seen_tag.add(tag)
        rows.append(
            {
                "model": f"{model_base}:{tag}",
                "digest_prefix": dm.group("digest").lower(),
                "size_label": dm.group("size").replace("\n", " ").strip(),
                "context_label": dm.group("context").replace("\n", " ").strip(),
            }
        )
    return rows


def fetch_manifest_digests(
    client: httpx.Client,
    model_base: str,
    tag: str,
    timeout: float,
) -> dict:
    """
    GET OCI manifest from registry.ollama.ai (no layer/blob download).
    Returns manifest_sha256 (hex of raw JSON body), layer list, and model-layer digests.
    """
    m_enc = quote(model_base, safe="")
    t_enc = quote(tag, safe="")
    url = f"{REGISTRY}/v2/library/{m_enc}/manifests/{t_enc}"
    r = client.get(url, timeout=timeout, headers={"Accept": MANIFEST_ACCEPT})
    if r.status_code == 404:
        return {"manifest_url": url, "manifest_error": "HTTP 404 (manifest not found)"}
    r.raise_for_status()
    raw = r.content
    manifest_sha256 = hashlib.sha256(raw).hexdigest()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return {
            "manifest_url": url,
            "manifest_error": f"invalid manifest JSON: {e}",
            "manifest_sha256": manifest_sha256,
        }
    layers_out: list[dict] = []
    model_layer_digests: list[str] = []
    for lay in data.get("layers") or []:
        mt = lay.get("mediaType")
        dg = lay.get("digest")
        sz = lay.get("size")
        layers_out.append({"media_type": mt, "digest": dg, "size_bytes": sz})
        if mt == MT_OLLAMA_MODEL_LAYER and isinstance(dg, str):
            model_layer_digests.append(dg)
    cfg = data.get("config") if isinstance(data.get("config"), dict) else {}
    return {
        "manifest_url": url,
        "manifest_sha256": manifest_sha256,
        "config_digest": cfg.get("digest"),
        "config_size_bytes": cfg.get("size"),
        "layers": layers_out,
        "model_layer_digests": model_layer_digests,
    }


def run(
    output_dir: Path,
    timeout: float,
    delay_s: float,
    manifest_delay_s: float,
    fetch_manifests: bool,
    max_models: int | None,
    user_agent: str,
) -> Path:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = output_dir / "ollama-library" / day
    out.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": user_agent}
    snapshot: dict = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "api_tags": f"{BASE}/api/tags",
            "openai_models": f"{BASE}/v1/models",
            "library_index": f"{BASE}/library",
            "tags_template": f"{BASE}/library/<model>/tags",
            "oci_manifest_template": f"{REGISTRY}/v2/library/<model>/manifests/<tag>",
        },
        "fetch_manifests": fetch_manifests,
        "notes": (
            "digest_prefix matches the first 12 hex chars of manifest_sha256 when manifests are fetched. "
            "model_layer_digests are full OCI blob digests (sha256:...) for application/vnd.ollama.image.model; "
            "compare sha256sum of a local .gguf to the 64-hex part after sha256: when the blob is the same file."
        ),
        "api_tags": None,
        "openai_models": None,
        "library_models": [],
        "models_with_errors": {},
    }

    with httpx.Client(headers=headers, follow_redirects=True) as client:
        api_tags_raw = fetch_text(client, f"{BASE}/api/tags", timeout)
        snapshot["api_tags"] = json.loads(api_tags_raw)

        oa_raw = fetch_text(client, f"{BASE}/v1/models", timeout)
        snapshot["openai_models"] = json.loads(oa_raw)

        lib_html = fetch_text(client, f"{BASE}/library", timeout)
        models = discover_library_models(lib_html)
        if max_models is not None:
            models = models[: max(0, max_models)]

        snapshot["library_models"] = models

        per_model: dict[str, object] = {}
        for i, name in enumerate(models):
            url = f"{BASE}/library/{name}/tags"
            try:
                tags_html = fetch_text(client, url, timeout)
                tags = parse_tags_page(tags_html, name)
                per_model[name] = {
                    "tags_url": url,
                    "tag_count": len(tags),
                    "tags": tags,
                }
            except Exception as e:  # noqa: BLE001 — collect and continue
                snapshot["models_with_errors"][name] = {"url": url, "error": str(e)}
                per_model[name] = {"tags_url": url, "tag_count": 0, "tags": [], "error": str(e)}
            if delay_s > 0 and i + 1 < len(models):
                time.sleep(delay_s)

        snapshot["library_tag_catalog"] = per_model

        manifest_ok = 0
        manifest_fail = 0
        if fetch_manifests:
            for name in models:
                info = per_model.get(name)
                if not isinstance(info, dict) or info.get("error"):
                    continue
                tags_list = info.get("tags") or []
                for row in tags_list:
                    if not isinstance(row, dict):
                        continue
                    parts = row.get("model", "").split(":", 1)
                    if len(parts) != 2:
                        manifest_fail += 1
                        row["manifest_error"] = "could not parse model:tag"
                        continue
                    base, t = parts[0], parts[1]
                    try:
                        extra = fetch_manifest_digests(client, base, t, timeout)
                        row.update(extra)
                        if row.get("manifest_error"):
                            manifest_fail += 1
                        else:
                            manifest_ok += 1
                    except Exception as e:  # noqa: BLE001
                        manifest_fail += 1
                        row["manifest_error"] = str(e)
                    if manifest_delay_s > 0:
                        time.sleep(manifest_delay_s)
            snapshot["summary_manifests"] = {"ok": manifest_ok, "failed": manifest_fail}

    total_tags = sum(
        int(v.get("tag_count", 0))  # type: ignore[union-attr]
        for v in per_model.values()
        if isinstance(v, dict)
    )
    snapshot["summary"] = {
        "library_model_families": len(models),
        "total_tag_rows": total_tags,
        "api_tags_models": len(snapshot["api_tags"].get("models", [])),  # type: ignore[union-attr]
        "openai_models_count": len(
            (snapshot["openai_models"] or {}).get("data", [])  # type: ignore[union-attr]
        ),
        "fetch_errors": len(snapshot["models_with_errors"]),
    }
    if fetch_manifests and "summary_manifests" in snapshot:
        snapshot["summary"]["manifest_fetch_ok"] = snapshot["summary_manifests"]["ok"]
        snapshot["summary"]["manifest_fetch_failed"] = snapshot["summary_manifests"]["failed"]

    snap_path = out / "snapshot.json"
    _atomic_write_json(snap_path, snapshot)

    readme = f"""# Ollama library metadata snapshot ({day})

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

Generated at (UTC): `{snapshot["fetched_at_utc"]}`
"""
    _atomic_write_text(out / "README.md", readme)
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Archive Ollama.com library metadata (JSON + HTML crawl).")
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Directory under which ollama-library/YYYY-MM-DD/ is created (default: fingerprints/)",
    )
    p.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout seconds")
    p.add_argument(
        "--delay",
        type=float,
        default=0.15,
        help="Seconds to sleep between per-model tag page requests (be polite)",
    )
    p.add_argument("--max-models", type=int, default=None, help="Only fetch tags for first N families (test)")
    p.add_argument(
        "--no-manifests",
        action="store_true",
        help="Do not query registry.ollama.ai for OCI manifests (no full layer SHA-256)",
    )
    p.add_argument(
        "--manifest-delay",
        type=float,
        default=0.05,
        help="Sleep seconds between each manifest GET (default: 0.05)",
    )
    p.add_argument(
        "--user-agent",
        default="model-archival-fingerprints/snapshot_ollama_library (+https://github.com/ollama/ollama)",
        help="User-Agent header",
    )
    args = p.parse_args()
    out = run(
        output_dir=args.output_dir.resolve(),
        timeout=args.timeout,
        delay_s=args.delay,
        manifest_delay_s=args.manifest_delay,
        fetch_manifests=not args.no_manifests,
        max_models=args.max_models,
        user_agent=args.user_agent,
    )
    print(out / "snapshot.json")


if __name__ == "__main__":
    main()
