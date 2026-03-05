#!/usr/bin/env bash
# =============================================================================
# setup-docker-runtime.sh
#
# Sets up and launches the official Google Colab local runtime on MX Linux
# (Debian/Ubuntu-based). Run this on your LOCAL machine, not on the VM.
#
# What it does:
#   1. Installs Docker (if not present)
#   2. Adds your user to the docker group
#   3. Pulls the official Colab runtime image
#   4. Starts the container and prints the connection URL for Colab
#
# Usage:
#   bash colab/local-tools/setup-docker-runtime.sh [--hf-token hf_xxx] [--port 9000]
#
# Then in Colab browser UI:
#   Connect ▾ → "Connect to a local runtime" → paste the printed URL
# =============================================================================

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
COLAB_IMAGE="us-docker.pkg.dev/colab-images/public/runtime"
PORT=9000
HF_TOKEN="${HF_TOKEN:-}"          # can be set in env or via --hf-token flag
CONTAINER_NAME="colab-runtime"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # repo root

# ── Colour helpers ────────────────────────────────────────────────────────────
_C_RESET="\033[0m"
_C_BOLD="\033[1m"
_C_GREEN="\033[0;32m"
_C_YELLOW="\033[0;33m"
_C_RED="\033[0;31m"
_C_CYAN="\033[0;36m"

TS()    { date '+%H:%M:%S'; }
info()  { echo -e "$(TS)  ${_C_CYAN}INFO${_C_RESET}   $*"; }
ok()    { echo -e "$(TS)  ${_C_GREEN}OK${_C_RESET}     $*"; }
warn()  { echo -e "$(TS)  ${_C_YELLOW}WARN${_C_RESET}   $*"; }
error() { echo -e "$(TS)  ${_C_RED}ERROR${_C_RESET}  $*" >&2; }
banner(){ echo -e "\n${_C_BOLD}${_C_CYAN}══════════════════════════════════════════${_C_RESET}"; \
          echo -e "${_C_BOLD}${_C_CYAN}  $*${_C_RESET}"; \
          echo -e "${_C_BOLD}${_C_CYAN}══════════════════════════════════════════${_C_RESET}\n"; }

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --hf-token) HF_TOKEN="$2"; shift 2 ;;
        --port)     PORT="$2";     shift 2 ;;
        --help|-h)
            echo "Usage: $0 [--hf-token hf_xxx] [--port 9000]"
            echo
            echo "Options:"
            echo "  --hf-token TOKEN   HuggingFace token (or set HF_TOKEN env var)"
            echo "  --port PORT        Host port to expose (default: 9000)"
            exit 0 ;;
        *) error "Unknown argument: $1"; exit 1 ;;
    esac
done

# ── Load HF token from ~/.hf_token if not provided ───────────────────────────
if [[ -z "$HF_TOKEN" && -f "$HOME/.hf_token" ]]; then
    HF_TOKEN="$(cat "$HOME/.hf_token")"
    info "HF_TOKEN loaded from ~/.hf_token"
fi

# =============================================================================
banner "Colab Local Runtime Setup"
# =============================================================================

echo -e "  Project dir : ${_C_BOLD}${PROJECT_DIR}${_C_RESET}"
echo -e "  Docker image: ${_C_BOLD}${COLAB_IMAGE}${_C_RESET}"
echo -e "  Host port   : ${_C_BOLD}${PORT}${_C_RESET}"
echo -e "  HF token    : ${_C_BOLD}$([ -n "$HF_TOKEN" ] && echo "set (${#HF_TOKEN} chars)" || echo "not set — gated models will fail")${_C_RESET}"
echo

# ── Step 1: Install Docker ────────────────────────────────────────────────────
banner "Step 1 — Docker installation"

if command -v docker &>/dev/null; then
    DOCKER_VERSION="$(docker --version)"
    ok "Docker already installed: ${DOCKER_VERSION}"
else
    info "Docker not found — installing via apt..."

    if ! command -v apt-get &>/dev/null; then
        error "apt-get not found. This script is for Debian/MX Linux/Ubuntu only."
        error "For Arch/Artix, install Docker with: sudo pacman -S docker"
        exit 1
    fi

    sudo apt-get update -qq
    sudo apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg lsb-release

    # Add Docker's official GPG key and repository
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg \
        | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    DISTRO_ID="$(. /etc/os-release && echo "${ID_LIKE:-$ID}" | awk '{print $NF}')"
    # MX Linux reports ID_LIKE=debian
    DISTRO_ID="${DISTRO_ID:-debian}"
    # Normalise to debian for the repo URL
    if [[ "$DISTRO_ID" == "mx" || "$DISTRO_ID" == "antix" ]]; then
        DISTRO_ID="debian"
    fi

    CODENAME="$(. /etc/os-release && echo "${VERSION_CODENAME:-bookworm}")"
    # MX Linux 23 is based on Debian bookworm
    info "Using Docker repo for distro=${DISTRO_ID} codename=${CODENAME}"

    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/${DISTRO_ID} ${CODENAME} stable" \
        | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update -qq
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin

    ok "Docker installed: $(docker --version)"
fi

# ── Step 2: Enable and start Docker service ───────────────────────────────────
banner "Step 2 — Docker service"

# Detect init system: systemd vs SysV
INIT_SYSTEM="sysv"
if [[ "$(cat /proc/1/comm 2>/dev/null)" == "systemd" ]]; then
    INIT_SYSTEM="systemd"
fi
info "Init system: ${INIT_SYSTEM}"

_docker_running() {
    docker info &>/dev/null
}

if _docker_running; then
    ok "Docker service is already running"
else
    info "Starting Docker service..."
    if [[ "$INIT_SYSTEM" == "systemd" ]]; then
        sudo systemctl enable --now docker
    else
        sudo /sbin/service docker start || sudo /etc/init.d/docker start
    fi
    sleep 3
    if _docker_running; then
        ok "Docker service started"
    else
        error "Docker failed to start. Try: sudo /sbin/service docker start"
        exit 1
    fi
fi

# ── Step 3: Add user to docker group ─────────────────────────────────────────
banner "Step 3 — Docker group"

CURRENT_USER="${USER:-$(whoami)}"
if groups "$CURRENT_USER" | grep -qw docker; then
    ok "User '${CURRENT_USER}' is already in the docker group"
else
    info "Adding '${CURRENT_USER}' to docker group..."
    sudo usermod -aG docker "$CURRENT_USER"
    warn "Added to docker group — you must log out and back in for this to take effect"
    warn "For this session, the container will be started with sudo"
    DOCKER_CMD="sudo docker"
fi

DOCKER_CMD="${DOCKER_CMD:-docker}"

# ── Step 4: Stop any existing container ──────────────────────────────────────
banner "Step 4 — Container cleanup"

if $DOCKER_CMD ps -a --format '{{.Names}}' | grep -qw "${CONTAINER_NAME}"; then
    info "Stopping existing container '${CONTAINER_NAME}'..."
    $DOCKER_CMD stop "${CONTAINER_NAME}" &>/dev/null || true
    $DOCKER_CMD rm   "${CONTAINER_NAME}" &>/dev/null || true
    ok "Old container removed"
else
    ok "No existing container to clean up"
fi

# ── Step 5: Pull the Colab runtime image ─────────────────────────────────────
banner "Step 5 — Pull Colab runtime image"

info "Pulling ${COLAB_IMAGE} ..."
info "(~5–10 GB download on first pull, cached thereafter)"
$DOCKER_CMD pull "${COLAB_IMAGE}"
ok "Image ready"

# ── Step 6: Start the container ──────────────────────────────────────────────
banner "Step 6 — Start Colab runtime"

# Build docker run args
DOCKER_RUN_ARGS=(
    --name  "${CONTAINER_NAME}"
    --rm                              # auto-remove when stopped
    -p "127.0.0.1:${PORT}:8080"      # expose only to localhost for security
    -v "${PROJECT_DIR}:/content/model-archival:ro"   # mount project read-only
    --memory="8g"                     # cap RAM (increase if your machine has more)
    --cpus="4"                        # cap CPU cores
)

# Pass HF token securely via env (never baked into image)
if [[ -n "$HF_TOKEN" ]]; then
    DOCKER_RUN_ARGS+=(-e "HF_TOKEN=${HF_TOKEN}")
    info "HF_TOKEN injected into container environment"
fi

info "Starting container..."
info "Project mounted at /content/model-archival (read-only)"

# Start detached so the terminal is free
$DOCKER_CMD run -d "${DOCKER_RUN_ARGS[@]}" "${COLAB_IMAGE}"

# ── Step 7: Extract and print connection URL ──────────────────────────────────
banner "Step 7 — Connection URL"

info "Waiting for runtime to initialise (up to 30s)..."
URL=""
for i in $(seq 1 30); do
    sleep 1
    URL="$($DOCKER_CMD logs "${CONTAINER_NAME}" 2>&1 \
        | grep -oP 'http://127\.0\.0\.1:\d+/\?token=\S+' | tail -1)"
    if [[ -n "$URL" ]]; then
        # Replace container's internal port with the host port
        URL="${URL/8080/${PORT}}"
        break
    fi
done

if [[ -z "$URL" ]]; then
    warn "Could not auto-detect URL. Fetch it manually:"
    echo
    echo "    $DOCKER_CMD logs ${CONTAINER_NAME} 2>&1 | grep token"
    echo
else
    echo
    echo -e "${_C_BOLD}${_C_GREEN}╔══════════════════════════════════════════════════════════╗${_C_RESET}"
    echo -e "${_C_BOLD}${_C_GREEN}║  Colab runtime ready!                                    ║${_C_RESET}"
    echo -e "${_C_BOLD}${_C_GREEN}╚══════════════════════════════════════════════════════════╝${_C_RESET}"
    echo
    echo -e "  Connection URL (paste into Colab):"
    echo
    echo -e "  ${_C_BOLD}${_C_CYAN}${URL}${_C_RESET}"
    echo
fi

echo -e "════════════════════════════════════════════════════════════"
echo -e "  How to connect:"
echo -e "  1. Open archiver.ipynb in Colab"
echo -e "  2. Click ${_C_BOLD}Connect ▾${_C_RESET} (top right)"
echo -e "  3. Select ${_C_BOLD}\"Connect to a local runtime\"${_C_RESET}"
echo -e "  4. Paste the URL above → Connect"
echo
echo -e "  Container runs in background. To stop it:"
echo -e "    ${_C_BOLD}${DOCKER_CMD} stop ${CONTAINER_NAME}${_C_RESET}"
echo
echo -e "  To view logs:"
echo -e "    ${_C_BOLD}${DOCKER_CMD} logs -f ${CONTAINER_NAME}${_C_RESET}"
echo -e "════════════════════════════════════════════════════════════"
echo
warn "SECURITY: the runtime is only bound to 127.0.0.1 (localhost only)."
warn "Do not expose port ${PORT} externally."
