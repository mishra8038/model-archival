#!/usr/bin/env bash
# =============================================================================
# setup-mxlinux-colab.sh
#
# Deploys Docker and the Google Colab local runtime on MX Linux 23.x
# (Debian bookworm-based, SysV init).
#
# Run once on the target MX Linux machine. Safe to re-run.
#
# Usage:
#   bash setup-mxlinux-colab.sh [--hf-token hf_xxx] [--port 9000]
#
# Copy to target machine first:
#   scp colab/local-tools/setup-mxlinux-colab.sh user@<mx-ip>:~/
#   ssh user@<mx-ip> "bash ~/setup-mxlinux-colab.sh --hf-token hf_YOUR_TOKEN"
#
# After setup, get the Colab connection URL at any time:
#   bash ~/colab-url.sh
# =============================================================================

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
PORT=9000
HF_TOKEN="${HF_TOKEN:-}"
CONTAINER_NAME="colab-runtime"
COLAB_IMAGE="us-docker.pkg.dev/colab-images/public/runtime"
REPORT_DIR="${HOME}"
REPORT_FILE="${REPORT_DIR}/colab-setup-report-$(date '+%Y-%m-%d_%H-%M-%S').md"

# ── Colour helpers ────────────────────────────────────────────────────────────
_R='\033[0m'; _BOLD='\033[1m'
_GREEN='\033[0;32m'; _YELLOW='\033[0;33m'; _RED='\033[0;31m'; _CYAN='\033[0;36m'

TS()    { date '+%H:%M:%S'; }
info()  { echo -e "$(TS)  ${_CYAN}INFO${_R}    $*"; }
ok()    { echo -e "$(TS)  ${_GREEN}OK${_R}      $*"; }
warn()  { echo -e "$(TS)  ${_YELLOW}WARN${_R}    $*"; }
err()   { echo -e "$(TS)  ${_RED}ERROR${_R}   $*" >&2; }
banner(){
    echo -e "\n${_BOLD}${_CYAN}══════════════════════════════════════════${_R}"
    echo -e "${_BOLD}${_CYAN}  $*${_R}"
    echo -e "${_BOLD}${_CYAN}══════════════════════════════════════════${_R}\n"
}

# ── Report helpers ────────────────────────────────────────────────────────────
_REPORT_LINES=()
_rpt()        { _REPORT_LINES+=("$*"); }
_rpt_pass()   { _rpt "- ✅ $*"; ok "$*"; }
_rpt_fail()   { _rpt "- ❌ $*"; err "$*"; }
_rpt_warn()   { _rpt "- ⚠️  $*"; warn "$*"; }
_rpt_info()   { _rpt "- ℹ️  $*"; info "$*"; }

flush_report(){
    {
        echo "# Colab Runtime Setup Report"
        echo ""
        echo "- Machine : $(hostname)"
        echo "- Date    : $(date)"
        echo "- User    : $(whoami)"
        echo ""
        echo "## Steps"
        echo ""
        for line in "${_REPORT_LINES[@]}"; do
            echo "$line"
        done
    } > "$REPORT_FILE"
}

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --hf-token) HF_TOKEN="$2"; shift 2 ;;
        --port)     PORT="$2";     shift 2 ;;
        --help|-h)
            echo "Usage: $0 [--hf-token hf_xxx] [--port 9000]"
            echo "  --hf-token   HuggingFace token for gated models"
            echo "  --port       Host port to bind (default: 9000)"
            exit 0 ;;
        *) err "Unknown argument: $1"; exit 1 ;;
    esac
done

# Load HF token from ~/.hf_token if not provided
if [[ -z "$HF_TOKEN" && -f "$HOME/.hf_token" ]]; then
    HF_TOKEN="$(cat "$HOME/.hf_token")"
    info "HF_TOKEN loaded from ~/.hf_token"
fi

# Must run as root or with sudo
if [[ "$EUID" -ne 0 ]]; then
    if ! sudo -n true 2>/dev/null; then
        err "This script requires sudo. Run as root or ensure passwordless sudo."
        err "Or prefix with: sudo bash $0"
        exit 1
    fi
    SUDO="sudo"
else
    SUDO=""
fi

# =============================================================================
banner "MX Linux 23 — Colab Runtime Setup"
# =============================================================================

echo -e "  Image   : ${_BOLD}${COLAB_IMAGE}${_R}"
echo -e "  Port    : ${_BOLD}${PORT}${_R}"
echo -e "  Token   : ${_BOLD}$([ -n "$HF_TOKEN" ] && echo "set (${#HF_TOKEN} chars)" || echo "not set — gated models will fail")${_R}"
echo -e "  Report  : ${_BOLD}${REPORT_FILE}${_R}"
echo

_rpt "## Configuration"
_rpt "- Image: \`${COLAB_IMAGE}\`"
_rpt "- Port: ${PORT}"
_rpt "- HF token: $([ -n "$HF_TOKEN" ] && echo "set" || echo "not set")"
_rpt ""
_rpt "## Steps"

# =============================================================================
banner "Step 1 — System packages"
# =============================================================================

info "Updating package lists..."
$SUDO apt-get update -qq

info "Installing prerequisites..."
$SUDO apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    apt-transport-https \
    2>/dev/null

_rpt_pass "System prerequisites installed"

# =============================================================================
banner "Step 2 — Docker CE"
# =============================================================================

if docker --version &>/dev/null; then
    VER="$(docker --version)"
    _rpt_pass "Docker already installed: ${VER}"
else
    info "Adding Docker's official GPG key and apt repository..."

    $SUDO install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg \
        | $SUDO gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    $SUDO chmod a+r /etc/apt/keyrings/docker.gpg

    # MX Linux 23 is based on Debian bookworm
    CODENAME="bookworm"
    ARCH="$(dpkg --print-architecture)"

    echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/debian ${CODENAME} stable" \
        | $SUDO tee /etc/apt/sources.list.d/docker.list > /dev/null

    info "Installing Docker CE..."
    $SUDO apt-get update -qq
    $SUDO apt-get install -y \
        docker-ce \
        docker-ce-cli \
        containerd.io \
        docker-buildx-plugin

    VER="$(docker --version)"
    _rpt_pass "Docker CE installed: ${VER}"
fi

# =============================================================================
banner "Step 3 — Docker service (SysV init)"
# =============================================================================

# MX Linux uses SysV init — systemctl is not available
_docker_running() { docker info &>/dev/null; }

if _docker_running; then
    _rpt_pass "Docker daemon already running"
else
    info "Starting Docker daemon via SysV init..."
    $SUDO /etc/init.d/docker start || $SUDO /sbin/service docker start
    sleep 3

    if _docker_running; then
        _rpt_pass "Docker daemon started"
    else
        _rpt_fail "Docker daemon failed to start"
        flush_report
        err "Could not start Docker. Check: sudo /etc/init.d/docker start"
        exit 1
    fi
fi

# Enable Docker to start on boot via SysV update-rc.d
if $SUDO update-rc.d docker enable 2>/dev/null; then
    _rpt_pass "Docker enabled on boot (update-rc.d)"
else
    _rpt_warn "Could not enable Docker on boot — start manually after reboot if needed"
fi

# =============================================================================
banner "Step 4 — Docker group"
# =============================================================================

CURRENT_USER="${SUDO_USER:-$USER}"
if id -nG "$CURRENT_USER" | grep -qw docker; then
    _rpt_pass "User '${CURRENT_USER}' already in docker group"
else
    $SUDO usermod -aG docker "$CURRENT_USER"
    _rpt_pass "User '${CURRENT_USER}' added to docker group"
    _rpt_warn "Group change requires re-login to take effect without sudo"
fi

# Determine whether we need sudo for docker commands in this session
if id -nG "$CURRENT_USER" | grep -qw docker && [ "$EUID" -ne 0 ]; then
    DC="docker"
elif [ "$EUID" -eq 0 ]; then
    DC="docker"
else
    DC="$SUDO docker"
fi

# =============================================================================
banner "Step 5 — Remove old container (if any)"
# =============================================================================

if $DC ps -a --format '{{.Names}}' 2>/dev/null | grep -qw "$CONTAINER_NAME"; then
    info "Removing existing container '${CONTAINER_NAME}'..."
    $DC stop "$CONTAINER_NAME" &>/dev/null || true
    $DC rm   "$CONTAINER_NAME" &>/dev/null || true
    _rpt_pass "Old container removed"
else
    _rpt_info "No existing container to remove"
fi

# =============================================================================
banner "Step 6 — Pull Colab runtime image"
# =============================================================================

info "Pulling ${COLAB_IMAGE}"
info "First pull is ~8–10 GB — this will take several minutes."
info "Progress is shown below. The script continues automatically when done."
echo

$DC pull "$COLAB_IMAGE"
echo

_rpt_pass "Colab runtime image pulled"

# =============================================================================
banner "Step 7 — Start container"
# =============================================================================

DOCKER_RUN_ARGS=(
    --name  "$CONTAINER_NAME"
    --restart=unless-stopped
    -p "127.0.0.1:${PORT}:8080"
    --memory="4g"
    --cpus="2"
    --log-opt max-size=50m
    --log-opt max-file=3
)

if [[ -n "$HF_TOKEN" ]]; then
    DOCKER_RUN_ARGS+=(-e "HF_TOKEN=${HF_TOKEN}")
    _rpt_info "HF_TOKEN injected into container environment"
fi

info "Starting container..."
$DC run -d "${DOCKER_RUN_ARGS[@]}" "$COLAB_IMAGE"
_rpt_pass "Container started: ${CONTAINER_NAME}"

# =============================================================================
banner "Step 8 — Connection URL"
# =============================================================================

info "Waiting for Jupyter to initialise (up to 30s)..."
URL=""
for i in $(seq 1 30); do
    sleep 1
    URL="$($DC logs "$CONTAINER_NAME" 2>&1 \
        | grep -oP 'http://127\.0\.0\.1:\d+/\?token=\S+' \
        | tail -1)"
    if [[ -n "$URL" ]]; then
        URL="${URL//:8080\//:${PORT}\/}"
        break
    fi
done

# =============================================================================
banner "Step 9 — Write helper scripts"
# =============================================================================

# ~/colab-url.sh — get the URL any time
cat > "$HOME/colab-url.sh" << HELPER
#!/usr/bin/env bash
# Prints the current Colab connection URL
CONTAINER="${CONTAINER_NAME}"
PORT="${PORT}"
DC="docker"
id -nG "\$(whoami)" | grep -qw docker || DC="sudo docker"

URL="\$(\$DC logs "\$CONTAINER" 2>&1 \\
    | grep -oP 'http://127\.0\.0\.1:\d+/\?token=\S+' \\
    | tail -1)"

if [[ -n "\$URL" ]]; then
    URL="\${URL//:8080\//:${PORT}\/}"
    echo
    echo "  ┌─────────────────────────────────────────────────────────────┐"
    echo "  │  Colab connection URL                                       │"
    echo "  └─────────────────────────────────────────────────────────────┘"
    echo
    echo "  \$URL"
    echo
    echo "  In Colab: Connect ▾ → Connect to a local runtime → paste URL"
    echo
else
    echo "  Container not running or not yet ready."
    echo "  Check: \$DC ps"
    echo "  Logs : \$DC logs \$CONTAINER"
fi
HELPER
chmod +x "$HOME/colab-url.sh"
ok "Helper written → ~/colab-url.sh"

# ~/colab-status.sh — quick status check
cat > "$HOME/colab-status.sh" << STATUS
#!/usr/bin/env bash
DC="docker"
id -nG "\$(whoami)" | grep -qw docker || DC="sudo docker"

echo "=== Docker service ==="
/etc/init.d/docker status 2>/dev/null || /sbin/service docker status 2>/dev/null

echo
echo "=== Colab container ==="
\$DC ps -a --filter name=${CONTAINER_NAME} \
    --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo
echo "=== Resource usage ==="
\$DC stats --no-stream --format \
    "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" ${CONTAINER_NAME} 2>/dev/null || true
STATUS
chmod +x "$HOME/colab-status.sh"
ok "Helper written → ~/colab-status.sh"

_rpt_pass "Helper scripts written"

# =============================================================================
# Final output
# =============================================================================

flush_report

echo
if [[ -n "$URL" ]]; then
    echo -e "${_BOLD}${_GREEN}╔══════════════════════════════════════════════════════════╗${_R}"
    echo -e "${_BOLD}${_GREEN}║  Colab runtime is ready!                                 ║${_R}"
    echo -e "${_BOLD}${_GREEN}╚══════════════════════════════════════════════════════════╝${_R}"
    echo
    echo -e "  ${_BOLD}Paste this URL into Colab:${_R}"
    echo
    echo -e "  ${_BOLD}${_CYAN}${URL}${_R}"
    echo
else
    warn "Could not auto-detect URL. Run after a few seconds:"
    echo -e "  ${_BOLD}bash ~/colab-url.sh${_R}"
    echo
fi

echo -e "══════════════════════════════════════════════════════════"
echo -e "  How to connect Colab:"
echo -e "  1. Open ${_BOLD}colab/archiver.ipynb${_R} at colab.research.google.com"
echo -e "  2. Click ${_BOLD}Connect ▾${_R} (top right)"
echo -e "  3. Select ${_BOLD}\"Connect to a local runtime\"${_R}"
echo -e "  4. Paste the URL above → Connect"
echo
echo -e "  Useful commands on this machine:"
echo -e "    bash ~/colab-url.sh      # get connection URL"
echo -e "    bash ~/colab-status.sh   # container + resource status"
echo -e "    ${DC} logs -f ${CONTAINER_NAME}  # live container logs"
echo -e "    ${DC} stop ${CONTAINER_NAME}     # stop container"
echo -e "    ${DC} start ${CONTAINER_NAME}    # restart container"
echo
echo -e "  ${_YELLOW}NOTE: URL changes if the container is restarted.${_R}"
echo -e "  ${_YELLOW}      Run ~/colab-url.sh after any restart.${_R}"
echo
echo -e "  Report saved: ${_BOLD}${REPORT_FILE}${_R}"
echo -e "══════════════════════════════════════════════════════════"
