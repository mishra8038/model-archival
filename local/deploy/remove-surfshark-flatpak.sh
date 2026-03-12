#!/usr/bin/env bash
# Remove Surfshark Flatpak (system install). Run with: sudo bash deploy/remove-surfshark-flatpak.sh
# User data (~/.var/app/com.surfshark.Surfshark) is already removed by the user.

set -euo pipefail

if [[ $(id -u) -ne 0 ]]; then
    echo "Run with sudo."
    exit 1
fi

flatpak uninstall --system com.surfshark.Surfshark -y 2>/dev/null || true
# Clean leftover refs and cache if uninstall didn't remove everything
rm -rf /var/lib/flatpak/.removed/com.surfshark.Surfshark-* 2>/dev/null || true
echo "Surfshark Flatpak removed."
