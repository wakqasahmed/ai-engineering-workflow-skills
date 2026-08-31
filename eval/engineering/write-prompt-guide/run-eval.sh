#!/usr/bin/env bash
set -euo pipefail

EVAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(mktemp -d)"
trap 'rm -rf "$WORKSPACE"' EXIT

if [[ "${1:---dry-run}" != "--dry-run" || $# -gt 1 ]]; then
  echo "Usage: run-eval.sh [--dry-run]" >&2
  exit 1
fi

mkdir -p "$WORKSPACE/eval/fixtures" "$WORKSPACE/home"
cp "$EVAL_DIR/check-contract.py" "$EVAL_DIR/validate-guide.py" "$WORKSPACE/eval/"
cp "$EVAL_DIR/fixtures/held-out.json" "$EVAL_DIR/fixtures/tuning.json" "$WORKSPACE/eval/fixtures/"
cp "$EVAL_DIR/../../../skills/engineering/write-prompt-guide/SKILL.md" "$WORKSPACE/SKILL.md"
cp "$EVAL_DIR/../../../SOURCES.md" "$WORKSPACE/SOURCES.md"
cat > "$WORKSPACE/sitecustomize.py" <<'PY'
import socket
def blocked(*args, **kwargs):
    raise OSError("network disabled for deterministic eval")
socket.socket = blocked
socket.create_connection = blocked
PY

PYTHONPATH="$WORKSPACE" HOME="$WORKSPACE/home" PYTHONNOUSERSITE=1 python3 "$WORKSPACE/eval/check-contract.py"
