#!/usr/bin/env bash
# =============================================================================
# deploy/setup-mxlinux.sh
# Bootstrap model-archival on MX Linux (Debian / apt-based)
#
# Usage:
#   bash setup-mxlinux.sh [--repo-dir /path/to/model-archival]
#
# Steps:
#   1. Install system packages via apt
#   2. Install uv (Astral) user-locally
#   3. Pin Python 3.11 and sync the virtual environment
#   4. Smoke-test the archiver CLI
#   5. Create /mnt/models/dN mount point directories
#   6. Add archiver-screen shell alias
#
# Run as a normal user WITH sudo privileges (not as root).
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo-dir) REPO_DIR="$2"; shift 2 ;;
        *) error "Unknown argument: $1" ;;
    esac
done

# ---------------------------------------------------------------------------
# Initialise report
# ---------------------------------------------------------------------------
init_report "setup-mxlinux"
_rpt "| Distro | MX Linux (Debian/apt) |"
_rpt "| Repo dir | \`$REPO_DIR\` |"
_rpt ""

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------
step "Pre-flight Checks"

[[ -f "$REPO_DIR/pyproject.toml" ]] \
    || error "pyproject.toml not found in $REPO_DIR — pass --repo-dir if needed."
ok "pyproject.toml found at $REPO_DIR"

command -v sudo &>/dev/null || error "'sudo' not available — run as a user with sudo privileges."
ok "sudo available"

_rpt "| pyproject.toml | found |"
_rpt "| sudo | available |"

# ---------------------------------------------------------------------------
# 1. System packages
# ---------------------------------------------------------------------------
step "1 — System Packages (apt)"

PACKAGES=(
    python3
    python3-pip
    python3-venv
    aria2
    git
    screen
    rsync
    curl
    wget
    ca-certificates
    htop
    nvme-cli
    gdisk
)

info "Updating apt package index…"
run_cmd --silent "sudo apt-get update -qq"
ok "Package index updated"

info "Installing: ${PACKAGES[*]}"
_rpt "**Packages:** \`${PACKAGES[*]}\`"
_rpt ""

# Install each package and report individually
INSTALLED=()
ALREADY=()
for pkg in "${PACKAGES[@]}"; do
    if dpkg -s "$pkg" &>/dev/null 2>&1; then
        ver=$(dpkg -s "$pkg" 2>/dev/null | grep '^Version:' | awk '{print $2}')
        ok "$pkg  (already installed — $ver)"
        ALREADY+=("$pkg")
        _rpt "  - $pkg — already installed ($ver)"
    else
        echo -e "      ${_C_DIM}Installing $pkg…${_C_RESET}"
        if sudo apt-get install -y "$pkg" &>/dev/null; then
            ver=$(dpkg -s "$pkg" 2>/dev/null | grep '^Version:' | awk '{print $2}')
            ok "$pkg  installed ($ver)"
            INSTALLED+=("$pkg")
            _rpt "  - $pkg — installed ($ver)"
        else
            warn "$pkg installation failed — continuing"
            _rpt "  - $pkg — ⚠ FAILED"
        fi
    fi
done

echo ""
info "Packages: ${#INSTALLED[@]} newly installed, ${#ALREADY[@]} already present"
_rpt ""
_rpt "Summary: ${#INSTALLED[@]} newly installed, ${#ALREADY[@]} already present"

# Verify key binaries
echo ""
info "Verifying key binaries…"
for bin in aria2c python3 git screen rsync sgdisk; do
    if command -v "$bin" &>/dev/null; then
        ver=$("$bin" --version 2>&1 | head -1 || true)
        ok "$bin — $ver"
        _rpt "  - \`$bin\` ✔  $ver"
    else
        warn "$bin not found in PATH after install"
        _rpt "  - \`$bin\` ⚠ not found"
    fi
done

# ---------------------------------------------------------------------------
# 2. Install uv
# ---------------------------------------------------------------------------
step "2 — Install uv (Python toolchain manager)"

export PATH="$HOME/.local/bin:$PATH"

if command -v uv &>/dev/null; then
    UV_VER=$(uv --version 2>&1)
    info "uv already installed: $UV_VER"
    ok "uv $UV_VER"
    _rpt "uv already installed: \`$UV_VER\`"
else
    info "Downloading and installing uv from astral.sh…"
    run_cmd "curl -LsSf https://astral.sh/uv/install.sh | sh"
    export PATH="$HOME/.local/bin:$PATH"
    UV_VER=$(uv --version 2>&1)
    ok "uv installed: $UV_VER"
    _rpt "uv installed: \`$UV_VER\`"
fi

# Persist PATH to shell rc files
_rpt ""
_rpt "**PATH persistence:**"
for RC in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [[ -f "$RC" ]] && ! grep -q '\.local/bin' "$RC"; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$RC"
        ok "Added ~/.local/bin to PATH in $RC"
        _rpt "  - Added to \`$RC\`"
    else
        [[ -f "$RC" ]] && { ok "$RC already has ~/.local/bin"; _rpt "  - \`$RC\` — already present"; }
    fi
done

# ---------------------------------------------------------------------------
# 3. Python environment
# ---------------------------------------------------------------------------
step "3 — Python 3.11 Virtual Environment (uv)"

info "Changing to repo directory: $REPO_DIR"
cd "$REPO_DIR"

info "Pinning Python 3.11…"
run_cmd "uv python pin 3.11"

info "Syncing virtual environment (uv sync)…"
run_interactive "uv sync"

VENV_PYTHON=$(uv run python --version 2>&1)
ok "Virtual environment ready — $VENV_PYTHON"
_rpt ""
_rpt "- Venv path: \`$REPO_DIR/.venv\`"
_rpt "- Python: \`$VENV_PYTHON\`"

# ---------------------------------------------------------------------------
# 4. Smoke-test CLI
# ---------------------------------------------------------------------------
step "4 — CLI Smoke Tests"

info "Testing archiver --help…"
HELP_OUT=$(uv run archiver --help 2>&1 | head -8)
echo "$HELP_OUT" | sed 's/^/      /'
ok "archiver --help returned output"
_rpt "**archiver --help (first 8 lines):**"
_rpt "\`\`\`"
while IFS= read -r l; do _rpt "$l"; done <<< "$HELP_OUT"
_rpt "\`\`\`"

echo ""
info "Testing registry list (drives not mounted yet — non-fatal)…"
LIST_OUT=$(uv run archiver list --tier A 2>&1 | head -6) || true
echo "$LIST_OUT" | sed 's/^/      /'
_rpt ""
_rpt "**archiver list --tier A (first 6 lines):**"
_rpt "\`\`\`"
while IFS= read -r l; do _rpt "$l"; done <<< "$LIST_OUT"
_rpt "\`\`\`"
ok "Registry list executed (drives not mounted yet is expected)"

# ---------------------------------------------------------------------------
# 5. Mount point directories
# ---------------------------------------------------------------------------
step "5 — Mount Point Directories"

info "Creating /mnt/models/dN directories…"
_rpt "| Directory | Created | Owner |"
_rpt "|-----------|---------|-------|"

for d in d1 d2 d3 d5; do
    mp="/mnt/models/$d"
    if [[ -d "$mp" ]]; then
        ok "$mp — already exists"
        _rpt "| \`$mp\` | already exists | $(stat -c '%U:%G' "$mp" 2>/dev/null || echo '?') |"
    else
        sudo mkdir -p "$mp"
        sudo chown "$(id -u):$(id -g)" "$mp"
        ok "$mp — created"
        _rpt "| \`$mp\` | created | $(id -un):$(id -gn) |"
    fi
done

# ---------------------------------------------------------------------------
# 6. Shell alias
# ---------------------------------------------------------------------------
step "6 — Shell Alias (archiver-screen)"

ALIAS_LINE="alias archiver-screen='cd $REPO_DIR && screen -S archiver uv run archiver'"
_rpt "Alias: \`$ALIAS_LINE\`"
_rpt ""

for RC in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [[ -f "$RC" ]]; then
        if grep -q 'archiver-screen' "$RC"; then
            ok "archiver-screen already in $RC"
            _rpt "- \`$RC\` — already present"
        else
            echo "$ALIAS_LINE" >> "$RC"
            ok "Added archiver-screen alias to $RC"
            _rpt "- \`$RC\` — added"
        fi
    fi
done

# ---------------------------------------------------------------------------
# Final summary
# ---------------------------------------------------------------------------
step "Setup Complete"

UV_VER_FINAL=$(uv --version 2>&1)
PY_VER_FINAL=$(uv run python --version 2>&1)
ARIA_VER=$(aria2c --version 2>&1 | head -1)

echo -e "${_C_GREEN}  ┌──────────────────────────────────────────────────────────────┐${_C_RESET}"
echo -e "${_C_GREEN}  │  ✔  MX Linux setup complete                                  │${_C_RESET}"
echo -e "${_C_GREEN}  └──────────────────────────────────────────────────────────────┘${_C_RESET}"
echo ""
printf "  %-20s %s\n" "uv:"     "$UV_VER_FINAL"
printf "  %-20s %s\n" "Python:" "$PY_VER_FINAL"
printf "  %-20s %s\n" "aria2c:" "$ARIA_VER"
printf "  %-20s %s\n" "Repo:"   "$REPO_DIR"
echo ""
echo -e "${_C_BOLD}  Next steps:${_C_RESET}"
echo "  1. Run the disk setup script (wipes + mounts the 4 drives):"
echo "       sudo bash deploy/vm-mount-disks.sh --wipe"
echo ""
echo "  2. (Optional) Set HuggingFace token for gated models:"
echo "       export HF_TOKEN=hf_..."
echo "       echo 'export HF_TOKEN=hf_...' >> ~/.bashrc"
echo ""
echo "  3. Dry-run to verify the plan:"
echo "       cd $REPO_DIR && uv run archiver download --all --dry-run"
echo ""
echo "  4. Start downloads in a screen session:"
echo "       screen -S archiver"
echo "       uv run archiver download --all --priority-only 1"
echo "       # Detach: Ctrl-A D    Reattach: screen -r archiver"
echo ""

_rpt "| Component | Version |"
_rpt "|-----------|---------|"
_rpt "| uv | $UV_VER_FINAL |"
_rpt "| Python | $PY_VER_FINAL |"
_rpt "| aria2c | $ARIA_VER |"
_rpt "| Repo | \`$REPO_DIR\` |"

finish_report "SUCCESS"
print_report_path
