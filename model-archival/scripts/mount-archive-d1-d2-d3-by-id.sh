#!/usr/bin/env bash
# Mount archive VM data disks (models-d1 / d2 / d3) by stable ATA id under /mnt/d1–d3.
#
# Run (interactive terminal): sudo /path/to/mount-archive-d1-d2-d3-by-id.sh
#
# Passwordless sudo for Cursor/agent shells (optional, tight rule — adjust username):
#   sudo visudo -f /etc/sudoers.d/model-archival-mount-d123
#   ---
#   x ALL=(root) NOPASSWD: /home/x/z/dev/model-archival/model-archival/model-archival/scripts/mount-archive-d1-d2-d3-by-id.sh
#   ---
#   (Path must match this file exactly; use `realpath` on this script if unsure.)
set -euo pipefail

D1=/dev/disk/by-id/ata-WDC_WD6002FZWX-00GBGB0_K8GD7LDD-part1
D2=/dev/disk/by-id/ata-WDC_WD30EZRZ-00Z5HB0_WD-WCC4N7XKD9UC-part1
D3=/dev/disk/by-id/ata-WDC_WD30EFRX-68AX9N0_WD-WCC1T1259471-part1

if [[ "${EUID:-}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0" >&2
  exit 1
fi

for dev in "$D1" "$D2" "$D3"; do
  if [[ ! -b "$dev" ]]; then
    echo "Missing block device: $dev" >&2
    exit 1
  fi
done

shopt -s nullglob
for m in /mnt/d1 /mnt/d2 /mnt/d3; do
  if mountpoint -q "$m" 2>/dev/null; then
    umount "$m"
  fi
done
for m in /media/*/models-d1 /media/*/models-d2 /media/*/models-d3; do
  if mountpoint -q "$m" 2>/dev/null; then
    umount "$m"
  fi
done

mkdir -p /mnt/d1 /mnt/d2 /mnt/d3

mount -t ext4 -o rw "$D1" /mnt/d1
mount -t ext4 -o rw "$D2" /mnt/d2
mount -t ext4 -o rw "$D3" /mnt/d3

echo "Mounted:"
findmnt -n -o TARGET,SOURCE,FSTYPE /mnt/d1 /mnt/d2 /mnt/d3
