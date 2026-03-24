#!/usr/bin/env python3
"""
Merge every recommendation source under model-archival/docs/model-lists into one Markdown table.

Usage (from repo root or this directory):
  python3 model-archival/docs/model-lists/build-merged-database.py

Output:
  model-archival/docs/model-lists/MASTER-RECOMMENDATIONS-DATABASE.md
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT.parent.parent / "config" / "registry-specialists.yaml"

LLM_STEM_DOMAIN = {
    "coding": "coding",
    "legal": "legal",
    "math": "math",
    "chemistry": "chemistry",
    "biomedical": "biomedical",
    "embeddings": "embeddings",
    "classification": "classification",
    "reasoning": "reasoning",
}

SPECIALIST_STEM_DOMAIN = {
    "legal_models": "legal",
    "coding_models": "coding",
    "reasoning_models": "reasoning",
    "math_models": "math",
    "chemistry_models": "chemistry",
    "biomedical_models": "biomedical",
    "embeddings_models": "embeddings",
}


def load_registry_hf_repos() -> set[str]:
    if not REGISTRY.is_file():
        return set()
    repos: set[str] = set()
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s+hf_repo:\s+(\S+)", line)
        if m:
            repos.add(m.group(1).strip())
    return repos


def esc(s: str | None) -> str:
    if s is None:
        return ""
    return str(s).replace("|", "\\|").replace("\n", " ").strip()


def parse_kv_block_body(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in body.splitlines():
        line = line.strip()
        m = re.match(r"^- ([^:]+):\s*(.*)$", line)
        if m:
            out[m.group(1).strip()] = m.group(2).strip()
    return out


def parse_llm_archive_v2_md(path: Path) -> list[dict]:
    stem = path.stem
    if stem in ("incorporation-notes",):
        return []
    default_domain = LLM_STEM_DOMAIN.get(stem, stem)
    text = path.read_text(encoding="utf-8")
    rows: list[dict] = []
    parts = re.split(r"^## ", text, flags=re.M)
    for part in parts[1:]:
        lines = part.splitlines()
        if not lines:
            continue
        title = lines[0].strip()
        body = "\n".join(lines[1:])
        fields = parse_kv_block_body(body)
        domain = fields.get("Domain") or default_domain
        extras = []
        for k in ("Uncensored", "Task", "Type", "Active", "Disk (Q4)"):
            if k in fields:
                extras.append(f"{k}: {fields[k]}")
        rows.append(
            {
                "sources": [str(path.relative_to(ROOT))],
                "kind": "LLM_ARCHIVE_v2",
                "domain": domain,
                "model": title,
                "hf_repo": fields.get("HF Repo"),
                "size": fields.get("Size"),
                "license": fields.get("License"),
                "type_col": fields.get("Type"),
                "highlights": fields.get("Notes"),
                "extras": "; ".join(extras) if extras else None,
            }
        )
    return rows


def parse_stack_recommendation(path: Path) -> list[dict]:
    rows: list[dict] = []
    section = "stack"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip().lower().replace(" ", "_")
            continue
        if section == "strategy":
            continue
        if line.strip().startswith("- "):
            name = line.strip()[2:].strip()
            dom = (
                "embeddings"
                if "embedding" in section
                else "biomedical"
                if "biomed" in section
                else "core"
            )
            rows.append(
                {
                    "sources": [str(path.relative_to(ROOT))],
                    "kind": "stack_recommendation",
                    "domain": dom,
                    "model": name,
                    "hf_repo": None,
                    "size": None,
                    "license": None,
                    "type_col": section,
                    "highlights": None,
                    "extras": None,
                }
            )
    return rows


def parse_source_index(path: Path) -> list[dict]:
    rows: list[dict] = []
    capture = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if "## Normalized Source Names" in line:
            capture = True
            continue
        if capture and line.startswith("## ") and "Normalized" not in line:
            break
        if capture and line.strip().startswith("- "):
            rows.append(
                {
                    "sources": [str(path.relative_to(ROOT))],
                    "kind": "source_index",
                    "domain": "mixed",
                    "model": line.strip()[2:].strip(),
                    "hf_repo": None,
                    "size": None,
                    "license": None,
                    "type_col": None,
                    "highlights": "Normalized name from imported 2026 specialist lists",
                    "extras": None,
                }
            )
    return rows


def parse_specialist_key_models_md(path: Path) -> list[dict]:
    stem = path.stem
    if stem not in SPECIALIST_STEM_DOMAIN:
        return []
    domain = SPECIALIST_STEM_DOMAIN[stem]
    rows: list[dict] = []
    subsection = "general"
    skip_sub = frozenset({"notes", "strategy"})

    def skip_bullets() -> bool:
        sl = subsection.lower()
        return sl in skip_sub or sl.startswith("notes")

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            subsection = line[3:].strip()
            continue
        if skip_bullets():
            continue
        if line.strip().startswith("- "):
            rows.append(
                {
                    "sources": [str(path.relative_to(ROOT))],
                    "kind": "specialist-models",
                    "domain": domain,
                    "model": line.strip()[2:].strip(),
                    "hf_repo": None,
                    "size": None,
                    "license": None,
                    "type_col": subsection,
                    "highlights": None,
                    "extras": None,
                }
            )
    return rows


def parse_specialist_ai_models_2026_md(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    rows: list[dict] = []
    section_major = "reference-2026"
    section_minor = ""
    pending_header: list[str] | None = None

    def bump_section(line: str) -> None:
        nonlocal section_major, section_minor, pending_header
        if line.startswith("## "):
            section_major = line[3:].strip()
            section_minor = ""
            pending_header = None
        elif line.startswith("### "):
            section_minor = line[4:].strip()

    def norm_header_cell(c: str) -> str:
        return re.sub(r"^\*\*|\*\*$", "", c).strip()

    for line in text.splitlines():
        bump_section(line)
        s = line.strip()
        if not s.startswith("|") or s.count("|") < 3:
            continue
        cells = [c.strip() for c in s.split("|")[1:-1]]
        if len(cells) < 3:
            continue
        # Markdown table separator |---|---|
        if cells and all(not re.sub(r"^:?|:-?$", "", c.strip()) or set(c) <= {":", "-"} for c in cells):
            continue
        c0 = norm_header_cell(cells[0])
        if c0 in ("Model", "Model / Tool"):
            pending_header = [norm_header_cell(x) for x in cells]
            continue
        raw_name = cells[0]
        name = re.sub(r"^\*\*|\*\*$", "", raw_name).strip()
        if not name:
            continue
        col1 = cells[1]
        highlights = cells[2]
        if pending_header and len(pending_header) >= 3:
            h1, h2 = pending_header[1], pending_header[2]
            if "developer" in h1.lower():
                type_col = f"Developer: {col1}"
            elif "type" in h1.lower():
                type_col = f"Type: {col1}"
            else:
                type_col = f"{h1}: {col1}"
            if "highlights" not in h2.lower():
                highlights = " | ".join(cells[2:])
        else:
            type_col = col1
        if type_col.lower() in ("type", "developer", "highlights"):
            continue
        dom = section_major
        if "material" in section_major.lower():
            dom = "materials"
        elif "Legal" in section_minor or "legal" in section_minor.lower():
            dom = "legal"
        elif "Mathematics" in section_minor or "math" in section_minor.lower():
            dom = "math"
        elif "Chemistry" in section_minor or "chemistry" in section_minor.lower():
            dom = "chemistry"
        elif "Biomedical" in section_minor or "biomedical" in section_minor.lower():
            dom = "biomedical"
        elif "Translation" in section_minor:
            dom = "translation"
        elif "Reasoning" in section_minor:
            dom = "reasoning"
        elif "Finance" in section_minor:
            dom = "finance"
        elif "Cybersecurity" in section_minor or "Sciences" in section_minor:
            dom = "science_security"
        elif "Coding" in section_major:
            dom = "coding"
        elif "SLM" in section_major or "Small Language" in section_major:
            dom = "slm"

        rows.append(
            {
                "sources": [str(path.relative_to(ROOT))],
                "kind": "specialist_ai_models_2026",
                "domain": dom,
                "model": name,
                "hf_repo": None,
                "size": None,
                "license": None,
                "type_col": f"{section_minor or section_major}: {type_col}",
                "highlights": highlights,
                "extras": None,
            }
        )
    return rows


def parse_reconciliation(path: Path) -> list[dict]:
    rows: list[dict] = []
    in_mapped = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("| Source Item |"):
            in_mapped = True
            continue
        if in_mapped:
            if not line.startswith("|"):
                break
            if line.startswith("|---"):
                continue
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) < 4:
                continue
            if cells[0] == "Source Item":
                continue
            rows.append(
                {
                    "sources": [str(path.relative_to(ROOT))],
                    "kind": "reconciliation",
                    "domain": "registry_mapping",
                    "model": cells[0],
                    "hf_repo": cells[1].replace("`", "").strip(),
                    "size": cells[3],
                    "license": None,
                    "type_col": cells[2],
                    "highlights": "Mapped to project registry / run_state (see doc)",
                    "extras": None,
                }
            )
    return rows


def parse_metadata_json(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for m in data.get("models", []):
        rows.append(
            {
                "sources": [str(path.relative_to(ROOT))],
                "kind": "metadata.json",
                "domain": m.get("domain", ""),
                "model": m.get("name", ""),
                "hf_repo": None,
                "size": m.get("size"),
                "license": "open" if m.get("open") else None,
                "type_col": None,
                "highlights": None,
                "extras": None,
            }
        )
    return rows


def parse_incorporation_notes(path: Path) -> list[dict]:
    """Explicit HF repos called out for registry-specialists."""
    rows: list[dict] = []
    section = "preamble"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        for m in re.finditer(r"`([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)`", line):
            repo = m.group(1)
            rows.append(
                {
                    "sources": [str(path.relative_to(ROOT))],
                    "kind": "incorporation-notes",
                    "domain": "registry_note",
                    "model": repo.split("/")[-1],
                    "hf_repo": repo,
                    "size": None,
                    "license": None,
                    "type_col": section,
                    "highlights": "Mentioned in LLM_ARCHIVE_v2 incorporation notes",
                    "extras": None,
                }
            )
    return rows


def dedup_key(r: dict) -> tuple[str, str]:
    hr = (r.get("hf_repo") or "").strip()
    if hr and "/" in hr:
        # mapping cells may list several `org/repo` — dedupe by first repo id
        first = re.split(r"\s*,\s*", hr.replace("`", ""))[0].strip()
        if "/" in first:
            return ("hf", first.lower())
    name = re.sub(r"[^a-z0-9]+", " ", (r.get("model") or "").lower()).strip()
    return ("name", name)


def merge_rows(group: list[dict]) -> dict:
    group = sorted(
        group,
        key=lambda r: (
            -(len((r.get("hf_repo") or "").strip())),
            r.get("kind", ""),
        ),
    )
    base = dict(group[0])
    sources = sorted({s for r in group for s in r["sources"]})
    kinds = sorted({r["kind"] for r in group})
    domains = sorted({r["domain"] for r in group if r.get("domain")})
    # prefer non-empty fields; longest hf_repo first (sort above)
    for key in ("hf_repo", "size", "license", "highlights", "type_col", "extras"):
        for r in group:
            v = r.get(key)
            if v:
                base[key] = v
                break
    base["sources"] = sources
    base["kind"] = ";".join(kinds)
    base["domain"] = "; ".join(domains) if domains else base.get("domain", "")
    return base


def main() -> None:
    all_rows: list[dict] = []
    # LLM_ARCHIVE_v2
    for p in sorted((ROOT / "LLM_ARCHIVE_v2").glob("*.md")):
        all_rows.extend(parse_llm_archive_v2_md(p))
    # metadata
    meta = ROOT / "LLM_ARCHIVE_v2" / "metadata.json"
    if meta.is_file():
        all_rows.extend(parse_metadata_json(meta))
    # specialist-models
    for p in sorted((ROOT / "specialist-models").glob("*.md")):
        if p.name == "README.md":
            continue
        all_rows.extend(parse_specialist_key_models_md(p))
        if p.name == "specialist_ai_models_2026.md":
            all_rows.extend(parse_specialist_ai_models_2026_md(p))
    stack = ROOT / "specialist-models" / "stack_recommendation.md"
    if stack.is_file():
        all_rows.extend(parse_stack_recommendation(stack))
    # top-level docs
    for name in (
        "specialist-ai-models-2026-source-index.md",
        "specialist-ai-models-2026-reconciliation.md",
    ):
        p = ROOT / name
        if p.is_file():
            if "source-index" in name:
                all_rows.extend(parse_source_index(p))
            else:
                all_rows.extend(parse_reconciliation(p))
    inc = ROOT / "LLM_ARCHIVE_v2" / "incorporation-notes.md"
    if inc.is_file():
        all_rows.extend(parse_incorporation_notes(inc))

    reg = load_registry_hf_repos()

    by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in all_rows:
        by_key[dedup_key(r)].append(r)
    merged = [merge_rows(g) for g in by_key.values()]
    merged.sort(key=lambda x: (x["domain"], x["model"].lower()))

    lines: list[str] = [
        "# Master recommendations database (merged)",
        "",
        f"Generated: **{date.today().isoformat()}**. Regenerate with:",
        "",
        "```bash",
        "python3 model-archival/docs/model-lists/build-merged-database.py",
        "```",
        "",
        "Single table merging curated rows from `LLM_ARCHIVE_v2/`, `specialist-models/`, ",
        "`specialist-ai-models-2026-*.md`, and `metadata.json`. ",
        "Rows with the same Hugging Face repo id (or same normalized model name when no repo is given) are **deduplicated**; the **Sources** column lists every file that mentioned them.",
        "",
        "**`registry_specialists`**: `yes` if any `org/name` token in the cell exactly matches an `hf_repo` in `model-archival/config/registry-specialists.yaml`.",
        "",
    ]

    if not REGISTRY.is_file():
        lines.append(
            f"*Warning: registry file not found at `{REGISTRY}` — column `registry_specialists` is empty.*"
        )
        lines.append("")

    lines.append(
        "| # | Sources | Kind | Domain | Model | HF repo / mapping | Size | License / open | Type / subsection | Highlights / notes | Extras | registry_specialists |"
    )
    lines.append(
        "|---:|---|---|---|---|---|---|---|---|---|---|---|"
    )

    def in_registry(cell: str) -> str:
        if not cell or not reg:
            return ""
        parts = re.findall(r"([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)", cell)
        for p in parts:
            if p in reg:
                return "yes"
        return "no"

    for i, r in enumerate(merged, start=1):
        hr = r.get("hf_repo") or ""
        lines.append(
            "| "
            + " | ".join(
                [
                    str(i),
                    esc("; ".join(r["sources"])),
                    esc(r.get("kind")),
                    esc(r.get("domain")),
                    esc(r.get("model")),
                    esc(hr),
                    esc(r.get("size")),
                    esc(r.get("license")),
                    esc(r.get("type_col")),
                    esc(r.get("highlights")),
                    esc(r.get("extras")),
                    in_registry(hr),
                ]
            )
            + " |"
        )

    out = ROOT / "MASTER-RECOMMENDATIONS-DATABASE.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(merged)} rows to {out}")


if __name__ == "__main__":
    main()
