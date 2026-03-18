# BOM Gaps And Required Additions

This note consolidates the single-stack BOM proposal with the broader multi-epoch archive strategy.

## What Claude's BOM gets right

- It treats the stack as a bill of materials instead of a vague install guide.
- It explicitly includes OS, driver, CUDA, application projects, wheel sources, and physical archive methods.
- It correctly emphasizes checksums, saved container images, and offline wheel downloads.
- It names a practical Ubuntu 24.04 + driver 570 + CUDA 12.8 forward stack.

## What is still missing for a resilient archive

### 1. Older recovery environments

The BOM only defines a single Ubuntu 24.04 / CUDA 12.8 stack.

To hedge against ecosystem rot and compatibility regressions, also archive these older anchors:

- Ubuntu 18.04 + CUDA 10.2
- Ubuntu 20.04 + CUDA 11.3
- Ubuntu 20.04 or 22.04 + CUDA 11.8
- Ubuntu 22.04 + CUDA 12.1
- Ubuntu 24.04 + CUDA 12.4 and 12.8

### 2. Exact artifact closures, not just top-level package names

For each stack, the archive needs exact downloadable artifacts, not only references to package names or web pages.

Required examples:

- Exact Ubuntu ISO filename plus official checksum file.
- Exact driver installer filename or complete `.deb` dependency tree.
- Exact CUDA installer filename for both runfile and local repo forms when available.
- Exact cuDNN, NCCL, and TensorRT archive filenames.
- Exact container image digest rather than a floating tag.
- Exact wheel filenames per Python version and platform.

### 3. Compiler and libc assumptions

Older CUDA stacks are sensitive to compiler and glibc versions.

The BOM should capture:

- Required GCC/G++ major versions per epoch.
- Whether the epoch expects the distro default compiler or a side-installed version.
- Any known kernel or glibc constraints.
- Whether a containerized build is acceptable or a matching host OS is required.

### 4. Python environment anchors

The BOM mentions PyTorch and transformers but not the full reproducible Python layer.

Add:

- Python source tarballs for `3.8`, `3.9`, `3.10`, `3.11`, and `3.12`.
- `pip`, `setuptools`, and `wheel` bootstrap artifacts.
- One offline requirements file per epoch.
- Wheelhouse plus source archive for native-extension packages such as `xformers`, `bitsandbytes`, `flash-attn`, `vllm`, and `tokenizers`.

### 5. Additional useful software families

To make this a true self-hosted LLM archive rather than just one serving path, include:

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

Legacy-worth-keeping:

- `fairseq`
- `apex`
- `deepspeed`
- `OpenNMT`
- `ESPnet`
- `Kaldi`

### 6. Source preservation strategy

For the open source projects in the BOM, the archive should keep both:

- a git mirror for full history and tags
- a tagged source tarball or release archive for easy offline use

This matters because release pages, tags, or package registries can disappear independently.

### 7. Licensing and authentication caveats

Some parts of the NVIDIA stack are not anonymously downloadable.

The archive plan should explicitly record:

- which artifacts require NVIDIA developer login
- whether redistribution is restricted
- whether only checksums/metadata can be stored for some components
- any manual login steps required to refresh the archive

Most likely friction points:

- cuDNN
- TensorRT
- some NVIDIA SDK-adjacent downloads

### 8. APT closure and offline reinstall support

For Debian/Ubuntu packages, it is not enough to store one top-level `.deb`.

The archive needs one of:

- the full dependency closure for pinned packages
- a local apt repo snapshot
- a documented list of exact package versions plus downloaded binaries

This especially applies to:

- NVIDIA driver packages
- Docker CE
- NVIDIA Container Toolkit
- build-essential toolchains

### 9. Verification and recovery documentation

The archive should define how to prove that an epoch is usable after restoration.

Required docs:

- rebuild instructions from bare Ubuntu install
- offline install steps
- environment variables and runtime flags
- one smoke test per major runtime path

Suggested smoke tests:

- `llama.cpp` CUDA build and single prompt run
- `ollama` model load and API query
- `vLLM` server start and one completion request
- `torch.cuda.is_available()`
- one `transformers` local load

## Recommendation

Keep Claude's Ubuntu 24.04 / CUDA 12.8 BOM as the forward stack, but place it inside a larger five-epoch archive plan.

That gives this project:

- one legacy CUDA 10.2 anchor
- one early CUDA 11 anchor
- one highly reusable CUDA 11.8 baseline
- one stable CUDA 12.1 baseline
- one forward Ubuntu 24.04 CUDA 12.4/12.8 stack

That is a much better hedge against future software disappearance than archiving only the newest stack.
