#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL="$REPO_ROOT/skills/engineering/ai-agent-pr-metadata/SKILL.md"

grep -Fq 'agent:<model+version>-<effort>-<role>' "$SKILL"
grep -Fq 'agent:gpt5.6-terra-medium-implementer' "$SKILL"
grep -Fq 'Never replace the resolved model version or declared effort with an alias or a stronger/weaker value.' "$SKILL"

echo "ai-agent-pr-metadata tests passed"
