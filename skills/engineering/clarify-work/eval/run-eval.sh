#!/usr/bin/env bash
set -euo pipefail

EVAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "$EVAL_DIR/evaluate.py" "$EVAL_DIR/fixtures/scenarios.json"
