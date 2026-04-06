# Model disk manifest (final snapshot)

**Generated:** 2026-04-05 (UTC)  
**Host:** archive VM `a4kg3-artix-xfce`  
**Scope:** All revision directories under `/mnt/models/{d1,d2,d3,d5}/` in **`raw/`**, **`quantized/`**, **`uncensored/`**, and **`specialist/<discipline>/<raw|quantized|uncensored>/`** with **≥ 1 MiB** total file bytes (recursive).  
**Not included:** `d1/.tmp`, `d1/.quarantine`, `d1/graphcore`, `d5/supermicro`, loose files outside the trees above, and anything below the size threshold.

## Machine-readable manifest

- **[MODEL-DISK-MANIFEST-2026-04-05.tsv](MODEL-DISK-MANIFEST-2026-04-05.tsv)** — **370** lines: **1 header + 369** data rows.

### TSV columns

| Column | Meaning |
|--------|---------|
| `drive` | `d1` … `d5` |
| `layout_category` | `raw`, `quantized`, `uncensored`, or `specialist/<discipline>/<sub>` |
| `hf_repo` | Hugging Face–style id `org/name` |
| `revision` | Directory name under the repo (commit SHA, `main`, `latest`, etc.) |
| `size_gib` | Sum of file sizes under that revision dir (**binary GiB**, 1024³) |
| `path` | Absolute path on the VM |

### Row counts by drive (data rows only)

| Drive | Rows | Approx sum `size_gib` |
|-------|------|------------------------|
| d1 | 53 | ~8 872 GiB |
| d2 | 85 | ~5 023 GiB |
| d3 | 220 | ~4 924 GiB |
| d5 | 11 | (see TSV; mostly overflow / specialist-linked trees) |

*Sums are from the manifest scan; they **exclude** non-catalogued mount usage (scratch, quarantine, Ollama mirrors, etc.).*

---

## Redundancy: same `hf_repo` on **multiple drives**

These are **not** necessarily byte-identical trees (different revisions, partials, or stubs), but they **do** share the same HF id and appear on more than one drive—**worth reconciling** if you are hunting space or canonical paths.

| `hf_repo` | Drives | Notes |
|-----------|--------|--------|
| `MiniMaxAI/MiniMax-M2.5` | **d1**, **d3** | **~64 GiB** on d1 vs **~24 GiB** on d3 (same revision dir name)—likely **partial + fuller** copy or interrupted layout; **high overlap risk**. |
| `Qwen/Qwen2.5-Math-72B-Instruct` | **d3**, **d5** | **d3:** tiny stub under `specialist/math/raw/…` (~0.01 GiB). **d5:** **~135 GiB** × **two** rows (`8fcf…` and **`latest`**)—see **same-drive** section; possible **duplicate full trees** on d5. |
| `deepseek-ai/deepseek-coder-6.7b-instruct` | **d2**, **d3** | **d2:** near-empty stub. **d3:** full **~25 GiB** (`e5d64…` + **`latest`**) plus **empty** `specialist/science/raw/…` stub. |
| `meta-llama/Llama-3.2-3B-Instruct` | **d2**, **d3** | **d2:** stub. **d3:** **~12 GiB** ×2 (`0cb8…` + **`latest`**). |
| `microsoft/Phi-4-mini-instruct` | **d2**, **d3** | **d2:** stub. **d3:** **~7 GiB** ×2 (`cfbe…` + **`latest`**). |

**Action ideas:** Remove **stubs** on d2 once you trust d3 copies; **dedupe** MiniMax between d1/d3 after verifying hashes; on **d5** for Qwen2.5-Math-72B, check whether `latest` is a **copy** or **symlink** to the SHA dir (`du` / `stat`).

---

## Redundancy: **same drive**, multiple revisions per `hf_repo`

**164** `(drive, hf_repo)` pairs have **more than one** revision row in the manifest (often **`latest` + commit SHA** with **matching `size_gib`**).

That pattern usually means either:

- **Duplicate full checkouts** (two directories holding the same weights—**~2× space**), or  
- **`latest` symlinked** into the SHA tree (manifest **double-counts** logical size when summing rows—**check with `du -s` / inode**).

Largest **reported** combined footprints (sum of rows, same drive) include:

- **d1** `deepseek-ai/DeepSeek-R1`, `DeepSeek-R1-0528`, `DeepSeek-V3` — each **~2 × ~641 GiB** rows (`latest` + SHA) → **~1.28 TiB** summed per repo if both are full copies.  
- **d1** `mistralai/Mistral-Large-Instruct-2411` — **~2 × ~457 GiB**.  
- **d3** `meta-llama/Llama-3.1-70B-Instruct` — **~2 × ~263 GiB**.  
- **d5** `Qwen/Qwen2.5-Math-72B-Instruct` — **~2 × ~135 GiB** on **d5 only**.

**Anomaly:** `failspy/Meta-Llama-3-70B-Instruct-abliterated-v3.5` on **d3** shows **three** rows (duplicate revision label in listing)—inspect that directory for **stray duplicate** trees.

---

## Anomaly: `failspy/...` triple row

On **d3**, the scanner reported **three** revision entries for `failspy/Meta-Llama-3-70B-Instruct-abliterated-v3.5` (two with the same short SHA prefix in the TSV). Inspect the directory manually—may be **duplicate nested dirs** or a layout bug from a past move.

---

## PAR2 planning

See **[PAR2-STORAGE-ESTIMATE-D1-D2-D3.md](PAR2-STORAGE-ESTIMATE-D1-D2-D3.md)** for headroom vs this manifest’s per-drive totals.

---

## Regenerating

On the archive VM, re-run a full recursive `du` inventory with the same rules (or extend the Python walker used in session) and replace the TSV; bump the date in filenames and this doc.
