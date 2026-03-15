#!/bin/bash
# Install Surfshark OpenVPN as a dinit service (Artix Linux, etc.).
# Run with: sudo bash deploy/install-surfshark-dinit.sh [us-nyc|nl-ams|...]
# Default: us-nyc (NYC/US East). Use nl-ams for EU.

set -e
CONFIG_NAME="${1:-us-nyc}"
CONFDIR="/etc/openvpn/client/surfshark"

if [[ "$CONFIG_NAME" == *.ovpn ]]; then
  CONFIG_FILE="$CONFIG_NAME"
else
  CONFIG_FILE="${CONFIG_NAME}.prod.surfshark.com_udp.ovpn"
fi

if [ ! -f "$CONFDIR/$CONFIG_FILE" ] || [ ! -f "$CONFDIR/surfshark.auth" ]; then
  echo "Note: $CONFDIR/$CONFIG_FILE or surfshark.auth missing. Create them first (see docs/DEPLOYMENT.md)."
  echo "      Installing service anyway; start will fail until config and auth exist."
fi

# Artix uses /usr/bin/openvpn (Arch package); some use /usr/sbin/openvpn
OPENVPN="$(command -v openvpn 2>/dev/null || echo /usr/bin/openvpn)"
mkdir -p /etc/dinit.d/boot.d /var/log/dinit

cat > /etc/dinit.d/openvpn-surfshark << EOF
type            = process
command         = $OPENVPN --config $CONFDIR/$CONFIG_FILE --auth-user-pass $CONFDIR/surfshark.auth
smooth-recovery = true
restart         = true
restart-delay   = 10
logfile         = /var/log/dinit/openvpn-surfshark.log
depends-on      = network.target
before          = login.target
EOF

ln -sf /etc/dinit.d/openvpn-surfshark /etc/dinit.d/boot.d/openvpn-surfshark
echo "Installed dinit service openvpn-surfshark (server: $CONFIG_FILE)"
echo "Start:  sudo dinitctl start openvpn-surfshark"
echo "Stop:   sudo dinitctl stop openvpn-surfshark"
echo "Status: sudo dinitctl status openvpn-surfshark"
