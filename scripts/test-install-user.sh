#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_HOME="$(mktemp -d)"
trap 'rm -rf "$TMP_HOME"' EXIT

bash -n "${REPO_ROOT}/scripts/install-user.sh"

"${REPO_ROOT}/scripts/install-user.sh" --target-home "$TMP_HOME" --dry-run > "$TMP_HOME/dry-run.log"
grep -q "would install: .*AGENTS.md" "$TMP_HOME/dry-run.log"
grep -q "would install: .*CLAUDE.md" "$TMP_HOME/dry-run.log"

"${REPO_ROOT}/scripts/install-user.sh" --target-home "$TMP_HOME" > "$TMP_HOME/install.log"
cmp -s "${REPO_ROOT}/AGENTS.md" "$TMP_HOME/AGENTS.md"
cmp -s "${REPO_ROOT}/CLAUDE.md" "$TMP_HOME/.claude/CLAUDE.md"

printf 'local custom instructions\n' > "$TMP_HOME/AGENTS.md"
if "${REPO_ROOT}/scripts/install-user.sh" --target-home "$TMP_HOME" > "$TMP_HOME/conflict.log" 2>&1; then
  echo "expected conflict without --force" >&2
  exit 1
fi
grep -q "conflict: .*AGENTS.md" "$TMP_HOME/conflict.log"

"${REPO_ROOT}/scripts/install-user.sh" --target-home "$TMP_HOME" --force > "$TMP_HOME/force.log"
cmp -s "${REPO_ROOT}/AGENTS.md" "$TMP_HOME/AGENTS.md"
test -f "$TMP_HOME/.ai-engineering-workflow-backups/"*/AGENTS.md

echo "install-user tests passed"
