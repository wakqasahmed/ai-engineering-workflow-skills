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
# binary in $PATH - this is checked before anything is written, so a failed
# install leaves nothing behind.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER_SRC="$SCRIPT_DIR/git-identity-guard.sh"

REQUIRED_NAME="${1:-$(git config --global user.name || true)}"
REQUIRED_EMAIL="${2:-$(git config --global user.email || true)}"
INSTALL_DIR="${3:-$HOME/.local/bin}"
CONFIG_DIR="$HOME/.config/git-identity-guard"
CONFIG_FILE="$CONFIG_DIR/config"

case "$INSTALL_DIR" in
  /*) ;;
  *) INSTALL_DIR="$PWD/$INSTALL_DIR" ;;
esac
if [ -d "$INSTALL_DIR" ]; then
  INSTALL_DIR="$(cd "$INSTALL_DIR" && pwd -P)"
fi

if [ -z "$REQUIRED_NAME" ] || [ -z "$REQUIRED_EMAIL" ]; then
  echo "No required name/email given and no 'git config --global user.name'/'user.email' set." >&2
  echo "Usage: install.sh <required-name> <required-email> [install-dir]" >&2
  exit 1
fi

# The config is parsed line by line by the wrapper, so a newline in either
# value would silently truncate or forge an entry.
case "$REQUIRED_NAME$REQUIRED_EMAIL" in
  *$'\n'*)
    echo "Required name/email must not contain a newline." >&2
    exit 1
    ;;
esac

if [ ! -f "$WRAPPER_SRC" ]; then
  echo "Cannot find git-identity-guard.sh next to this script at $WRAPPER_SRC" >&2
  exit 1
fi

# Verify $PATH feasibility BEFORE writing anything: the guard is worthless if
# the real git is found first, and a failed install must not leave a config,
# a wrapper, or a rewritten global identity behind.
path_puts_wrapper_first() {
  local dir dir_abs
  local -a dirs=()
  IFS=':' read -ra dirs <<< "$PATH"
  for dir in "${dirs[@]+"${dirs[@]}"}"; do
    [ -n "$dir" ] || continue
    dir_abs="$dir"
    if [ -d "$dir" ]; then
      dir_abs="$(cd "$dir" && pwd -P)"
    fi
    if [ "$dir_abs" = "$INSTALL_DIR" ]; then
      return 0
    fi
    if [ -x "$dir/git" ]; then
      return 1
    fi
  done
  return 1
}

if ! path_puts_wrapper_first; then
  echo "ABORTED: the guard would be installed but NOT ACTIVE." >&2
  echo "$INSTALL_DIR is not ahead of the real git in \$PATH for this shell," >&2
  echo "so 'git' would keep resolving to the real binary and nothing would be checked." >&2
  echo "Add this to your shell rc (~/.bashrc / ~/.zshrc), open a new shell, and re-run:" >&2
  echo "  export PATH=\"$INSTALL_DIR:\$PATH\"" >&2
  echo "Nothing was written." >&2
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
echo "Setting global git user.name/user.email to '$REQUIRED_NAME <$REQUIRED_EMAIL>' (overwriting any current global value)."
git config --global user.name "$REQUIRED_NAME"
git config --global user.email "$REQUIRED_EMAIL"

hash -r 2>/dev/null || true
resolved="$(command -v git || true)"
resolved_real="$(readlink -f "$resolved" 2>/dev/null || echo "$resolved")"
wrapper_real="$(readlink -f "$INSTALL_DIR/git" 2>/dev/null || echo "$INSTALL_DIR/git")"

echo ""
if [ "$resolved_real" = "$wrapper_real" ]; then
  echo "OK: 'which git' resolves to the wrapper ($resolved)."
else
  echo "WARNING: installed but NOT ACTIVE - 'which git' still resolves to $resolved." >&2
  echo "Open a new shell (or re-hash this one) and re-check before relying on this." >&2
  exit 1
fi

echo ""
echo "Run the verification steps in SKILL.md before trusting this in a new environment."
