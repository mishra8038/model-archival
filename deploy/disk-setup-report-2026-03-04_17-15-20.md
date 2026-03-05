# Disk Setup Report

| Field | Value |
|-------|-------|
| Host | a4kg3-artix-xfce |
| Run time | 2026-03-04 17:15:20 EST |
| Script | vm-mount-disks.sh |
| Mode | --force-format |
| Dry run | false |

---

## Disk Discovery

| Device | Size | GiB | Model | Serial | Root? |
|--------|------|-----|-------|--------|-------|
| /dev/sda |  5.5T | 5589 | QEMU HARDDISK | drive-scsi1 | no |
| /dev/sdb |  256G | 256 | QEMU HARDDISK | drive-scsi0 | ← ROOT (skip) |
| /dev/sdc | 931.5G | 931 | QEMU HARDDISK | drive-scsi2 | no |
| /dev/sdd |  2.7T | 2794 | QEMU HARDDISK | drive-scsi3 | no |
| /dev/sde |  2.7T | 2794 | QEMU HARDDISK | drive-scsi4 | no |

## Drive Assignment

  ⚠   /dev/sda  5589 GiB  → D1 [capacity fallback — serial not matched]
  ⚠   /dev/sdc  931 GiB  → D5 [capacity fallback]
  ⚠   /dev/sdd  2794 GiB  → 3 TB pool [capacity fallback]
  ⚠   /dev/sde  2794 GiB  → 3 TB pool [capacity fallback]
  ⚠   /dev/sdd → D2 [capacity fallback]
  ⚠   /dev/sde → D3 [capacity fallback]

## Proposed Mount Plan

| Role | Disk | Partition | Mount Point | Current FS | Action |
|------|------|-----------|-------------|------------|--------|
| D1 | /dev/sda | /dev/sda1 | /mnt/models/d1 | none | FORMAT ext4 + mount |
| D2 | /dev/sdd | /dev/sdd1 | /mnt/models/d2 | none | FORMAT ext4 + mount |
| D3 | /dev/sde | /dev/sde1 | /mnt/models/d3 | none | FORMAT ext4 + mount |
| D5 | /dev/sdc | /dev/sdc1 | /mnt/models/d5 | none | FORMAT ext4 + mount |

> .tmp scratch: `/mnt/models/d1/.tmp` (~1.9 TB headroom on D1 post-downloads)

> User confirmed: **YES** — proceeding.

## Wipe / Partition / Format


### /dev/sda — D1 — 6TB raw giants ( 5.5T)

  **Format ext4**
  - Partition: /dev/sda1
  - Label: models-d1
  - Reserved blocks: 1%
  - ✔ ext4 formatted — UUID: b5eb9174-b438-40b3-b26b-046cd44cb296
  - UUID: `b5eb9174-b438-40b3-b26b-046cd44cb296`
  - Status: ✔ formatted

### /dev/sdc — D5 — 1TB archive/logs (931.5G)

  **Format ext4**
  - Partition: /dev/sdc1
  - Label: models-d5
  - Reserved blocks: 1%
  - ✔ ext4 formatted — UUID: b31ca1c3-a6b2-4862-b7a8-ee7ad6227324
  - UUID: `b31ca1c3-a6b2-4862-b7a8-ee7ad6227324`
  - Status: ✔ formatted

### /dev/sdd — D2 — 3TB raw mid-size ( 2.7T)

  **Format ext4**
  - Partition: /dev/sdd1
  - Label: models-d2
  - Reserved blocks: 1%
  - ✔ ext4 formatted — UUID: 62a732fb-3c90-42e8-8ee2-e138a1444747
  - UUID: `62a732fb-3c90-42e8-8ee2-e138a1444747`
  - Status: ✔ formatted

### /dev/sde — D3 — 3TB GGUF quants ( 2.7T)

  **Format ext4**
  - Partition: /dev/sde1
  - Label: models-d3
  - Reserved blocks: 1%
  - ✔ ext4 formatted — UUID: 47bf0892-fe9c-4e19-a9c9-37bd93f9c4d2
  - UUID: `47bf0892-fe9c-4e19-a9c9-37bd93f9c4d2`
  - Status: ✔ formatted

## Mounting

| Partition | Mount Point | Result |
|-----------|-------------|--------|
  ✓   Mounting /dev/sda1 → /mnt/models/d1
  - ✔   Mounted
| /dev/sda1 | /mnt/models/d1 | ✔ mounted |
  ✓   Mounting /dev/sdd1 → /mnt/models/d2
  - ✔   Mounted
| /dev/sdd1 | /mnt/models/d2 | ✔ mounted |
  ✓   Mounting /dev/sde1 → /mnt/models/d3
  - ✔   Mounted
| /dev/sde1 | /mnt/models/d3 | ✔ mounted |
  ✓   Mounting /dev/sdc1 → /mnt/models/d5
  - ✔   Mounted
| /dev/sdc1 | /mnt/models/d5 | ✔ mounted |

## Directory Structure

**D1** — raw model storage + .tmp scratch:
  - ✔   /mnt/models/d1/raw/.keep
  - `/mnt/models/d1/raw/.keep`
  - ✔   /mnt/models/d1/.tmp
  - `/mnt/models/d1/.tmp`
**D2** — raw mid-size + uncensored:
  - ✔   /mnt/models/d2/raw/.keep
  - `/mnt/models/d2/raw/.keep`
  - ✔   /mnt/models/d2/uncensored/.keep
  - `/mnt/models/d2/uncensored/.keep`
**D3** — GGUF quantized:
  - ✔   /mnt/models/d3/quantized/.keep
  - `/mnt/models/d3/quantized/.keep`
**D5** — archive + logs:
  - ✔   /mnt/models/d5/archive/checksums
  - `/mnt/models/d5/archive/checksums`
  - ✔   /mnt/models/d5/archive/manifests
  - `/mnt/models/d5/archive/manifests`
  - ✔   /mnt/models/d5/logs
  - `/mnt/models/d5/logs`

## /etc/fstab

| Mount Point | UUID | Entry added? |
|-------------|------|--------------|
  ✓   Adding /mnt/models/d1 → UUID=b5eb9174-b438-40b3-b26b-046cd44cb296
  - ✔   Written
| /mnt/models/d1 | `b5eb9174-b438-40b3-b26b-046cd44cb296` | ✔ added |
  ✓   Adding /mnt/models/d2 → UUID=62a732fb-3c90-42e8-8ee2-e138a1444747
  - ✔   Written
| /mnt/models/d2 | `62a732fb-3c90-42e8-8ee2-e138a1444747` | ✔ added |
  ✓   Adding /mnt/models/d3 → UUID=47bf0892-fe9c-4e19-a9c9-37bd93f9c4d2
  - ✔   Written
| /mnt/models/d3 | `47bf0892-fe9c-4e19-a9c9-37bd93f9c4d2` | ✔ added |
  ✓   Adding /mnt/models/d5 → UUID=b31ca1c3-a6b2-4862-b7a8-ee7ad6227324
  - ✔   Written
| /mnt/models/d5 | `b31ca1c3-a6b2-4862-b7a8-ee7ad6227324` | ✔ added |

## Mount Verification

| Mount Point | Size | Used | Free | Use% |
|-------------|------|------|------|------|
| /mnt/models/d1 | 5.5T | 2.1M | 5.4T | 1% |
| /mnt/models/d5 | 916G | 2.1M | 907G | 1% |
| /mnt/models/d2 | 2.7T | 2.1M | 2.7T | 1% |
| /mnt/models/d3 | 2.7T | 2.1M | 2.7T | 1% |

---

## Final Summary

| Role | Disk | Partition | Mount | UUID |
|------|------|-----------|-------|------|
| D1 | /dev/sda | /dev/sda1 | /mnt/models/d1 | `b5eb9174-b438-40b3-b26b-046cd44cb296` |
| D2 | /dev/sdd | /dev/sdd1 | /mnt/models/d2 | `62a732fb-3c90-42e8-8ee2-e138a1444747` |
| D3 | /dev/sde | /dev/sde1 | /mnt/models/d3 | `47bf0892-fe9c-4e19-a9c9-37bd93f9c4d2` |
| D5 | /dev/sdc | /dev/sdc1 | /mnt/models/d5 | `b31ca1c3-a6b2-4862-b7a8-ee7ad6227324` |

Completed: 2026-03-04 17:36:50 EST
