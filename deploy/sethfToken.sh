#!/usr/bin/env bash
# =============================================================================
# deploy/sethfToken.sh
# Set and persist the HuggingFace token for the current user.
#
# Usage:
#   bash deploy/sethfToken.sh hf_XXXXXXXXXXXXXXXXXXXX
#
# The token is written to ~/.hf_token (chmod 600) and sourced from ~/.bashrc.
# It is never stored in the repository.
# =============================================================================
set -euo pipefail

TOKEN="${1:-}"

if [[ -z "$TOKEN" ]]; then
    # Try reading from ~/.hf_token if already set
    if [[ -f "$HOME/.hf_token" ]]; then
        TOKEN=$(cat "$HOME/.hf_token")
        echo "Using existing token from ~/.hf_token"
    else
        echo "Usage: bash deploy/sethfToken.sh hf_XXXXXXXXXXXXXXXXXXXX" >&2
        exit 1
    fi
fi

# Validate format
if [[ ! "$TOKEN" =~ ^hf_[A-Za-z0-9]{10,}$ ]]; then
    echo "WARNING: token format looks unusual (expected hf_XXXX...)" >&2
fi

# Store securely outside the repo
TOKEN_FILE="$HOME/.hf_token"
echo "$TOKEN" > "$TOKEN_FILE"
chmod 600 "$TOKEN_FILE"
echo "Token written to $TOKEN_FILE (chmod 600)"

# Export for current session
export HF_TOKEN="$TOKEN"
echo "HF_TOKEN exported for current session"

# Persist in shell rc — add only if not already present
SHELL_RC="$HOME/.bashrc"
[[ -f "$HOME/.zshrc" ]] && SHELL_RC="$HOME/.zshrc"

EXPORT_LINE='export HF_TOKEN=$(cat ~/.hf_token)'
if ! grep -qF "$EXPORT_LINE" "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"
    echo "# HuggingFace token (set by deploy/sethfToken.sh)" >> "$SHELL_RC"
    echo "$EXPORT_LINE" >> "$SHELL_RC"
    echo "Persisted to $SHELL_RC"
else
    echo "Already persisted in $SHELL_RC"
fi

echo ""
echo "Token is set. Verify with:  echo \$HF_TOKEN | head -c 10"
