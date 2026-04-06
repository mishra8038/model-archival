# Freed space recalculation — D1 / D2 / D3 (post-prune)

**Date:** 2026-04-05 (UTC)  
**Scope:** Documented operator prunes and dedupe pass; **not** a live `df` / `du` on the archive VM. Re-run `df -B1` and regenerate [`MODEL-DISK-MANIFEST-*.tsv`](MODEL-DISK-MANIFEST-2026-04-05.tsv) on **192.168.8.65** for authoritative numbers.

All **GiB** below are **binary GiB** (1024³), consistent with the disk manifest and [`D1-PRUNE-CANDIDATES.md`](D1-PRUNE-CANDIDATES.md).

---

## D1 — estimated freed

| Source | Est. freed (GiB) | Basis |
|--------|------------------:|--------|
| **Nemotron Super 120B (both BF16 trees on D1)** | **120.92** | Last manifest: `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16` **88.370** + `…-Base-BF16` **32.546** ([`MODEL-DISK-MANIFEST-2026-04-05.tsv`](MODEL-DISK-MANIFEST-2026-04-05.tsv)). Matches progress math (HF total − remaining) from [D1-PRUNE-CANDIDATES](D1-PRUNE-CANDIDATES.md). |
| **Other 12 prune-candidate repos (0% progress in report)** | **~0** (revision trees) | Archiver estimates: remaining = full HF size → **no counted bytes** under revision dirs. **Exception:** whatever lived under **`d1/.tmp/<slug>/`** is **not** in the manifest; could be **0–many GiB** per repo until you `du` those paths (if already deleted, N/A). |
| **`MiniMaxAI/MiniMax-M2.7`** | **unknown** | 404 / no HF size in prune table; any local stub only. |
| **`meta-llama/Llama-4-Maverick-17B-128E` (base, purged)** | **~129.3** | Operator table: HF total **748.04** GiB, remaining **618.79** GiB → on-disk ≈ **129.25** GiB before purge. |
| **`meta-llama/Llama-4-Scout-17B-16E` (base, purged)** | **~202.4** | Manifest rows (since removed from TSV): **~202.391** GiB **per** revision row; count **one** tree if `latest` → SHA symlink (not double). |

**D1 subtotal (numeric, excluding MiniMax and `.tmp` unknowns):**  
120.92 + 129.25 + 202.39 ≈ **452.6 GiB** ≈ **0.44 TiB** binary.

**Upper bound caveat:** If any “0%” prune target actually held large partials without manifest credit, real freed space could exceed the **~453 GiB** subtotal. **`du -sh` on deleted paths** (or current `df` delta) is definitive.

---

## D2 — estimated freed

| Source | Est. freed | Basis |
|--------|------------|--------|
| **Dedupe stubs** | **≪ 1 GiB** | [`MODEL-DEDUPE-2026-04-05.md`](MODEL-DEDUPE-2026-04-05.md): `microsoft/Phi-4-mini-instruct`, `deepseek-ai/deepseek-coder-6.7b-instruct` stubs on d2; manifest shows **~0.006–0.009 GiB** per path. Llama-3.2-3B-Instruct on d2 was stub then filled from d3 — net d2 change is **not** a large delete. |

**D2 total:** round to **~0 GiB** for planning (tens of MiB class).

---

## D3 — estimated freed (dedupe / consolidation)

From [`MODEL-DEDUPE-2026-04-05.md`](MODEL-DEDUPE-2026-04-05.md) + manifest sizes (count **one** tree when `latest` duplicates SHA):

| Removal | Est. freed (GiB) | Notes |
|---------|------------------:|--------|
| `MiniMaxAI/MiniMax-M2.5` duplicate on d3 | **23.92** | TSV: d3 raw **23.920** (dedupe: “~24 GiB”). |
| `microsoft/Phi-4-mini-instruct` BF16 tree on d3 | **7.17** | TSV: **7.166** ×2 rows → one tree. |
| `meta-llama/Llama-3.2-3B-Instruct` tree on d3 | **11.98** | TSV: **11.979** ×2 rows → one tree. |
| Other stub paths in dedupe note | **&lt; 0.02** | specialist stubs ~MiB. |

**D3 total:** ≈ **43.1 GiB** binary.

---

## Summary table

| Drive | Estimated freed (GiB, binary) | Confidence |
|-------|------------------------------:|------------|
| **D1** | **~453** + `.tmp` unknown + MiniMax unknown | Medium (manifest + prune math); verify with `df` |
| **D2** | **~0** (≪ 1 GiB) | High |
| **D3** | **~43** | High (manifest-aligned dedupe) |

---

## Optional: catalog **C** and PAR2 ceiling (illustrative)

Pre-prune snapshot ([`PAR2-STORAGE-ESTIMATE-D1-D2-D3.md`](PAR2-STORAGE-ESTIMATE-D1-D2-D3.md)): **C** ≈ **8 872 / 5 023 / 4 924 GiB** on d1 / d2 / d3; **F** from `df` was **~21 / 178 / 74 GiB** (decimal GiB in that doc).

**Rough post-prune catalog deltas (binary GiB):**

- **D1:** 8 872 − **~453** ≈ **8 419 GiB** (only if no other large adds; regenerate TSV).
- **D2:** ~**5 023** (unchanged within rounding).
- **D3:** 4 924 − **~43** ≈ **4 881 GiB**.

**Rough D1 available space (order of magnitude):** if essentially all **~453 GiB** returns to **F** and old **F** ≈ 21 GiB binary-class, **F** could move toward **~470–500 GiB** — confirm with **`df -B1 /mnt/models/d1`**.

Revised uniform PAR2 ceiling \(r_{\max} \approx 100 \times F/C\) for **D1** (illustrative): **100 × 474 / 8419 ≈ 5.6%** vs the pre-prune **~0.24%** (uses **F ≈ 474 GiB**, **C ≈ 8419 GiB**; both approximate).

---

## Related

- [D1-PRUNE-CANDIDATES.md](D1-PRUNE-CANDIDATES.md) — prune list and `rm -rf` targets  
- [MODEL-DEDUPE-2026-04-05.md](MODEL-DEDUPE-2026-04-05.md) — cross-drive deletes  
- [PAR2-STORAGE-ESTIMATE-D1-D2-D3.md](PAR2-STORAGE-ESTIMATE-D1-D2-D3.md) — pre-prune **F** and **C**
