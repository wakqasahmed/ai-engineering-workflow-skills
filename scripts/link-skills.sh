#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mkdir -p "$DEST"
find "$REPO/skills" -name SKILL.md -print0 |
while IFS= read -r -d '' skill_md; do
  src="$(dirname "$skill_md")"
  name="$(basename "$src")"
  target="$DEST/$name"
  if [[ -e "$target" && ! -L "$target" ]]; then
    echo "skip: $target exists and is not a symlink" >&2
    continue
  fi
  ln -sfn "$src" "$target"
  echo "linked $name -> $src"
done
