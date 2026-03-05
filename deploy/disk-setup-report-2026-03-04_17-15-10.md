# Disk Setup Report

| Field | Value |
|-------|-------|
| Host | a4kg3-artix-xfce |
| Run time | 2026-03-04 17:15:10 EST |
| Script | vm-mount-disks.sh |
| Mode | mount only |
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
| D1 | /dev/sda | /dev/sda1 | /mnt/models/d1 | none | NEEDS --force-format |
| D2 | /dev/sdd | /dev/sdd1 | /mnt/models/d2 | none | NEEDS --force-format |
| D3 | /dev/sde | /dev/sde1 | /mnt/models/d3 | none | NEEDS --force-format |
| D5 | /dev/sdc | /dev/sdc1 | /mnt/models/d5 | none | NEEDS --force-format |

> .tmp scratch: `/mnt/models/d1/.tmp` (~1.9 TB headroom on D1 post-downloads)

> **ABORTED** — partitions need formatting but --force-format not set.
