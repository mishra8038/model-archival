# Agent change log

Entries added by Cursor agent; commit this file with the related code changes.

## 2026-03-16 (run.sh unbound SKIP_DRIVE_SPACE_CHECK)

- **Summary**: Fix unbound variable in run.sh when --skip-drive-space-check is not passed: use ${SKIP_DRIVE_SPACE_CHECK:-} so script does not exit under set -u.
- **Files**: local/scripts/run.sh.

## 2026-03-15 (base-first priority policy)

- **Summary**: Adopt base-first priority policy going forward (1=base, 2=smallest GGUF, 3=instruct, 4=middle quants); document in rules; allow priority 3 and 4 in preflight/CLI. No deletion of already-downloaded models.
- **Files**: .cursor/rules/model-archival-project.mdc, .cursor/rules/archiver-codebase.mdc, local/src/archiver/preflight.py, local/src/archiver/cli.py, local/src/archiver/scheduler.py, local/src/archiver/models.py.

## 2026-03-15 (non-obsolete flagship models)

- **Summary**: Add missing non-obsolete flagship models to registry at lowest priority (Falcon 40B/180B, MPT 7B/30B, Llama 3.2-1B, SmolLM2, IBM Granite 20B).
- **Files**: local/config/registry.yaml.

## 2026-03-15 (GDrive verify + upload log)

- **Summary**: GDrive backup: verify each model dir (manifest/sidecar checksums) before upload; record successfully uploaded models to logs/uploaded.log.
- **Files**: gdrive-archival/backup.py.

## 2026-03-15 (MCP code archive)

- **Summary**: Add MCP servers code archive: registry, README, archive script, FastMCP starter example.
- **Files**: code-archival/registry-mcp.yaml, code-archival/README-mcp.md, code-archival/archive-mcp.sh, code-archival/examples/fastmcp-starter/server.py, code-archival/examples/fastmcp-starter/README.md, code-archival/examples/fastmcp-starter/pyproject.toml.

## 2026-03-15 (Nemotron 3 Super + Ultra, tier D priority 4)

- **Summary**: Add Nemotron 3 Super 120B-A12B (base, instruct, FP8, NVFP4) and Nemotron Ultra 253B at tier D, priority 4, d1; lowest priority.
- **Files**: local/config/registry.yaml.

## 2026-03-15 (Diffusion coding models: CoDA + DiffuCoder)

- **Summary**: Add Salesforce CoDA (1.7B base/instruct) and Apple DiffuCoder (7B base/instruct/cpGRPO) diffusion code models at tier G, priority 4 on d3 as research/experimental coding models.
- **Files**: local/config/registry.yaml.

## 2026-03-15 (Nemotron 3 Nano + NemoClaw)

- **Summary**: Add Nemotron 3 Nano 30B-A3B (base BF16, instruct BF16, NVFP4, FP8) to registry; notes reference NemoClaw agent platform (model-only; NemoClaw code not on HF).
- **Files**: local/config/registry.yaml.

## 2026-03-16 (Llama 4 + Guard/Prompt Guard)

- **Summary**: Add Llama 4 Scout/Maverick base and instruct checkpoints plus Llama Guard 4 and Llama Prompt Guard 2 safety models to the registry with appropriate tiers, drives, and priorities.
- **Files**: local/config/registry.yaml.

## 2026-03-15 (OS & Windows MCP servers)

- **Summary**: Add OS/Windows MCP servers and Linux/Windows skills doc; extend MCP and skills registries.
- **Files**: code-archival/registry-mcp.yaml (OS & Windows section), code-archival/README-mcp-os.md, code-archival/registry-skills.yaml (majiayu000, hao-cyber), code-archival/README-mcp.md (see-also link).

## 2026-03-17 (Docs: progress and end-state vision)

- **Summary**: Expand top-level documentation with a concise summary of what the archival project has already achieved (frontier weights, uncensored variants, research models, resilient downloader, status/reporting, checksum and code archival, GDrive backup path) and the end-state vision for coverage, integrity, operations, historical record, and storage safety.
- **Files**: docs/README.md.

## 2026-03-17 (Registry: move 404/legacy models out of default)

- **Summary**: Move clearly unavailable or non-default models (CohereForAI/c4ai-command-r-plus and NovaSky-Berkeley/Sky-T1-32B-Preview) from the active registry into the legacy registry so they no longer cause repeated failures in default runs while remaining documented for historical reference.
- **Files**: local/config/registry.yaml, local/config/registry-legacy.yaml.

## 2026-03-17 (Registry: add Leanstral code/proof agent)

- **Summary**: Add Mistral Leanstral 120B-A6B sparse Lean 4 code/proof agent to the main registry as a Tier E research/reasoning model with high preservation priority.
- **Files**: local/config/registry.yaml.

## 2026-03-18 00:02

- **Summary**: Add a local-time bandwidth schedule so archiver runs cap total download speed to 6 MB/s from 14:00 to 01:00 and stay unlimited outside that window; apply the same schedule through `run.sh`.
- **Files**: local/src/archiver/cli.py, local/src/archiver/aria2_manager.py, local/scripts/run.sh.

## 2026-03-18 03:30

- **Summary**: Add a live priority override to promote `meta-llama/Llama-3.1-405B` ahead of instruct variants and de-prioritize the current instruct queue.
- **Files**: /mnt/models/d5/priority_overrides.json.

## 2026-03-18 03:33

- **Summary**: Expand the live priority overrides so unfinished base models and smaller models are preferred, while large unfinished instruct and giant models are strongly de-prioritized; keep `meta-llama/Llama-3.1-405B` first.
- **Files**: /mnt/models/d5/priority_overrides.json.

## 2026-03-18 03:38

- **Summary**: Force-stop the current archiver run and restart it after refining the live priority overrides to favor `meta-llama/Llama-3.1-405B` and smaller unfinished models while pushing unfinished large models down.
- **Files**: /mnt/models/d5/priority_overrides.json, see process restart in terminal state.

## 2026-03-18 13:06

- **Summary**: Create a new `full-stack` planning area with a multi-epoch NVIDIA local-AI software archive manifest and BOM gap analysis, including Ubuntu 18.04 and 20.04 anchors.
- **Files**: full-stack/README.md, full-stack/epochs.yaml, full-stack/BOM-GAPS.md.

## 2026-03-18 13:08

- **Summary**: Merge the forward Ubuntu 24.04/CUDA 12.8 BOM into the broader `full-stack` archive plan by adding a consolidated software BOM document and enriching the `E4` epoch with concrete driver, CUDA, and application pins.
- **Files**: full-stack/README.md, full-stack/epochs.yaml, full-stack/BOM.md.

## 2026-03-18 13:08

- **Summary**: Build out the `full-stack` project with a compatibility matrix, an expansive project/package catalog covering source releases plus deb/rpm/Arch package forms, and a helper CLI that bootstraps the archive layout and index files onto D5.
- **Files**: full-stack/compatibility-matrix.yaml, full-stack/projects.yaml, full-stack/pyproject.toml, full-stack/src/full_stack_archive/__init__.py, full-stack/src/full_stack_archive/cli.py, full-stack/README.md, /mnt/models/d5/full-stack-archive (bootstrapped output).

## 2026-03-18 13:22

- **Summary**: Move the physical archive target to `/mnt/models/d5/full-stack-archives`, reshape it to match the earlier archive tree, and add an epoch-centered software matrix that lists required software for each epoch.
- **Files**: full-stack/compatibility-matrix.yaml, full-stack/projects.yaml, full-stack/src/full_stack_archive/cli.py, full-stack/README.md, /mnt/models/d5/full-stack-archives.

## 2026-03-18 13:33

- **Summary**: Add compatible Docker, Podman, containerd/nerdctl, and Kubernetes/k3s release tracks to the full-stack compatibility matrix and project catalog, then regenerate the D5 archive indexes.
- **Files**: full-stack/compatibility-matrix.yaml, full-stack/projects.yaml, /mnt/models/d5/full-stack-archives.

## 2026-03-18 17:13

- **Summary**: Build out resumable full-stack download infrastructure: add a pinned direct-download manifest and launcher, container/orchestration artifacts, per-epoch wheelhouse requirements and wheel download command, exported Debian/RPM/Arch package plans, and restart D5 archival downloads with optional metadata sidecars handled safely.
- **Files**: full-stack/download-manifest.yaml, full-stack/scripts/download-initial.sh, full-stack/requirements/requirements-e0-cu102-py38.txt, full-stack/requirements/requirements-e1-cu113-py39.txt, full-stack/requirements/requirements-e2-cu118-py310.txt, full-stack/requirements/requirements-e3-cu121-py311.txt, full-stack/requirements/requirements-e4-cu124-py311.txt, full-stack/requirements/requirements-e4-cu128-py312.txt, full-stack/src/full_stack_archive/cli.py, full-stack/README.md, /mnt/models/d5/full-stack-archives.

## 2026-03-18 18:26

- **Summary**: Extend the full-stack archive with Java, Go, Rust, and C++ toolchains, add direct-download bundles for those ecosystems, and fold the new language toolchains into the initial archive wave.
- **Files**: full-stack/projects.yaml, full-stack/compatibility-matrix.yaml, full-stack/download-manifest.yaml, full-stack/README.md, full-stack/scripts/download-initial.sh.

## 2026-03-18 18:30

- **Summary**: Tighten the full-stack archive's coherence by bootstrapping the new toolchain directories and mirrored index docs, expanding epoch metadata for cross-language toolchains, and documenting the current automation scope plus restart path.
- **Files**: full-stack/src/full_stack_archive/cli.py, full-stack/epochs.yaml, full-stack/README.md.

## 2026-03-18 13:36

- **Summary**: Move unfinished D2-scheduled models onto D3 and retune live priority overrides to favor self-hostable small models plus the selected 405B and tensorblock downloads while parking Scout, Maverick, and Llama-3.3-70B-Instruct for later.
- **Files**: local/config/registry.yaml, /mnt/models/d5/priority_overrides.json.

## 2026-03-18 19:30

- **Summary**: Add a serial queue mode and make `run.sh` default to a strict 6 Mbps cap (`0.75 MB/s`) so downloads stay neighbor-friendly unless explicitly overridden.
- **Files**: local/src/archiver/cli.py, local/src/archiver/scheduler.py, local/scripts/run.sh, local/scripts/archiver-download.sh, local/README.md, local/docs/OPERATIONS.md, local/docs/ARCHITECTURE.md.

## 2026-03-18 20:22

- **Summary**: Add the same neighbor-friendly defaults to the full-stack direct downloader: `6 Mbps` cap (`0.75 MB/s`) and serial queue mode in the CLI and initial download script.
- **Files**: full-stack/src/full_stack_archive/cli.py, full-stack/scripts/download-initial.sh, full-stack/README.md.
