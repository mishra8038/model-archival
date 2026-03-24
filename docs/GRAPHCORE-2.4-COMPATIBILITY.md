# Graphcore SDK 2.4.0 Compatibility Notes (C2 / Ubuntu 18.04)

This document captures the relevant compatibility details for evaluating a fallback from Poplar SDK `2.6.0` to the older `2.4.0` line on our C2 server.

## Why this exists

- We currently run:
  - C2 card (`1d95:0001`)
  - Ubuntu 18.04 host
  - Kernel `5.4.0-150-generic`
  - Driver `ipu_driver 1.1.2`
  - Firmware `1.3.31`
  - Poplar SDK `2.6.0`
- ICU firmware flashing (`icuflash`) was intentionally blocked for safety.
- We need a documented "legacy-compatible" stack target while waiting for gated legacy artifacts.

## 2.4.0 matrix extracted from Graphcore release notes

Source: `https://docs.graphcore.ai/projects/release-notes/en/2.4.0/release-notes.html`

- **Package contents (Ubuntu 18.04):**
  - Driver & Utilities: `1.0.57`
  - PopART: `2.4.0+2529`
  - PopTorch: `2.4.0+40669`
  - Poplar: `2.4.0+2151`
  - PopDist/PopRun: `2.4.0+2151`
  - TensorFlow: Graphcore TF `2.4.0`
- **IPU PCIe hardware support level:**
  - Model: `C2 300-0004`
  - ICU firmware version: `1.4.14`
  - Driver version: `1.0.57`
  - Support level: `Deprecated`

## Docker tags and stack references for 2.4.0

Source: `https://docs.graphcore.ai/projects/poplar-docker/en/2.4.0/user_guide.html`

- Poplar image tags include:
  - `graphcore/poplar:2.4.0`
  - `graphcore/poplar:2.4.0-ubuntu-bionic-20210723`
- TensorFlow image tags include:
  - `graphcore/tensorflow:2-amd-2.4.0`
  - `graphcore/tensorflow:2-intel-2.4.0`
  - OS-specific variants ending with `-ubuntu-bionic-20210723`

## Assessment: will 2.4.0 help us?

Short answer: **likely yes for better stack alignment**, with caveats.

- The 2.4.0 line explicitly packages Driver & Utilities `1.0.57`, which is the legacy branch tied to C2 support documentation.
- The published C2 matrix for 2.4.0 references firmware `1.4.14`; we are currently on `1.3.31`.
- Even without upgrading firmware, moving from driver `1.1.2` (newer branch) to the older `1.0.57` branch is a reasonable compatibility experiment if we observe instability.
- This should be installed **side-by-side** with current `2.6.0`, then validated via:
  - `gc-info -l`
  - `gc-info --device-id 0 -i`
  - minimal Poplar compile/run test

## Action plan when gated artifact arrives

1. Download exact 2.4.0 Ubuntu 18.04 SDK artifact from Graphcore portal.
2. Install to `/home/x/graphcore/poplar_sdk-ubuntu_18_04-2.4.0...` (parallel install).
3. Wire `/home/x/env-gc24.sh` to actual install path.
4. Install/use its packaged driver branch (`1.0.57` era).
5. Re-run smoke tests and compare behavior with current 2.6 baseline.
