# Specialist folder move on VM

- Requested structure created where space allows: `/mnt/models/<drive>/specialist/{math,law,science,medicine,chemistry,reasoning,embeddings}`.
- Drive capacity blockers: `d1` and `d2` at 100% prevented creating full specialist trees and moving 8 repos there.
- Moves completed: 63 specialist repo folders moved into `specialist/<category>/<track>/<org>/<repo>` on `d3` and `d5`.
- Unmoved due space: 8 repos on `d1`/`d2` (RomboUltima-32B, deepseek-coder-6.7b-instruct x2, R1 distills, ChemDFM-v2.0-14B, Mistral-Small-24B-2501).
- Plan file on VM: `/home/x/dev/model-archival/gdrive-archival/logs/specialist-move-plan.json`.
