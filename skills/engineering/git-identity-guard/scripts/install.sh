#!/bin/bash
# Installs git-identity-guard: a $PATH shim that hard-blocks any commit or
# push whose author/committer identity doesn't match one configured
# name/email, everywhere on this machine, no override.
#
# Usage:
#   install.sh <required-name> <required-email> [install-dir]
#
# If <required-name>/<required-email> are omitted, falls back to the current
# `git config --global user.name`/`user.email` (which is the common case:
# the global identity is already correct, and the problem being solved is
# that per-command overrides keep undermining it).
#
# [install-dir] defaults to ~/.local/bin. It must come before the real git
# binary in $PATH - the script checks this and warns if it doesn't.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER_SRC="$SCRIPT_DIR/git-identity-guard.sh"

REQUIRED_NAME="${1:-$(git config --global user.name || true)}"
REQUIRED_EMAIL="${2:-$(git config --global user.email || true)}"
INSTALL_DIR="${3:-$HOME/.local/bin}"
CONFIG_DIR="$HOME/.config/git-identity-guard"
CONFIG_FILE="$CONFIG_DIR/config"

if [ -z "$REQUIRED_NAME" ] || [ -z "$REQUIRED_EMAIL" ]; then
  echo "No required name/email given and no 'git config --global user.name'/'user.email' set." >&2
  echo "Usage: install.sh <required-name> <required-email> [install-dir]" >&2
  exit 1
fi

if [ ! -f "$WRAPPER_SRC" ]; then
  echo "Cannot find git-identity-guard.sh next to this script at $WRAPPER_SRC" >&2
  exit 1
fi

mkdir -p "$CONFIG_DIR"
cat > "$CONFIG_FILE" <<EOF
# Config for the git-identity-guard wrapper. Every commit made anywhere on
# this machine must be attributed to exactly this name/email.
REQUIRED_NAME="$REQUIRED_NAME"
REQUIRED_EMAIL="$REQUIRED_EMAIL"
EOF
echo "Wrote $CONFIG_FILE"

mkdir -p "$INSTALL_DIR"
cp "$WRAPPER_SRC" "$INSTALL_DIR/git"
chmod +x "$INSTALL_DIR/git"
echo "Installed wrapper at $INSTALL_DIR/git"

# Make sure the global git config's own default matches too, so any tool
# that reads config directly (without going through this wrapper's checks,
# e.g. an editor plugin) still gets the right identity by default.
git config --global user.name "$REQUIRED_NAME"
git config --global user.email "$REQUIRED_EMAIL"

resolved="$(command -v git || true)"
resolved_real="$(readlink -f "$resolved" 2>/dev/null || echo "$resolved")"
wrapper_real="$(readlink -f "$INSTALL_DIR/git" 2>/dev/null || echo "$INSTALL_DIR/git")"

echo ""
if [ "$resolved_real" = "$wrapper_real" ]; then
  echo "OK: 'which git' resolves to the wrapper ($resolved)."
else
  echo "WARNING: 'which git' still resolves to $resolved, not the wrapper." >&2
  echo "$INSTALL_DIR is not ahead of the real git in \$PATH for this shell." >&2
  echo "Add this to your shell rc (~/.bashrc / ~/.zshrc) and open a new shell:" >&2
  echo "  export PATH=\"$INSTALL_DIR:\$PATH\"" >&2
  exit 1
fi

echo ""
echo "Run the verification steps in SKILL.md before trusting this in a new environment."
