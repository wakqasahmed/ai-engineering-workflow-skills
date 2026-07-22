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
cp "$EVAL_DIR/check-contract.py" "$WORKSPACE/eval/"
cp "$EVAL_DIR/fixtures/held-out.json" "$WORKSPACE/eval/fixtures/"
cp "$EVAL_DIR/../SKILL.md" "$WORKSPACE/SKILL.md"
cat > "$WORKSPACE/sitecustomize.py" <<'PY'
import socket
def blocked(*args, **kwargs):
    raise OSError("network disabled for deterministic eval")
socket.socket = blocked
socket.create_connection = blocked
PY
echo "== ai-agent-pr-metadata eval (dry-run, offline fixtures only) =="
PYTHONPATH="$WORKSPACE" HOME="$WORKSPACE/home" PYTHONNOUSERSITE=1 python3 -s "$WORKSPACE/eval/check-contract.py"
