#!/usr/bin/env python3
"""Adapt a target agent's review text into the harness artifact contract."""
import json
import os
import subprocess
from pathlib import Path


WORKSPACE = Path(os.environ.get("HARNESS_WORKSPACE", "/workspace"))


def main() -> int:
    case = json.loads((WORKSPACE / "case.json").read_text())
    request = {"prompt": case["prompt"], "artifacts": case.get("artifacts", {})}
    skill = WORKSPACE / "SKILL.md"
    if skill.is_file():
        request["skill_path"] = str(skill)
    result = subprocess.run(
        [str(WORKSPACE / "target-agent")],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        check=True,
        cwd=WORKSPACE,
        env={"HOME": "/home/agent", "LANG": "C", "PATH": "/usr/local/bin:/usr/bin:/bin", "PYTHONNOUSERSITE": "1"},
    )
    response = result.stdout.strip()
    if not response:
        raise SystemExit("target agent returned an empty response")
    print(json.dumps({"response": response}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
