#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOK="$REPO_ROOT/skills/engineering/git-guardrails-claude-code/scripts/block-dangerous-git.sh"

assert_status() {
  local expected_status="$1"
  local command="$2"
  local description="$3"
  local output
  local status

  set +e
  output=$(jq -n --arg command "$command" '{"tool_input":{"command":$command}}' | "$HOOK" 2>&1)
  status=$?
  set -e

  if [ "$status" -ne "$expected_status" ]; then
    printf 'FAIL: %s\ncommand: %s\nexpected: %s\nactual: %s\noutput: %s\n' \
      "$description" "$command" "$expected_status" "$status" "$output" >&2
    exit 1
  fi
}

assert_status 2 'git push origin main' 'blocks direct push to a protected branch'
assert_status 2 'git push --force-with-lease origin feature/topic' 'blocks force-with-lease push'
assert_status 2 'git reset --hard origin/main' 'blocks hard reset'
assert_status 2 'git clean -fd' 'blocks forced clean'
assert_status 2 'git branch -D obsolete' 'blocks forced branch deletion'
assert_status 2 'git checkout .' 'blocks bare checkout discard'
assert_status 2 'git restore -- .' 'blocks bare restore discard'

assert_status 2 'git -C /tmp/example push origin main' 'blocks protected push after -C'
assert_status 2 'git -c core.askPass=true push --force origin feature/topic' 'blocks force push after -c'
assert_status 2 'git --git-dir=/tmp/example/repository reset --hard' 'blocks hard reset after --git-dir'
assert_status 2 'git --git-dir /tmp/example/repository restore .' 'consumes a separate --git-dir argument'
assert_status 2 '/usr/bin/git -C /tmp/example clean -fd' 'recognizes an absolute Git executable path'
assert_status 2 'printf "safe\n" && git -c color.ui=false branch -D obsolete' 'blocks a dangerous compound-command segment'

assert_status 0 'git -C /tmp/example push origin feature/topic' 'allows feature-branch push after -C'
assert_status 0 '/usr/bin/git -c color.ui=false push origin feature/topic' 'allows feature-branch push through an absolute Git path'
assert_status 0 'git -C push status origin main' 'does not mistake a global-option argument for the subcommand'
assert_status 0 'git reset --harder' 'does not match a longer reset option'
assert_status 0 'git checkout .bashrc' 'does not match a longer path'
assert_status 0 'gh issue create --body "discusses git -C /tmp push origin main and git reset --hard"' 'allows quoted prose'
assert_status 0 "printf '%s\\n' 'safe && git -c color.ui=false push --force origin feature/topic'" 'ignores shell operators and Git prose inside quotes'

printf 'git guardrails tests passed\n'
