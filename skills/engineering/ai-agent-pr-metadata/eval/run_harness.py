#!/usr/bin/env python3
"""Run a supplied evaluator in clean, network-isolated workspaces."""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from fake_github import FakeGithub

EVAL_DIR = Path(__file__).resolve().parent
CASES = EVAL_DIR / "fixtures" / "held-out.json"
HARNESS_VERSION = "3"

def prepare_workspace(workspace: Path, case: dict, condition: str) -> None:
    (workspace / "home").mkdir()
    (workspace / "audit").mkdir()
    (workspace / "bin").mkdir()
    (workspace / "case.json").write_text(json.dumps({"prompt": case["prompt"]}))
    for tool in ("gh", "git"):
        shim = workspace / "bin" / tool
        shutil.copy2(EVAL_DIR / "fake_cli.py", shim)
        shim.chmod(0o755)
    if condition == "enabled":
        shutil.copy2(EVAL_DIR.parent / "SKILL.md", workspace / "SKILL.md")

def isolated_command(workspace: Path, image: str, command: str, condition: str, trial: int, model: str) -> list[str]:
    return [
        "docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        "--mount", f"type=bind,source={workspace},target=/workspace,readonly",
        "--mount", f"type=bind,source={workspace / 'home'},target=/home/evaluator",
        "--env", "HARNESS_WORKSPACE=/workspace", "--env", "HOME=/home/evaluator",
        "--env", "HARNESS_GITHUB_SOCKET=/workspace/audit/github.sock",
        "--env", "PATH=/workspace/bin:/usr/local/bin:/usr/bin:/bin",
        "--env", f"HARNESS_CONDITION={condition}", "--env", f"HARNESS_TRIAL={trial}",
        "--env", f"HARNESS_MODEL={model}", "--workdir", "/workspace", "--entrypoint", "/bin/sh",
        image, "-ceu", command,
    ]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", required=True, help="command that emits one JSON record to stdout")
    parser.add_argument("--image", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--trials", type=int, choices=range(3, 7), default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.trials != 5:
        raise SystemExit("this evaluator requires five trials for each condition")
    if "@sha256:" not in args.image:
        raise SystemExit("image must be pinned by digest")
    records = []
    for case in json.loads(CASES.read_text())["cases"]:
        for condition in ("enabled", "disabled"):
            for trial in range(1, args.trials + 1):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    workspace = root / "workspace"
                    workspace.mkdir()
                    prepare_workspace(workspace, case, condition)
                    github = FakeGithub(workspace / "audit" / "github.sock", root / "state.json", case.get("initial_state"))
                    github.start()
                    result = subprocess.run(
                        isolated_command(workspace, args.image, args.command, condition, trial, args.model),
                        text=True, capture_output=True, check=True,
                        env={"PATH": os.environ["PATH"], "HOME": "/nonexistent", "LANG": "C"},
                    )
                    github.stop()
                    state = json.loads((root / "state.json").read_text())
                record = json.loads(result.stdout)
                if not isinstance(record, dict) or record.get("model") != args.model:
                    raise SystemExit("runner must emit one record with the declared model")
                records.append({"artifact": {"state": state}, **record, "case_id": case["id"], "condition": condition, "trial": trial,
                                "model": args.model, "harness_version": HARNESS_VERSION})
    args.output.write_text(json.dumps(records, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
