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
