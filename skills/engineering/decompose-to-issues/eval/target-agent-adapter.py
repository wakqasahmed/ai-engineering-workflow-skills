#!/usr/bin/env python3
"""Pass one sterile evaluation request to the repository-controlled agent."""
import json
import os
import subprocess
from pathlib import Path


workspace = Path(os.environ["HARNESS_WORKSPACE"])
request = {
    "prompt": json.loads((workspace / "case.json").read_text())["prompt"],
    "response_contract": "Return valid JSON only. For work that needs decomposition, return {\"issues\":[{\"title\":string,\"scope\":string,\"acceptance_criteria\":[string],\"verification\":[string],\"dependencies\":[string],\"non_goals\":[string]}],\"relationships\":[{\"from\":number,\"to\":number,\"type\":\"depends_on\"}]}. For a direct, already-scoped change, return {\"direct_action\":{\"scope\":string,\"verification\":[string],\"non_goals\":[string]}}.",
}
skill = workspace / "SKILL.md"
if skill.exists():
    request["skill_path"] = str(skill)

result = subprocess.run(
    [str(workspace / "target-agent")],
    input=json.dumps(request),
    text=True,
    capture_output=True,
    check=True,
    env={"HOME": os.environ["HOME"], "PATH": os.environ["PATH"], "PYTHONNOUSERSITE": "1"},
)
print(json.dumps({"response": result.stdout.strip()}))
