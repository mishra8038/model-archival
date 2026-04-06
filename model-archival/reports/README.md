# Reports

Operational snapshots and estimates generated for the archival fleet (archive VM disk inventory, parity planning, etc.).

| File | Description |
|------|-------------|
| [PAR2-STORAGE-ESTIMATE-D1-D2-D3.md](PAR2-STORAGE-ESTIMATE-D1-D2-D3.md) | Back-of-envelope PAR2 / parchive headroom on D1–D3 from free space vs catalogued weights. |
| [PAR2-BACKFILL-D2-D3.md](PAR2-BACKFILL-D2-D3.md) | Runbook: per-revision PAR2 on D2/D3; outputs `PAR2-D2-D3-RUN-*.md` / `.json`. |
| [MODEL-DISK-MANIFEST-2026-04-05.md](MODEL-DISK-MANIFEST-2026-04-05.md) | Narrative manifest, redundancy notes, and pointer to the TSV. |
| [MODEL-DISK-MANIFEST-2026-04-05.tsv](MODEL-DISK-MANIFEST-2026-04-05.tsv) | One row per revision tree: drive, layout category, HF repo id, revision, GiB, absolute path. |
| [FREED-SPACE-POST-PRUNE-2026-04-05.md](FREED-SPACE-POST-PRUNE-2026-04-05.md) | Recalculated **estimated** freed GiB on D1–D3 after documented prunes/dedupe (verify with `df` + fresh manifest). |
| [D1-FOCUSED-REMAINING-DOWNLOAD.md](D1-FOCUSED-REMAINING-DOWNLOAD.md) | **`registry-d1-manifest-incomplete.yaml`**: expected **~122.5 GiB** left to download (post-prune), plus scratch headroom notes. |

Regenerate the manifest after major layout changes by re-running the inventory script on the archive VM (see the methodology section in the manifest doc).
