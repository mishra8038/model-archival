# Full-Stack Software BOM

Manifest version `1.0`  
Archive date `2026-03-18`

This file merges the forward Ubuntu 24.04 BOM with the broader multi-epoch archival plan.

## Purpose

Use this project as a software seed vault for self-hosted NVIDIA local AI systems.

The goal is not just to pin one working machine, but to preserve enough low-level and high-level software to rebuild usable stacks across multiple CUDA generations even if package indexes, release pages, or installers disappear.

## Epoch Matrix

| Epoch | Role | Ubuntu | Driver | CUDA | Python | PyTorch |
|---|---|---|---|---|---|---|
| `E0` | legacy-deep | `18.04.6` | `440/450` | `10.2` | `3.8` | `1.12.1 cu102` |
| `E1` | early-11 bridge | `20.04.6` | `470` | `11.3` | `3.8/3.9` | `1.13.1 cu113` |
| `E2` | broad-safe | `20.04.6` or `22.04.4` | `525` | `11.8` | `3.10` | `2.1.2 cu118` |
| `E3` | mainline-stable | `22.04.4` | `535` | `12.1` | `3.10/3.11` | `2.2.1 cu121` |
| `E4` | forward-stable | `24.04.2` | `570.86.16` preferred, `550` alternate | `12.8.0` preferred, `12.4` alternate | `3.11/3.12` | `2.6.0+cu128` and `2.5.1 cu124` |

## Forward Stack From Claude, Integrated

This is the newest concrete stack and should be preserved as the `E4` forward reference environment.

### OS base image

| Component | Pinned version | Artifact / source | Notes |
|---|---|---|---|
| Ubuntu Server | `24.04.2 LTS` | `ubuntu-24.04.2-live-server-amd64.iso` | Kernel `6.8.x`, Python `3.12` default |

### NVIDIA and CUDA chain

| Component | Pinned version | Artifact / source | Notes |
|---|---|---|---|
| NVIDIA driver | `570.86.16` | NVIDIA Linux x86_64 archive, or full Ubuntu `.deb` closure | Supports CUDA up to `12.8` |
| CUDA Toolkit | `12.8.0` | `cuda_12.8.0_570.86.10_linux.run` and local repo artifacts | Archive both runfile and repo package forms if available |
| cuDNN | `9.7.1` | NVIDIA developer download | Requires login; record auth caveat |
| cuBLAS | `12.8.x` | Bundled with CUDA | Preserve via CUDA archive |
| NVIDIA Container Toolkit | `1.17.x` | GitHub releases and apt repo snapshot | Needed for Docker GPU containers |

### Application software

| Component | Version | Source | Notes |
|---|---|---|---|
| Docker CE | `27.x` | Docker Ubuntu repo and package closure | Save exact `.deb` tree |
| Ollama | `0.6.x` | `github.com/ollama/ollama` | Archive install script, tag, and source |
| llama.cpp | `b5000+` | `github.com/ggml-org/llama.cpp` | Keep specific commit SHA and source archive |
| vLLM | `0.7.x` | `github.com/vllm-project/vllm`, PyPI | Save wheel, sdist, and git mirror |
| PyTorch | `2.6.0+cu128` | `download.pytorch.org/whl/cu128` | Also keep `2.5.1 cu124` as fallback |
| transformers | `4.50.x` | `github.com/huggingface/transformers`, PyPI | Archive wheel and source |
| Open WebUI | `0.5.x` | `github.com/open-webui/open-webui`, `ghcr.io` | Pin container by digest |
| AnythingLLM | `1.7.x` | `github.com/Mintplex-Labs/anything-llm` | Pin tag plus container image if used |

## Archive Scope

### Low level

- Ubuntu ISO images, checksums, and release notes
- NVIDIA driver installers or exact Ubuntu package closures
- CUDA toolkit installers and local repo packages
- cuDNN, NCCL, TensorRT, and NVIDIA Container Toolkit
- GCC/G++ toolchains and Python source tarballs

### Python runtime

- Offline wheelhouses for each epoch
- `pip`, `setuptools`, and `wheel` bootstrap artifacts
- sdists for native-extension packages likely to break later

### Inference and serving

- `llama.cpp`
- `llama-cpp-python`
- `Ollama`
- `vLLM`
- `SGLang`
- `TensorRT-LLM`
- `text-generation-inference`
- `text-generation-webui`
- `koboldcpp`
- `tabbyAPI`
- `LiteLLM`
- `AutoGPTQ`
- `exllamav2`
- `flash-attn`
- `xformers`
- `bitsandbytes`

### UI and orchestration

- `Open WebUI`
- `AnythingLLM`
- `docker compose` or equivalent launch configs
- saved container images by digest

### Legacy and research

- `fairseq`
- `apex`
- `deepspeed`
- `OpenNMT`
- `ESPnet`
- `Kaldi`

## Physical Archive Policy

For every important component, try to preserve all of:

- direct binary artifact
- checksum
- source URL
- release notes
- license note
- source tarball
- git mirror where applicable

For packages installed through apt, preserve one of:

- a complete `.deb` dependency closure
- a local apt snapshot
- or a documented exact package list plus downloaded binaries

## Fragile Packages Requiring Extra Care

Archive wheel plus sdist plus git mirror for:

- `vllm`
- `flash-attn`
- `xformers`
- `bitsandbytes`
- `tokenizers`
- `TensorRT-LLM`

These are the packages most likely to become difficult to rebuild once upstream binary compatibility shifts.

## Verification And Recovery

Each epoch should eventually have:

- a rebuild guide from bare Ubuntu install
- an offline install path
- smoke tests
- known-good environment variables and runtime flags

Suggested smoke tests:

- `torch.cuda.is_available()`
- one local `transformers` load
- one `llama.cpp` CUDA run
- one `ollama` API request
- one `vllm` server start and completion request

## Bottom Line

Claude's BOM is now the forward `E4` slice of a larger five-epoch software archive. The combined plan preserves:

- one deep-legacy CUDA 10.2 anchor
- one early CUDA 11 bridge
- one broadly useful CUDA 11.8 baseline
- one stable CUDA 12.1 baseline
- one forward Ubuntu 24.04 CUDA 12.4/12.8 stack

That is a stronger hedge than preserving only the newest installer set.
