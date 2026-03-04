#!/usr/bin/env bash
# =============================================================================
# deploy/setup-artix.sh
# Bootstrap model-archival on Artix Linux (Arch/pacman-based, dinit init system)
#
# Usage:
#   bash setup-artix.sh [--repo-dir /path/to/model-archival]
#
# What this script does:
#   1. Installs system packages: python, aria2, git, screen, rsync
#   2. Installs uv (Astral) for the current user
#   3. Creates / syncs the Python virtual environment via uv
#   4. Installs the archiver package in editable mode
#   5. Verifies the CLI entry point is accessible
#   6. Prints a quick-start reminder
#
# Run as a normal user with sudo privileges (NOT as root).
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { echo -e "\033[1;32m[INFO]\033[0m  $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
error() { echo -e "\033[1;31m[ERROR]\033[0m $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-dir) REPO_DIR="$2"; shift 2 ;;
    *) error "Unknown argument: $1" ;;
  esac
done

info "Repository directory: $REPO_DIR"
[[ -f "$REPO_DIR/pyproject.toml" ]] || error "pyproject.toml not found in $REPO_DIR — is --repo-dir correct?"

# ---------------------------------------------------------------------------
# 1. System packages (pacman)
# ---------------------------------------------------------------------------
info "Syncing pacman database…"
sudo pacman -Sy --noconfirm

info "Installing system dependencies…"
sudo pacman -S --noconfirm --needed \
  python \
  aria2 \
  git \
  screen \
  rsync \
  curl \
  wget \
  ca-certificates \
  htop \
  nvme-cli

# python-pip is bundled with python on Arch; python-virtualenv is not needed
# (uv manages its own venvs)

# Verify aria2c
aria2c --version | head -1 && info "aria2c OK"

# ---------------------------------------------------------------------------
# 2. Install uv (user-local, no sudo needed)
# ---------------------------------------------------------------------------
if command -v uv &>/dev/null; then
  info "uv already installed: $(uv --version)"
else
  info "Installing uv…"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  info "uv installed: $(uv --version)"
fi

export PATH="$HOME/.local/bin:$PATH"

for RC in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.config/fish/config.fish"; do
  if [[ -f "$RC" ]] && ! grep -q '\.local/bin' "$RC"; then
    if [[ "$RC" == *.fish ]]; then
      echo 'fish_add_path "$HOME/.local/bin"' >> "$RC"
    else
      echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$RC"
    fi
    info "Added ~/.local/bin to PATH in $RC"
  fi
done

# ---------------------------------------------------------------------------
# 3. Pin Python version and sync virtual environment
# ---------------------------------------------------------------------------
info "Setting up Python 3.11 environment with uv…"
cd "$REPO_DIR"

uv python pin 3.11
uv sync

info "Virtual environment ready at $REPO_DIR/.venv"

# ---------------------------------------------------------------------------
# 4. Smoke-test the CLI
# ---------------------------------------------------------------------------
info "Testing archiver CLI…"
uv run archiver --help | head -5

info "Testing registry load…"
uv run archiver list --tier A 2>/dev/null | head -5 || warn "Registry list returned non-zero (drives not mounted yet — expected)"

# ---------------------------------------------------------------------------
# 5. Drive mount directories
# ---------------------------------------------------------------------------
info "Creating mount point directories under /mnt/models/…"
for d in d1 d2 d3 d4 d5; do
  sudo mkdir -p "/mnt/models/$d"
  sudo chown "$(id -u):$(id -g)" "/mnt/models/$d"
done
info "Mount points created. Add entries to /etc/fstab to auto-mount your drives."

# ---------------------------------------------------------------------------
# 6. Screen helper alias
# ---------------------------------------------------------------------------
ALIAS_LINE='alias archiver-screen="cd $REPO_DIR && screen -S archiver uv run archiver"'
for RC in "$HOME/.bashrc" "$HOME/.zshrc"; do
  if [[ -f "$RC" ]] && ! grep -q 'archiver-screen' "$RC"; then
    echo "$ALIAS_LINE" >> "$RC"
  fi
done

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
echo "  Setup complete — Artix Linux (Arch/dinit)"
echo "============================================================"
echo ""
echo "  Next steps:"
echo "  1. Mount your drives and update /etc/fstab, e.g.:"
echo "       UUID=xxxx-xxxx  /mnt/models/d1  ext4  noatime,nodiratime,defaults  0 2"
echo ""
echo "  2. Edit config/drives.yaml to match your mount points:"
echo "       $REPO_DIR/config/drives.yaml"
echo ""
echo "  3. (Optional) Set your HF token for gated models:"
echo "       export HF_TOKEN=hf_..."
echo "       # or add it to ~/.bashrc"
echo ""
echo "  4. Dry-run to confirm everything looks right:"
echo "       cd $REPO_DIR"
echo "       uv run archiver download --all --dry-run"
echo ""
echo "  5. Start the archive in a screen session:"
echo "       screen -S archiver"
echo "       uv run archiver download --all"
echo "       # Detach: Ctrl-A D   Reattach: screen -r archiver"
echo ""
echo "  STATUS.md is written to the working directory and updated every ~60s."
echo ""
