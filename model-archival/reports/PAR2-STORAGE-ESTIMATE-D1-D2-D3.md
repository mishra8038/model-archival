# PAR2 / parchive headroom on D1, D2, D3

**Snapshot:** 2026-04-05 (UTC) · **Host:** archive VM `a4kg3-artix-xfce` · **Mounts:** `/mnt/models/d1` … `d3`

This note estimates **what class of PAR2-style measures** (parity / recovery files alongside model weights) are realistic **using only current free space**, without deleting weights. It is **not** a PAR2 tutorial; numbers are **order-of-magnitude** for planning.

## How the estimate works

Tools such as **`par2create`** / **`par2cmdline`** generate recovery blocks whose total size depends on block size, file count, and the chosen redundancy (e.g. “10% recovery” is often **roughly ~10% of the protected payload** for large, uniform files—real overhead varies with block layout and small files).

Define:

- **F** = filesystem **available** space (bytes) on the drive.
- **C** = **catalogued** model weight total (bytes): sum of all revision trees included in [`MODEL-DISK-MANIFEST-2026-04-05.tsv`](MODEL-DISK-MANIFEST-2026-04-05.tsv) for that drive (only paths under `raw/`, `quantized/`, `uncensored/`, and `specialist/…`; excludes e.g. `d1/.tmp`, `d1/.quarantine`, `d5/supermicro` unless under those trees).

**Uniform ceiling (illustrative):**

\[
r_{\max} \approx 100 \times \frac{F}{C} \quad (\%)
\]

Interpretation: if recovery files were **linear** in redundancy and you wanted **one** parity plan covering **all** catalogued weights on that disk, **average** recovery percentage could not exceed \(r_{\max}\) without freeing space or moving parity elsewhere.

**Per-folder / per-model:** For a subtree of size **D** bytes, parity at nominal **p%** needs about **D × p/100** bytes of recovery files (simplified). That fits in **F** only if **D × p/100 ≤ F** (or you use only part of **F**).

## Measured inputs (snapshot)

| Drive | Available (**F**) | **F** (GiB, decimal) | Catalogued weights (**C**) | **C** (TiB, binary) | \(r_{\max}\) ≈ **100×F/C** |
|-------|---------------------|----------------------|----------------------------|---------------------|----------------------------|
| **D1** | 22 556 200 960 B | ~21.0 | ~8 872 GiB | ~8.66 | **~0.24%** |
| **D2** | 191 137 808 384 B | ~178 | ~5 023 GiB | ~4.91 | **~3.5%** |
| **D3** | 79 003 205 632 B | ~74 | ~4 924 GiB | ~4.81 | **~1.5%** |

**Source:** `df -B1` on the VM and sums from the same manifest used in [`MODEL-DISK-MANIFEST-2026-04-05.md`](MODEL-DISK-MANIFEST-2026-04-05.md).

**Important:** **D1** is effectively **full** for practical purposes (≈100% use in `df`). The **~21 GiB** free must also cover **new downloads** (`d1/.tmp` scratch), metadata, and filesystem slack—**fleet-wide PAR2 on all D1 weights is not realistic** until space is reclaimed or parity is stored elsewhere.

## What you can implement in practice

### D1 — *very limited*

- **Whole-disk uniform parity:** **Under ~0.25%** equivalent—**not meaningful** for bit-rot / drive failure scenarios.
- **Targeted PAR2:** You could still protect **individual** large shards or a **small** high-value directory if **D × p/100 ≤ ~21 GiB** (e.g. ~210 GiB of payload at **~10%** nominal redundancy needs **~21 GiB** parity—right at the free-space edge, before any download scratch).
- **Recommendation:** Prefer **scrub/verify** (`archiver verify`, SHA sidecars), **off-disk parity** (e.g. parity files on **D2/D5** pointing at D1 sources), or **free space first** (trim `.tmp`, quarantine, duplicates).

### D2 — *modest uniform headroom*

- **Uniform ceiling ~3.5%** vs catalogued weights: enough for **light** whole-volume redundancy **if** you accept that parity competes with future downloads and layout churn.
- **Examples (simplified):**
  - **10%** nominal redundancy on **~1.8 TiB** of chosen payload → **~180 GiB** parity → **fits** in **~178 GiB** free **only** if payload is smaller or redundancy lower.
  - **5%** on **~3.6 TiB** → **~180 GiB** parity → borderline vs free space.

### D3 — *between D1 and D2*

- **Uniform ceiling ~1.5%** vs catalogued weights.
- **Per-collection PAR2** for **GGUF / specialist** subtrees is more realistic than “protect everything on D3 at 10%.”

## Operational patterns (recommended framing)

1. **Do not** assume PAR2 replaces **checksum manifests**; keep **manifest + `.sha256`** as the source of integrity truth.
2. **Store `.par2` on a different drive** when the source drive is full (D1 → D2/D5), and document paths in runbooks.
3. **Tune block size** to **large weight files** (multi‑GiB shards) to limit PAR2 file-count explosion.
4. **Re-run** this estimate after large deletes, sync jobs, or `.tmp` cleanups—**F** and **C** move quickly.

## Related artifacts

- [`MODEL-DISK-MANIFEST-2026-04-05.tsv`](MODEL-DISK-MANIFEST-2026-04-05.tsv) — per-revision sizes used for **C** per drive.
- **[PAR2-BACKFILL-D2-D3.md](PAR2-BACKFILL-D2-D3.md)** — operational script to create per-revision PAR2 on **D2/D3** and write **`PAR2-D2-D3-RUN-*.md`** reports.
