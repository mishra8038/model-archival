# VM Surfshark: single OpenVPN service (2026-03-21)

- **Issue:** Two dinit services both ran OpenVPN (`openvpn-surfshark` + `surfshark-vpn`) → two `tun` devices; stopping one could drop `0.0.0.0/1` + `128.0.0.0/1` routes and leak traffic via ISP.
- **Fix on `x@192.168.8.65`:**
  - Removed boot symlink `/etc/dinit.d/boot.d/surfshark-vpn` (already absent after first fix).
  - Renamed `/etc/dinit.d/surfshark-vpn` → `/etc/dinit.d/surfshark-vpn.disabled` with a comment to use **`openvpn-surfshark` only**.
- **Canonical service:** `openvpn-surfshark` — config `us-nyc.prod.surfshark.com_udp.ovpn`, auth `/etc/openvpn/client/surfshark/surfshark.auth`.
- **Full-tunnel IPv4:** Surfshark push `redirect-gateway def1` → routes `0.0.0.0/1` + `128.0.0.0/1` via `tun0`; LAN + VPN server IP stay on `eth0`.
