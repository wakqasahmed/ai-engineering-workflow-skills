#!/usr/bin/env bash
set -euo pipefail

SKILL_MD="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/SKILL.md"

require_contract() {
  local description="$1"
  local pattern="$2"

  if ! grep -Eq "$pattern" "$SKILL_MD"; then
    echo "FAIL: ${description}" >&2
    return 1
  fi

  echo "PASS: ${description}"
}

require_contract "initial estimate uses available context" 'Estimate the initial number of blocking questions from all available context'
require_contract "only one blocking question is asked per turn" 'Ask exactly one blocking question per user turn'
require_contract "planned questions show stable progress" 'Question n/N.*\[.*\]'
require_contract "follow-ups retain the original estimate" 'Follow-up k.*Question n/N'
require_contract "zero blockers skip the interview" 'If the estimate is zero, skip the interview'
