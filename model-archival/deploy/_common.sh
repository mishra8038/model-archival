#!/usr/bin/env bash
# =============================================================================
# deploy/_common.sh
# Shared helpers for all deploy scripts.
# Source with:  source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
# =============================================================================

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
_C_RESET="\033[0m"
_C_GREEN="\033[1;32m"
_C_YELLOW="\033[1;33m"
_C_RED="\033[1;31m"
_C_CYAN="\033[1;36m"
_C_MAGENTA="\033[1;35m"
_C_DIM="\033[2m"
_C_BOLD="\033[1m"

# ---------------------------------------------------------------------------
# Report state
# ---------------------------------------------------------------------------
_REPORT_FILE=""
_REPORT_LINES=()

# Call once at script startup:
#   init_report "script-name"
init_report() {
    local script_name="$1"
    local dir
    dir="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
    _REPORT_FILE="$dir/${script_name}-report-$(date +%Y-%m-%d_%H-%M-%S).md"
    _REPORT_LINES=()

    local hostname user runtime
    hostname=$(hostname 2>/dev/null || echo "unknown")
    user=$(whoami 2>/dev/null || echo "unknown")
    runtime=$(date '+%Y-%m-%d %H:%M:%S %Z')

    _rpt "# $script_name — Execution Report"
    _rpt ""
    _rpt "| Field | Value |"
    _rpt "|-------|-------|"
    _rpt "| Script | \`$script_name\` |"
    _rpt "| Host | $hostname |"
    _rpt "| User | $user |"
    _rpt "| Started | $runtime |"
    _rpt ""
    _rpt "---"
}

flush_report() {
    [[ -z "$_REPORT_FILE" ]] && return
    printf '%s\n' "${_REPORT_LINES[@]}" > "$_REPORT_FILE"
}

_rpt() { _REPORT_LINES+=("$*"); }

# ---------------------------------------------------------------------------
# Timestamp
# ---------------------------------------------------------------------------
TS() { date '+%H:%M:%S'; }

# ---------------------------------------------------------------------------
# Console + report logging
# ---------------------------------------------------------------------------
info() {
    echo -e "${_C_GREEN}[$(TS) INFO]${_C_RESET}  $*"
    _rpt "  ✓ $*"
}

warn() {
    echo -e "${_C_YELLOW}[$(TS) WARN]${_C_RESET}  $*"
    _rpt "  ⚠ $*"
}

error() {
    echo -e "${_C_RED}[$(TS) ERROR]${_C_RESET} $*" >&2
    _rpt ""
    _rpt "## ✗ FAILED"
    _rpt ""
    _rpt "> **ERROR**: $*"
    _rpt ""
    _rpt "Script terminated at $(date '+%Y-%m-%d %H:%M:%S %Z')"
    flush_report
    [[ -n "$_REPORT_FILE" ]] && echo -e "  Report saved → ${_C_BOLD}$_REPORT_FILE${_C_RESET}" >&2
    exit 1
}

ok() {
    echo -e "      ${_C_GREEN}✔${_C_RESET}  $*"
    _rpt "  - ✔ $*"
}

# ---------------------------------------------------------------------------
# Section headers
# ---------------------------------------------------------------------------
step() {
    local title="$*"
    echo ""
    echo -e "${_C_CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${_C_RESET}"
    echo -e "${_C_CYAN}  ▸  $title${_C_RESET}"
    echo -e "${_C_CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${_C_RESET}"
    echo ""
    _rpt ""
    _rpt "## $title"
    _rpt ""
}

banner() {
    # Highlight banner for major items (disk, package group, etc.)
    local label="$*"
    echo ""
    echo -e "${_C_MAGENTA}  ▶  $label  ${_C_RESET}"
    echo ""
    _rpt ""
    _rpt "### $label"
    _rpt ""
}

# ---------------------------------------------------------------------------
# Command runner — shows command, captures output, writes to report
# ---------------------------------------------------------------------------
run_cmd() {
    # run_cmd [--silent] <command...>
    # --silent suppresses stdout on console (output still goes to report)
    local silent=false
    [[ "${1:-}" == "--silent" ]] && { silent=true; shift; }

    local cmd="$*"
    echo -e "      ${_C_DIM}\$ $cmd${_C_RESET}"
    _rpt "  - \`$cmd\`"

    local out rc=0
    out=$(eval "$cmd" 2>&1) || rc=$?

    if [[ -n "$out" ]]; then
        if ! $silent; then
            echo "$out" | sed 's/^/        /'
        fi
        _rpt "  \`\`\`"
        while IFS= read -r l; do _rpt "  $l"; done <<< "$out"
        _rpt "  \`\`\`"
    fi

    if [[ $rc -ne 0 ]]; then
        echo -e "      ${_C_RED}✗  exit code $rc${_C_RESET}"
        _rpt "  - ✗ exit code $rc"
    fi

    return $rc
}

# Like run_cmd but always shows output (never silent), passes stdin/tty
run_interactive() {
    local cmd="$*"
    echo -e "      ${_C_DIM}\$ $cmd${_C_RESET}"
    _rpt "  - \`$cmd\`"
    eval "$cmd"
    local rc=$?
    [[ $rc -ne 0 ]] && _rpt "  - ✗ exit code $rc"
    return $rc
}

# ---------------------------------------------------------------------------
# tmux-powerline (no stable Debian/Arch package — upstream git)
# ---------------------------------------------------------------------------
# After installing tmux + powerline + fonts via the distro, call this to clone
# https://github.com/erikw/tmux-powerline into ~/.tmux-powerline.
# Override URL: TMUX_POWERLINE_URL=https://github.com/...
install_tmux_powerline_repo() {
    local dest="${HOME}/.tmux-powerline"
    local url="${TMUX_POWERLINE_URL:-https://github.com/erikw/tmux-powerline.git}"
    if [[ -d "$dest/.git" ]]; then
        ok "tmux-powerline repo already present at $dest"
        _rpt "tmux-powerline: already at \`$dest\`"
        return 0
    fi
    if ! command -v git &>/dev/null; then
        warn "git not available — skipping tmux-powerline clone"
        _rpt "tmux-powerline: skipped (no git)"
        return 0
    fi
    info "Cloning tmux-powerline → $dest …"
    if git clone --depth 1 "$url" "$dest" &>/dev/null; then
        ok "tmux-powerline cloned — wire ~/.tmux.conf per upstream README"
        _rpt "tmux-powerline: cloned \`$dest\`"
    else
        warn "tmux-powerline clone failed"
        _rpt "tmux-powerline: clone ⚠ FAILED"
    fi
}

# ---------------------------------------------------------------------------
# Oh My Fish (requires fish + git; curl installer from upstream)
# ---------------------------------------------------------------------------
# Set OMF_SKIP=1 to skip. Uses ~/.local/share/omf (or $XDG_DATA_HOME/omf).
install_oh_my_fish() {
    if [[ "${OMF_SKIP:-}" == "1" ]]; then
        info "Skipping Oh My Fish (OMF_SKIP=1)"
        _rpt "omf: skipped (OMF_SKIP=1)"
        return 0
    fi
    if ! command -v fish &>/dev/null; then
        warn "fish not in PATH — skipping Oh My Fish"
        _rpt "omf: skipped (no fish)"
        return 0
    fi
    if ! command -v git &>/dev/null; then
        warn "git not available — skipping Oh My Fish"
        _rpt "omf: skipped (no git)"
        return 0
    fi
    local omf_base="${XDG_DATA_HOME:-$HOME/.local/share}/omf"
    if [[ -d "$omf_base/pkg/omf" ]]; then
        ok "Oh My Fish already present at $omf_base"
        _rpt "omf: already at \`$omf_base\`"
        return 0
    fi
    if fish -c 'omf --version' &>/dev/null; then
        ok "Oh My Fish already available (\`omf --version\`)"
        _rpt "omf: already installed"
        return 0
    fi
    local url="${OMF_INSTALL_URL:-https://raw.githubusercontent.com/oh-my-fish/oh-my-fish/master/bin/install}"
    local tmp
    tmp=$(mktemp) || {
        warn "mktemp failed — skipping Oh My Fish"
        return 0
    }
    info "Downloading Oh My Fish installer…"
    if ! curl -fsSL "$url" -o "$tmp"; then
        warn "Could not download Oh My Fish installer"
        rm -f "$tmp"
        _rpt "omf: download ⚠ FAILED"
        return 0
    fi
    info "Running Oh My Fish install (non-interactive)…"
    if fish "$tmp" --noninteractive --yes; then
        ok "Oh My Fish installed — open fish and run \`omf theme\` / \`omf install\` as needed"
        _rpt "omf: installed"
    else
        warn "Oh My Fish install failed (try: fish, then re-run installer with --verbose)"
        _rpt "omf: install ⚠ FAILED"
    fi
    rm -f "$tmp"
}

# ---------------------------------------------------------------------------
# Final report footer
# ---------------------------------------------------------------------------
finish_report() {
    local status="${1:-SUCCESS}"
    local finish_time
    finish_time=$(date '+%Y-%m-%d %H:%M:%S %Z')
    _rpt ""
    _rpt "---"
    _rpt ""
    _rpt "## Result: $status"
    _rpt ""
    _rpt "Completed: $finish_time"
    flush_report
}

print_report_path() {
    [[ -n "$_REPORT_FILE" ]] || return
    echo ""
    echo -e "  ${_C_DIM}Report saved → ${_C_BOLD}$_REPORT_FILE${_C_RESET}"
}
