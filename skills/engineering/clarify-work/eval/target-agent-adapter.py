#!/usr/bin/env python3
"""Adapt a target agent's text response into the harness artifact contract."""
import json
import os
import shlex
import subprocess
from pathlib import Path


WORKSPACE = Path(os.environ.get("HARNESS_WORKSPACE", "/workspace"))


def main() -> int:
    command = os.environ.get("TARGET_AGENT_COMMAND")
    if not command:
        raise SystemExit("TARGET_AGENT_COMMAND is required")
    case = json.loads((WORKSPACE / "case.json").read_text())
    request = {"prompt": case["prompt"]}
    skill = WORKSPACE / "SKILL.md"
    if skill.is_file():
        request["skill_path"] = str(skill)
    result = subprocess.run(
        shlex.split(command), input=json.dumps(request), text=True, capture_output=True, check=True, cwd=WORKSPACE
    )
    response = result.stdout.strip()
    if not response:
        raise SystemExit("target agent returned an empty response")
    print(json.dumps({"response": response}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
