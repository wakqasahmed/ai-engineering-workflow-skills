#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOK="$REPO_ROOT/skills/engineering/git-guardrails-claude-code/scripts/block-dangerous-git.sh"
if [ ! -x "$HOOK" ]; then
  printf 'Error: Hook script not found or not executable: %s\n' "$HOOK" >&2
  exit 1
fi

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
assert_status 2 'command git push origin main' 'blocks a protected push through command'
assert_status 2 'env git -C /tmp/example reset --hard' 'blocks a hard reset through env'
assert_status 2 'sudo git push --force origin feature/topic' 'blocks a force push through sudo'
assert_status 2 'command -p env -i X=1 git push origin staging' 'consumes command and env options and assignments'
assert_status 2 'sudo -n -u root git branch -D obsolete' 'consumes sudo options'

assert_status 0 'git -C /tmp/example push origin feature/topic' 'allows feature-branch push after -C'
assert_status 0 '/usr/bin/git -c color.ui=false push origin feature/topic' 'allows feature-branch push through an absolute Git path'
assert_status 0 'env -i GIT_CONFIG_NOSYSTEM=1 git push origin feature/topic' 'allows a feature-branch push through env'
assert_status 0 'sudo -n -u root git push origin feature/topic' 'allows a feature-branch push through sudo'
assert_status 0 'git -C push status origin main' 'does not mistake a global-option argument for the subcommand'
assert_status 0 'git reset --harder' 'does not match a longer reset option'
assert_status 0 'git checkout .bashrc' 'does not match a longer path'
assert_status 0 'gh issue create --body "discusses git -C /tmp push origin main and git reset --hard"' 'allows quoted prose'
assert_status 0 "printf '%s\\n' 'safe && git -c color.ui=false push --force origin feature/topic'" 'ignores shell operators and Git prose inside quotes'

# Command/process substitution cannot be evaluated without executing it, so a
# tainted subcommand or dangerous flag is fail-closed rather than allowed
# through unrecognized.
assert_status 2 'git $(echo reset) --hard' 'blocks a hard reset with the subcommand hidden behind command substitution'
assert_status 2 'git `echo reset` --hard' 'blocks a hard reset with the subcommand hidden behind backtick substitution'
assert_status 2 'git reset $(echo --hard)' 'blocks a hard reset with --hard hidden behind command substitution'
assert_status 2 'git push $(echo --force) origin feature/topic' 'blocks a force push with --force hidden behind command substitution'
assert_status 0 'git commit -m "Release $(date +%F)"' 'allows a command substitution inside an ordinary commit message'
assert_status 0 'BRANCH="feature/$(date +%s)"; git push origin "$BRANCH"' 'allows a dynamic feature-branch name computed in an earlier command'

# A backslash-newline line continuation used to split a dangerous command
# across a fake segment boundary so neither half matched on its own.
assert_status 2 $'git reset \\\n--hard' 'blocks a hard reset split by an escaped line continuation'

# Real shell double-quote escaping: backslash only escapes $, `, ", \, or a
# newline inside double quotes; any other backslash is literal and does not
# end the quoted string early.
assert_status 0 'git commit -m "say \"hard\" reset"' 'keeps an escaped quote inside a double-quoted commit message as one opaque argument'

printf 'git guardrails tests passed\n'
