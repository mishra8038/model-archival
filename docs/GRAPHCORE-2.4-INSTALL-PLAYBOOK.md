# Graphcore 2.4 Install Playbook (C2 / Ubuntu 18.04)

This playbook is a step-by-step runbook for installing a legacy Poplar `2.4.x` stack side-by-side with the current `2.6.0` setup, with fast rollback and minimal risk.

## Scope and safety

- Target host: `asus-esc4000` (`x@192.168.8.32`)
- Hardware: Graphcore C2 (`1d95:0001`)
- Current baseline:
  - Kernel `5.4.0-150-generic`
  - Driver `ipu_driver 1.1.2`
  - Firmware `1.3.31`
  - SDK `2.6.0`
- Firmware flashing is intentionally blocked; this playbook does **not** use `icuflash`.

## Required artifact from Graphcore

Obtain the exact portal download command for Ubuntu 18.04 `2.4.x` bundle (ideally the SDK variant with Driver & Utilities `1.0.57`).

Expected filename style:

- `poplar_sdk-ubuntu_18_04-2.4.0-<build>.tar.gz`

## Phase 0: pre-flight capture

Run on server:

```bash
uname -r
/sbin/modinfo ipu_driver | sed -n 's/^version:[[:space:]]*//p' | head -n1
source /home/x/graphcore/poplar_sdk-ubuntu_18_04-2.6.0+1074-33d3efd05d/enable
gc-info -l
gc-info --device-id 0 -i | sed -n 's/^  firmware version: //p'
popc --version | head -n1
```

## Phase 1: download and unpack 2.4

### 1) Download (local machine or server)

If downloading on local machine:

```bash
wget -O "poplar_sdk-ubuntu_18_04-2.4.x.tar.gz" "<GRAPHCORE_PORTAL_URL>"
scp "poplar_sdk-ubuntu_18_04-2.4.x.tar.gz" asus-esc4000:/home/x/
```

If downloading directly on server:

```bash
wget -O "/home/x/poplar_sdk-ubuntu_18_04-2.4.x.tar.gz" "<GRAPHCORE_PORTAL_URL>"
```

### 2) Verify it is non-empty

```bash
ls -lh /home/x/poplar_sdk-ubuntu_18_04-2.4.x.tar.gz
```

### 3) Extract to side-by-side location

```bash
mkdir -p /home/x/graphcore
tar -xzf /home/x/poplar_sdk-ubuntu_18_04-2.4.x.tar.gz -C /home/x/graphcore
ls -la /home/x/graphcore | sed -n '/poplar_sdk-ubuntu_18_04-2.4/p'
```

## Phase 2: wire environment script

Find extracted directory name, then update:

- `/home/x/env-gc24.sh`

Set:

```bash
SDK_GC24="/home/x/graphcore/<EXACT_2.4_SDK_DIR>"
```

Validate:

```bash
/home/x/env-gc24.sh
```

## Phase 3: install 2.4 driver branch (1.0.57 era)

Inside extracted SDK, locate kernel module package dir (`gc_kernel-module-ubuntu_18_04-...`), then:

```bash
cd "/home/x/graphcore/<EXACT_2.4_SDK_DIR>/gc_kernel-module-ubuntu_18_04-*/pkg"
echo 'x' | sudo -S ./driver_load.sh
```

Verify:

```bash
/sbin/modinfo ipu_driver | sed -n '1,40p'
lsmod | sed -n '/ipu_driver/p'
ls -l /dev/ipu* 2>/dev/null || true
```

## Phase 4: validate stack end-to-end

```bash
source /home/x/env-gc24.sh
gc-info -l
gc-info --device-id 0 -i
popc --version
```

Run a minimal compile/run test:

```bash
source /home/x/env-gc24.sh
cd "/home/x/graphcore/<EXACT_2.4_SDK_DIR>/poplar-ubuntu_18_04-*/examples/adder_popc"
popc codelets.cpp -o codelets.gp
g++ -std=c++17 adder.cpp -lpoplar -o adder
./adder
```

Expected: valid output sums (similar to `10`, `65`) and no driver/runtime errors.

## Phase 5: update status docs

Update server status snapshot:

- `/home/x/graphcore/STATUS.md`

Include:

- exact 2.4 SDK path
- driver version after switch
- gc-info results
- example test result

## Rollback (fast)

If any regression appears:

1. Reload prior driver bundle from 2.6 SDK package path.
2. Use `/home/x/env-gc26.sh` for all sessions.
3. Re-run baseline checks and confirm prior behavior.

## Do not do in this playbook

- Do not run firmware updates.
- Do not remove the 2.6 SDK.
- Do not overwrite archives under `/home/x/graphcore/archive`.
