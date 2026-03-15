#!/bin/bash
# Install Surfshark OpenVPN as a SysV-style init script (MX Linux sysvinit, etc.).
# Run with: sudo bash deploy/install-surfshark-sysvinit.sh
# Config: edit CONFIG in /etc/init.d/openvpn-surfshark after install (us-nyc, nl-ams, etc.).

set -e
CONFIG_NAME="${1:-us-nyc}"   # optional: us-nyc, nl-ams, de-fra, etc.

INSTALL_MARKER="/etc/init.d/openvpn-surfshark"
CONFDIR="/etc/openvpn/client/surfshark"
mkdir -p /etc/init.d "$CONFDIR"

# Build .ovpn filename (us-nyc -> us-nyc.prod.surfshark.com_udp.ovpn)
if [[ "$CONFIG_NAME" == *.ovpn ]]; then
  CONFIG_FILE="$CONFIG_NAME"
else
  CONFIG_FILE="${CONFIG_NAME}.prod.surfshark.com_udp.ovpn"
fi

if [ ! -f "$CONFDIR/$CONFIG_FILE" ] || [ ! -f "$CONFDIR/surfshark.auth" ]; then
  echo "Note: $CONFDIR/$CONFIG_FILE or surfshark.auth not found yet."
  echo "      Install will continue; run 'sudo /etc/init.d/openvpn-surfshark start' after you set up VPN (see docs/DEPLOYMENT.md)."
fi

cat > "$INSTALL_MARKER" << SCRIPT
#!/bin/bash
# Surfshark OpenVPN — change CONFIG for your region (us-nyc, nl-ams, de-fra, etc.)
CONFIG="$CONFIG_FILE"
CONFDIR="/etc/openvpn/client/surfshark"
AUTH="\$CONFDIR/surfshark.auth"
LOG="/var/log/surfshark-openvpn.log"
PIDFILE="/var/run/openvpn-surfshark.pid"

case "\$1" in
  start)
    if [ -f "\$PIDFILE" ] && kill -0 "\$(cat "\$PIDFILE")" 2>/dev/null; then
      echo "openvpn-surfshark already running"
      exit 0
    fi
    /usr/sbin/openvpn --config "\$CONFDIR/\$CONFIG" --auth-user-pass "\$AUTH" --daemon --log "\$LOG" --writepid "\$PIDFILE"
    ;;
  stop)
    [ -f "\$PIDFILE" ] && kill "\$(cat "\$PIDFILE")" 2>/dev/null; rm -f "\$PIDFILE"
    ;;
  status)
    if [ -f "\$PIDFILE" ] && kill -0 "\$(cat "\$PIDFILE")" 2>/dev/null; then
      echo "openvpn-surfshark is running"; exit 0
    else
      echo "openvpn-surfshark is not running"; exit 1
    fi
    ;;
  *)
    echo "Usage: \$0 {start|stop|status}"; exit 1
    ;;
esac
exit 0
SCRIPT
chmod +x "$INSTALL_MARKER"
echo "Installed $INSTALL_MARKER (server: $CONFIG_FILE)"

# Enable at boot if this system has update-rc.d
if command -v update-rc.d >/dev/null 2>&1; then
  update-rc.d openvpn-surfshark defaults
  echo "Enabled at boot (update-rc.d). Start now: sudo service openvpn-surfshark start"
else
  echo "update-rc.d not found. To start now run: sudo /etc/init.d/openvpn-surfshark start"
  echo "To start at boot, add to crontab: @reboot /etc/init.d/openvpn-surfshark start"
  echo "  Or create symlinks in /etc/rc.d/ (rc2.d, rc3.d, etc.) if your init uses them."
fi
