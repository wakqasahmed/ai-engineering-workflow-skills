#!/usr/bin/env bash
set -euo pipefail

EVAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$EVAL_DIR/../../.." && pwd)"

if [[ "${1:---dry-run}" != "--dry-run" || $# -gt 1 ]]; then
  echo "Usage: run-eval.sh [--dry-run]" >&2
  exit 1
fi

cd "$REPO_ROOT"
PYTHONNOUSERSITE=1 python3 -m unittest tests.test_caveman
