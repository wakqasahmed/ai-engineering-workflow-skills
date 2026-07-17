#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL="$REPO_ROOT/skills/engineering/changesets-release/SKILL.md"

grep -Fq 'Do not require Changesets for a single deployed application' "$SKILL"
grep -Fq 'patch' "$SKILL"
grep -Fq 'minor' "$SKILL"
grep -Fq 'major' "$SKILL"
grep -Fq 'changeset status' "$SKILL"
grep -Fq 'WordPress plugin' "$SKILL"

echo "changesets-release tests passed"
