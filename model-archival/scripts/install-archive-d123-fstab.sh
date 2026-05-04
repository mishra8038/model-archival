#!/usr/bin/env bash
# Append permanent fstab mounts for models-d1 / d2 / d3 at /mnt/d1–d3 (UUID-based).
# Safe to run twice (skips if markers already present).
#
# Run in a terminal: sudo bash install-archive-d123-fstab.sh
# Optional NOPASSWD for agents (match path): x ALL=(root) NOPASSWD: /full/path/install-archive-d123-fstab.sh
#
# UUIDs match filesystem labels models-d1 … models-d3 (verify: blkid | grep models-d).
set -euo pipefail

if [[ "${EUID:-}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0" >&2
  exit 1
fi

MARK_BEGIN="# >>> model-archival archive disks (models-d1,d2,d3)"
MARK_END="# <<< model-archival archive disks"

UUID_D1='b5eb9174-b438-40b3-b26b-046cd44cb296'
UUID_D2='62a732fb-3c90-42e8-8ee2-e138a1444747'
UUID_D3='47bf0892-fe9c-4e19-a9c9-37bd93f9c4d2'

if grep -qF 'model-archival archive disks' /etc/fstab 2>/dev/null; then
  echo "fstab already contains model-archival archive block; remove it manually to re-add."
  exit 0
fi

cp -a /etc/fstab "/etc/fstab.bak.$(date +%Y%m%d%H%M%S)"

tmp="$(mktemp)"
{
  cat /etc/fstab
  printf '\n%s\n' "$MARK_BEGIN"
  printf 'UUID=%s /mnt/d1 ext4 defaults,nofail 0 2\n' "$UUID_D1"
  printf 'UUID=%s /mnt/d2 ext4 defaults,nofail 0 2\n' "$UUID_D2"
  printf 'UUID=%s /mnt/d3 ext4 defaults,nofail 0 2\n' "$UUID_D3"
  printf '%s\n' "$MARK_END"
} >"$tmp"
mv "$tmp" /etc/fstab
chmod 644 /etc/fstab

mkdir -p /mnt/d1 /mnt/d2 /mnt/d3

# Drop stale /media automounts if present so /mnt can attach.
shopt -s nullglob
for m in /media/*/models-d1 /media/*/models-d2 /media/*/models-d3; do
  if mountpoint -q "$m" 2>/dev/null; then umount "$m" || true; fi
done

for mp in /mnt/d1 /mnt/d2 /mnt/d3; do
  if ! mountpoint -q "$mp"; then mount "$mp"; fi
done
echo "Done. Verify (each mountpoint is separate; /mnt itself is not mounted):"
echo "  for d in /mnt/d1 /mnt/d2 /mnt/d3; do findmnt \"\$d\"; done"
