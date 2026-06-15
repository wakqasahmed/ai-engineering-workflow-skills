#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_HOME="${HOME}"
DRY_RUN=false
FORCE=false
BACKUP_DIR=""

usage() {
  cat <<'USAGE'
Usage:
  scripts/install-user.sh [--target-home <path>] [--backup-dir <path>] [--dry-run] [--force]

Installs the workflow entrypoints into a user's agent instruction locations:
  AGENTS.md          -> <target-home>/AGENTS.md
  CLAUDE.md          -> <target-home>/.claude/CLAUDE.md

Options:
  --target-home DIR  Install under DIR instead of $HOME.
  --backup-dir DIR   Store backups in DIR. Defaults to <target-home>/.ai-engineering-workflow-backups/<timestamp>.
  --dry-run          Show actions and conflicts without writing files.
  --force            Overwrite differing files after backing them up.
  --help             Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-home)
      TARGET_HOME="${2:?--target-home requires a path}"
      shift 2
      ;;
    --backup-dir)
      BACKUP_DIR="${2:?--backup-dir requires a path}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --force)
      FORCE=true
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${BACKUP_DIR}" ]]; then
  BACKUP_DIR="${TARGET_HOME}/.ai-engineering-workflow-backups/$(date -u +%Y%m%dT%H%M%SZ)"
fi

install_file() {
  local src="$1"
  local dest="$2"
  local backup_name="$3"

  if [[ -f "$dest" ]] && cmp -s "$src" "$dest"; then
    echo "unchanged: $dest"
    return 0
  fi

  if [[ -e "$dest" && "$FORCE" != "true" ]]; then
    echo "conflict: $dest differs from $(basename "$src")"
    echo "         rerun with --force to back it up and replace it"
    return 2
  fi

  if [[ "$DRY_RUN" == "true" ]]; then
    if [[ -e "$dest" ]]; then
      echo "would backup: $dest -> ${BACKUP_DIR}/${backup_name}"
    fi
    echo "would install: $src -> $dest"
    return 0
  fi

  mkdir -p "$(dirname "$dest")"

  if [[ -e "$dest" ]]; then
    mkdir -p "$BACKUP_DIR"
    cp "$dest" "${BACKUP_DIR}/${backup_name}"
    echo "backup: $dest -> ${BACKUP_DIR}/${backup_name}"
  fi

  cp "$src" "$dest"
  echo "installed: $dest"
}

main() {
  local status=0

  install_file "${REPO_ROOT}/AGENTS.md" "${TARGET_HOME}/AGENTS.md" "AGENTS.md" || status=$?
  install_file "${REPO_ROOT}/CLAUDE.md" "${TARGET_HOME}/.claude/CLAUDE.md" "CLAUDE.md" || status=$?

  if [[ "$status" -eq 2 ]]; then
    echo "install blocked by differing existing files" >&2
  fi

  return "$status"
}

main
