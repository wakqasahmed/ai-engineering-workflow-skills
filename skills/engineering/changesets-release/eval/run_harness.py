#!/usr/bin/env python3
"""Run a repository-controlled Changesets evaluator in isolated workspaces."""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parents[3]
CASES = EVAL_DIR / "fixtures" / "held-out.json"
HARNESS_VERSION = "1"


def prepare_workspace(workspace: Path, runner: Path, case: dict, condition: str) -> None:
    (workspace / "case.json").write_text(json.dumps({"prompt": case["prompt"]}))
    shutil.copy2(runner, workspace / "runner")
    (workspace / "runner").chmod(0o755)
    if condition == "enabled":
        shutil.copy2(EVAL_DIR.parent / "SKILL.md", workspace / "SKILL.md")


def isolated_command(workspace: Path, image: str, condition: str, trial: int, model: str) -> list[str]:
    return [
        "docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        "--mount", f"type=bind,source={workspace},target=/workspace,readonly",
        "--env", "HARNESS_WORKSPACE=/workspace",
        "--env", f"HARNESS_CONDITION={condition}",
        "--env", f"HARNESS_TRIAL={trial}",
        "--env", f"HARNESS_MODEL={model}",
        "--workdir", "/workspace", image, "/workspace/runner",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--trials", type=int, choices=range(3, 7), default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.trials != 5:
        raise SystemExit("this evaluator requires five trials for each condition")
    runner = args.runner.resolve()
    if not runner.is_file() or not runner.is_relative_to(ROOT):
        raise SystemExit("runner must be a repository-controlled file")
    if "@sha256:" not in args.image:
        raise SystemExit("image must be pinned by digest")

    records = []
    for case in json.loads(CASES.read_text())["cases"]:
        for condition in ("enabled", "disabled"):
            for trial in range(1, args.trials + 1):
                with tempfile.TemporaryDirectory() as directory:
                    workspace = Path(directory)
                    prepare_workspace(workspace, runner, case, condition)
                    result = subprocess.run(
                        isolated_command(workspace, args.image, condition, trial, args.model),
                        text=True,
                        capture_output=True,
                        check=True,
                        env={"PATH": os.environ["PATH"], "HOME": "/nonexistent", "LANG": "C"},
                    )
                record = json.loads(result.stdout)
                if not isinstance(record, dict) or record.get("model") != args.model:
                    raise SystemExit("runner must emit one record with the declared model")
                records.append({
                    **record,
                    "case_id": case["id"],
                    "condition": condition,
                    "trial": trial,
                    "model": args.model,
                    "harness_version": HARNESS_VERSION,
                })
    args.output.write_text(json.dumps(records, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
