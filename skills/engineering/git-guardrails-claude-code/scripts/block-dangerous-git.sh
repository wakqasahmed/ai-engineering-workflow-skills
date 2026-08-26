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
# Hardened 2026-08-26 per Open Code Review on PR #103: printf instead of echo
# (a COMMAND starting with a dash could be misread as an echo option),
# blank-run normalization so "git reset   --hard" (extra spaces) can't bypass
# a naive substring match, and word-boundary anchoring so "git reset --harder"
# or "git checkout .bashrc" don't false-positive against the plain-word forms.

INPUT=$(cat)
COMMAND=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty')

[ -z "$COMMAND" ] && exit 0

# Collapse runs of horizontal whitespace (space/tab) per line so "git reset
# --hard" and "git reset   --hard" match the same pattern. Deliberately uses
# [:blank:] (not [:space:]) so newlines are preserved and grep keeps matching
# line-by-line — collapsing newlines would reintroduce the cross-line prose
# false-positive this hook already had to fix once (a GitHub issue body
# mentioning "git push" and "main" on the same visual line, far apart).
NORM_COMMAND=$(printf '%s' "$COMMAND" | tr -s '[:blank:]' ' ')

# All patterns require a literal "git <subcommand>" prefix, not just the bare
# word (e.g. "push", "reset --hard") — an earlier version matched those loosely
# and false-positived on prose mentioning git commands. Bare patterns are also
# word-boundary anchored on the right (\b) so "git reset --harder" doesn't
# match "git reset --hard", and the checkout/restore-dot patterns require the
# dot be immediately followed by whitespace or end-of-line so "git checkout
# .bashrc" isn't blocked. The push patterns cap the gap between "git push"
# and its flag/branch target to a short window so a sentence that merely
# mentions "git push" and "main" far apart in the same line of prose doesn't
# trigger.
DANGEROUS_PATTERNS=(
  "git reset --hard\b"
  "git clean -f(d)?\b"
  "git branch -D\b"
  "git checkout( --)? \.([[:space:]]|$)"
  "git restore( --)? \.([[:space:]]|$)"
  "git push[^&|;]{0,30}(--force|--force-with-lease|-f\b)"
  "git push[^&|;]{0,20}(origin[[:space:]]+)?(HEAD:)?(main|master|staging)\b"
)

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if printf '%s\n' "$NORM_COMMAND" | grep -qE "$pattern"; then
    printf 'BLOCKED: %s matches dangerous pattern %s. Force-push, direct pushes to main/master/staging, reset --hard, clean -f/-fd, branch -D, and bare checkout/restore . are not permitted. The user has prevented you from doing this.\n' "$COMMAND" "$pattern" >&2
    exit 2
  fi
done

exit 0
