#!/bin/bash
#
# PreToolUse hook (Bash matcher): blocks a fixed list of destructive/hard-to-reverse
# git commands before Claude Code executes them.
#
# Source: mattpocock/skills — misc/git-guardrails-claude-code
# https://github.com/mattpocock/skills/blob/main/skills/misc/git-guardrails-claude-code/SKILL.md
# Adapted 2026-08-26: upstream blocks ALL `git push`; this version narrows that to
# force-push and direct pushes to protected branches only, per this repo's own
# git-workflow rules (system-level/core.md), which forbid force-push and direct
# commits/pushes to main/staging but require routine feature-branch pushes for
# the standard PR workflow (worktree -> branch -> push -> PR).

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

[ -z "$COMMAND" ] && exit 0

# All patterns require a literal "git <subcommand>" prefix, not just the bare
# word (e.g. "push", "reset --hard") — an earlier version matched those loosely
# and false-positived on prose mentioning git commands (e.g. a GitHub issue
# body describing this hook's own behavior). The push patterns also cap the
# gap between "git push" and its flag/branch target to a short window so a
# sentence that merely mentions "git push" and "main" far apart in the same
# line of prose doesn't trigger.
DANGEROUS_PATTERNS=(
  "git reset --hard"
  "git clean -fd"
  "git clean -f"
  "git branch -D"
  "git checkout \."
  "git restore \."
  "git push[^&|;]{0,30}(--force|--force-with-lease|-f\b)"
  "git push[^&|;]{0,20}(origin[[:space:]]+)?(HEAD:)?(main|master|staging)\b"
)

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if echo "$COMMAND" | grep -qE "$pattern"; then
    echo "BLOCKED: '$COMMAND' matches dangerous pattern '$pattern'. Force-push, direct pushes to main/master/staging, reset --hard, clean -f/-fd, branch -D, and bare checkout/restore . are not permitted. The user has prevented you from doing this." >&2
    exit 2
  fi
done

exit 0
