# Full Stack Archive

Software-only archival project for rebuilding self-hosted local AI environments without relying on live upstream package indexes.

Model artifacts are intentionally out of scope here because they are already archived elsewhere in this repository workflow.

## Goals

- Preserve rebuildable NVIDIA-backed local AI software stacks across multiple compatibility epochs.
- Archive low-level dependencies through high-level inference and UI tools.
- Prefer exact versions, checksums, source mirrors, and offline-installable artifacts over loose package names.
- Keep one manifest-driven layout so the stack can be reconstructed even if upstream sites or package repos disappear.

## Planned epoch coverage

- `E0`: Ubuntu 18.04 + CUDA 10.2 + legacy Pascal/Volta era software.
- `E1`: Ubuntu 20.04 + CUDA 11.3 + early Ampere bridge.
- `E2`: Ubuntu 20.04 or 22.04 + CUDA 11.8 + broad-safe modern baseline.
- `E3`: Ubuntu 22.04 + CUDA 12.1 + current mainline-stable stack.
- `E4`: Ubuntu 24.04 + CUDA 12.4/12.8 + forward-stable stack.

## What belongs in this archive

- Ubuntu server ISOs and official checksum files.
- NVIDIA drivers, CUDA installers, cuDNN, NCCL, TensorRT, container toolkit, and release notes.
- Compiler, linker, and language-toolchain anchors needed to rebuild older CUDA epochs.
- Offline wheelhouses for pinned Python environments.
- Git mirrors, source tarballs, and release metadata for important open source projects.
- Saved container images and image digests for known-good runtime stacks.
- Checksums, manifests, and rebuild notes.

## Physical archive layout

```text
/mnt/models/d5/full-stack-archives/
  manifests/
    checksums/
    source/
  indexes/
  os/
    ubuntu-18.04.6/
    ubuntu-20.04.6/
    ubuntu-22.04.4/
    ubuntu-24.04.1/
    ubuntu-24.04.2/
  nvidia/
    drivers/
      440/
      450/
      470/
      525/
      535/
      550/
      570/
    cuda/
      10.2/
      11.3/
      11.8/
      12.1/
      12.4/
      12.8/
    cudnn/
    nccl/
    tensorrt/
  compilers/
    gcc/
    cpp/
    go/
    java/
    rust/
  python/
    3.8/
    3.9/
    3.10/
    3.11/
    3.12/
  wheels/
  sdists/
  packages/
    debs/
    rpms/
    arch/
  repos/
  source-archives/
  containers/
  docs/
    compatibility/
    rebuild-guides/
  logs/
  state/
```

## Project files

The manifest and helper code live in the repository under `full-stack/`.

Per-epoch wheel requirements live under `full-stack/requirements/`.

## Current readiness

- The direct-download archive is manifest-driven, resumable, and safe to rerun; completed files are skipped and partial files resume.
- The project currently automates direct artifacts, wheelhouse downloads, checksum refresh, and package-plan export.
- The current direct-download wave covers Ubuntu ISOs, Python sources, NVIDIA driver artifacts, container/orchestration binaries, and cross-language toolchains for Java, Go, Rust, and C++ build chains.
- Package-closure mirroring for `deb`/`rpm`/Arch and full git/container-image mirroring are still expansion phases; the catalog and package plans are in place, but those fetchers are not yet fully automated.

## Notes

- Treat this as an artifact catalog, not a one-shot installer.
- Capture both direct binaries and the metadata needed to trust them: source URL, version, release notes, checksum, and any auth/licensing caveats.
- For fragile packages such as `xformers`, `bitsandbytes`, `flash-attn`, and `vllm`, archive wheel plus source plus git mirror.
- `BOM.md` is the merged bill of materials that combines the forward Ubuntu 24.04 stack with the broader multi-epoch archive plan.
- `compatibility-matrix.yaml` tracks version-sensitive projects by OS, GCC, Python, CUDA, and Torch epochs.
- `projects.yaml` is the expansive archive catalog, including desired source releases plus `deb`, `rpm`, and Arch package forms.
- `download-manifest.yaml` pins the first direct-download batches: Ubuntu ISOs, Python source tarballs and signatures, cross-language toolchains, NVIDIA driver branches, and container/orchestration artifacts.
- The default physical destination for the archive payload is `/mnt/models/d5/full-stack-archives`.
- The archive output includes an epoch-centered software matrix at `indexes/epoch-software-matrix.md` and `docs/compatibility/epoch-software-matrix.md`.
- The downloader writes a local checksum ledger to `manifests/checksums/local-sha256sums.txt` and keeps per-file metadata in `state/download-state.json`.
- `export-package-plans` emits per-epoch Debian/RPM/Arch package lists under `packages/`.

## CLI

Use the local helper to scaffold the archive onto D5:

```bash
uv run --project full-stack full-stack-archive summary
uv run --project full-stack full-stack-archive bootstrap-d5
uv run --project full-stack full-stack-archive download-direct --group language-toolchains
uv run --project full-stack full-stack-archive download-direct --group container-orchestration
uv run --project full-stack full-stack-archive download-wheelhouse --epoch E3 --epoch E4
uv run --project full-stack full-stack-archive export-package-plans
uv run --project full-stack full-stack-archive refresh-checksums
bash full-stack/scripts/download-initial.sh
```

For a clean "next wave" restart from the latest manifests, rerun the direct-download helper and then restart the wheelhouse passes:

```bash
bash full-stack/scripts/download-initial.sh
uv run --project full-stack full-stack-archive download-wheelhouse --epoch E3 --epoch E4
```
