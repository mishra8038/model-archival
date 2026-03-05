#!/bin/sh
# =============================================================================
# setup-alpine-colab.sh
#
# Sets up the Google Colab local runtime on Alpine Linux.
# Designed to run once on a fresh Alpine VM (no XFCE required — headless).
#
# What it does:
#   1. Installs Docker via apk
#   2. Adds the current user to the docker group
#   3. Starts Docker via OpenRC and enables it on boot
#   4. Pulls the official Colab runtime image
#   5. Starts the container with --restart=unless-stopped
#   6. Prints the connection URL to paste into Colab
#   7. Creates a helper script ~/colab-url.sh to retrieve the URL any time
#
# Usage:
#   sh setup-alpine-colab.sh [--hf-token hf_xxx] [--port 9000]
#
# Copy to VM first:
#   scp colab/local-tools/setup-alpine-colab.sh user@<vm-ip>:~/
#   ssh user@<vm-ip> "sh ~/setup-alpine-colab.sh --hf-token hf_YOUR_TOKEN"
#
# After setup, get the Colab connection URL at any time:
#   ssh user@<vm-ip> "sh ~/colab-url.sh"
# =============================================================================

set -e

# ── Defaults ──────────────────────────────────────────────────────────────────
PORT=9000
HF_TOKEN="${HF_TOKEN:-}"
CONTAINER_NAME="colab-runtime"
COLAB_IMAGE="us-docker.pkg.dev/colab-images/public/runtime"
PROJECT_MOUNT=""    # optional: mount a local project dir into the container

# ── Colour helpers (POSIX sh compatible) ─────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

ts()     { date '+%H:%M:%S'; }
info()   { printf "${CYAN}[%s] INFO${RESET}   %s\n"   "$(ts)" "$*"; }
ok()     { printf "${GREEN}[%s] OK${RESET}     %s\n"   "$(ts)" "$*"; }
warn()   { printf "${YELLOW}[%s] WARN${RESET}   %s\n"  "$(ts)" "$*"; }
err()    { printf "${RED}[%s] ERROR${RESET}  %s\n"  "$(ts)" "$*" >&2; }
banner() { printf "\n${BOLD}${CYAN}══════════════════════════════════════════${RESET}\n"
           printf "${BOLD}${CYAN}  %s${RESET}\n" "$*"
           printf "${BOLD}${CYAN}══════════════════════════════════════════${RESET}\n\n"; }

# ── Argument parsing ──────────────────────────────────────────────────────────
while [ $# -gt 0 ]; do
    case "$1" in
        --hf-token) HF_TOKEN="$2"; shift 2 ;;
        --port)     PORT="$2";     shift 2 ;;
        --mount)    PROJECT_MOUNT="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: $0 [--hf-token hf_xxx] [--port 9000] [--mount /path/to/project]"
            exit 0 ;;
        *) err "Unknown argument: $1"; exit 1 ;;
    esac
done

# Load HF token from ~/.hf_token if not provided
if [ -z "$HF_TOKEN" ] && [ -f "$HOME/.hf_token" ]; then
    HF_TOKEN="$(cat "$HOME/.hf_token")"
    info "HF_TOKEN loaded from ~/.hf_token"
fi

# =============================================================================
banner "Alpine Colab Runtime Setup"
# =============================================================================

printf "  Image   : %s\n" "$COLAB_IMAGE"
printf "  Port    : %s\n" "$PORT"
printf "  HF token: %s\n" "$([ -n "$HF_TOKEN" ] && echo "set (${#HF_TOKEN} chars)" || echo "not set — gated models will fail")"
printf "  Mount   : %s\n\n" "$([ -n "$PROJECT_MOUNT" ] && echo "$PROJECT_MOUNT" || echo "none")"

# ── Step 1: Install Docker ────────────────────────────────────────────────────
banner "Step 1 — Install Docker"

if command -v docker > /dev/null 2>&1; then
    ok "Docker already installed: $(docker --version)"
else
    info "Installing Docker via apk..."
    apk update --quiet
    apk add --quiet docker docker-cli docker-compose
    ok "Docker installed: $(docker --version)"
fi

# Install curl if missing (needed for connectivity check)
command -v curl > /dev/null 2>&1 || apk add --quiet curl

# ── Step 2: OpenRC — enable and start Docker ──────────────────────────────────
banner "Step 2 — Docker service (OpenRC)"

# Add to default runlevel so it starts on boot
if ! rc-update show default 2>/dev/null | grep -q docker; then
    rc-update add docker default
    ok "Docker added to OpenRC default runlevel"
else
    ok "Docker already in OpenRC default runlevel"
fi

# Start the service now
if rc-service docker status > /dev/null 2>&1; then
    ok "Docker service already running"
else
    info "Starting Docker service..."
    rc-service docker start
    sleep 3
    if rc-service docker status > /dev/null 2>&1; then
        ok "Docker service started"
    else
        err "Docker failed to start. Check: rc-service docker start"
        exit 1
    fi
fi

# ── Step 3: Docker group ──────────────────────────────────────────────────────
banner "Step 3 — Docker group"

CURRENT_USER="$(whoami)"
if id -nG "$CURRENT_USER" | grep -qw docker; then
    ok "User '$CURRENT_USER' already in docker group"
else
    addgroup "$CURRENT_USER" docker 2>/dev/null || \
        adduser "$CURRENT_USER" docker 2>/dev/null || true
    ok "User '$CURRENT_USER' added to docker group"
    warn "Group change takes effect on next login or new shell"
    # For this script, use sg to run docker commands with the new group
    DOCKER_CMD="sg docker -c docker"
fi

DOCKER_CMD="${DOCKER_CMD:-docker}"

# ── Step 4: Stop any existing container ──────────────────────────────────────
banner "Step 4 — Cleanup"

if $DOCKER_CMD ps -a --format '{{.Names}}' 2>/dev/null | grep -qw "$CONTAINER_NAME"; then
    info "Removing existing container '$CONTAINER_NAME'..."
    $DOCKER_CMD stop "$CONTAINER_NAME" > /dev/null 2>&1 || true
    $DOCKER_CMD rm   "$CONTAINER_NAME" > /dev/null 2>&1 || true
    ok "Old container removed"
else
    ok "No existing container"
fi

# ── Step 5: Pull Colab image ──────────────────────────────────────────────────
banner "Step 5 — Pull Colab runtime image"

info "Pulling $COLAB_IMAGE"
info "First pull is ~8-10 GB. This will take a while on first run."
info "Subsequent runs use the cached image (instant)."
$DOCKER_CMD pull "$COLAB_IMAGE"
ok "Image ready"

# ── Step 6: Start the container ──────────────────────────────────────────────
banner "Step 6 — Start container"

# Build run arguments
RUN_ARGS="--name $CONTAINER_NAME"
RUN_ARGS="$RUN_ARGS --restart=unless-stopped"
RUN_ARGS="$RUN_ARGS -p 127.0.0.1:${PORT}:8080"
RUN_ARGS="$RUN_ARGS --memory=4g"
RUN_ARGS="$RUN_ARGS --cpus=2"

# Mount project directory if provided
if [ -n "$PROJECT_MOUNT" ] && [ -d "$PROJECT_MOUNT" ]; then
    RUN_ARGS="$RUN_ARGS -v ${PROJECT_MOUNT}:/content/project:ro"
    info "Mounting $PROJECT_MOUNT → /content/project"
fi

# Inject HF token
if [ -n "$HF_TOKEN" ]; then
    RUN_ARGS="$RUN_ARGS -e HF_TOKEN=$HF_TOKEN"
    info "HF_TOKEN injected into container"
fi

info "Starting container..."
$DOCKER_CMD run -d $RUN_ARGS "$COLAB_IMAGE"

# ── Step 7: Extract connection URL ────────────────────────────────────────────
banner "Step 7 — Connection URL"

info "Waiting for runtime to initialise (30s)..."
URL=""
i=0
while [ $i -lt 30 ]; do
    sleep 1
    i=$((i + 1))
    URL="$($DOCKER_CMD logs "$CONTAINER_NAME" 2>&1 \
        | grep -oE 'http://127\.0\.0\.1:[0-9]+/\?token=[a-zA-Z0-9]+' \
        | tail -1)"
    if [ -n "$URL" ]; then
        URL="$(echo "$URL" | sed "s/:[0-9]*\//:${PORT}\//")"
        break
    fi
done

# ── Step 8: Write helper script ───────────────────────────────────────────────
cat > "$HOME/colab-url.sh" << HELPER
#!/bin/sh
# Run any time to get the current Colab connection URL
URL=\$(docker logs $CONTAINER_NAME 2>&1 \\
    | grep -oE 'http://127\\.0\\.0\\.1:[0-9]+/\\?token=[a-zA-Z0-9]+' \\
    | tail -1 \\
    | sed 's/:[0-9]*\\//:${PORT}\\//')
if [ -n "\$URL" ]; then
    echo
    echo "  Colab connection URL:"
    echo
    echo "  \$URL"
    echo
    echo "  Colab: Connect ▾ → Connect to a local runtime → paste URL"
    echo
else
    echo "Container not running or URL not yet available."
    echo "Check: docker logs $CONTAINER_NAME"
fi
HELPER
chmod +x "$HOME/colab-url.sh"
ok "Helper script written to ~/colab-url.sh"

# ── Final output ──────────────────────────────────────────────────────────────
banner "Setup Complete"

if [ -n "$URL" ]; then
    printf "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════╗${RESET}\n"
    printf "${BOLD}${GREEN}║  Colab runtime is ready                                  ║${RESET}\n"
    printf "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════╝${RESET}\n\n"
    printf "  ${BOLD}Connection URL (paste into Colab):${RESET}\n\n"
    printf "  ${BOLD}${CYAN}%s${RESET}\n\n" "$URL"
else
    warn "Could not auto-detect URL. Fetch it with:"
    printf "  sh ~/colab-url.sh\n\n"
fi

printf "══════════════════════════════════════════════════════════\n"
printf "  How to connect:\n"
printf "  1. Open colab/archiver.ipynb in your browser\n"
printf "  2. Click ${BOLD}Connect ▾${RESET} (top right of Colab)\n"
printf "  3. Select ${BOLD}\"Connect to a local runtime\"${RESET}\n"
printf "  4. Paste the URL above → Connect\n"
printf "\n"
printf "  Container management:\n"
printf "    docker ps                          # check running\n"
printf "    docker logs -f %-22s # live logs\n" "$CONTAINER_NAME"
printf "    docker stop  %-22s # stop\n"        "$CONTAINER_NAME"
printf "    docker start %-22s # restart\n"     "$CONTAINER_NAME"
printf "    sh ~/colab-url.sh                  # get URL any time\n"
printf "\n"
printf "  ${YELLOW}NOTE: URL changes if container is restarted.${RESET}\n"
printf "  ${YELLOW}      Run ~/colab-url.sh after any restart to get the new URL.${RESET}\n"
printf "══════════════════════════════════════════════════════════\n\n"
