#!/usr/bin/env python3
"""Run a repository-controlled review-gate evaluator in isolated workspaces."""
import argparse
import hashlib
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
ADAPTER = EVAL_DIR / "target-agent-adapter.py"


def prepare_workspace(workspace: Path, agent: Path, case: dict, condition: str) -> None:
    workspace.chmod(0o755)
    (workspace / "case.json").write_text(json.dumps({"prompt": case["prompt"]}))
    shutil.copy2(ADAPTER, workspace / "runner")
    (workspace / "runner").chmod(0o755)
    shutil.copy2(agent, workspace / "target-agent")
    (workspace / "target-agent").chmod(0o755)
    if condition == "enabled":
        shutil.copy2(EVAL_DIR.parent / "SKILL.md", workspace / "SKILL.md")


def isolated_command(workspace: Path, image: str) -> list[str]:
    return [
        "docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges", "--user", "65532:65532", "--pids-limit", "64",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        "--tmpfs", "/home/agent:rw,noexec,nosuid,size=8m",
        "--mount", f"type=bind,source={workspace},target=/workspace,readonly",
        "--env", "HARNESS_WORKSPACE=/workspace",
        "--env", "HOME=/home/agent", "--env", "PYTHONNOUSERSITE=1", "--env", "PATH=/usr/local/bin:/usr/bin:/bin",
        "--workdir", "/workspace", image, "/workspace/runner",
    ]


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_attestation(path: Path, image: str, agent: Path) -> None:
    if not path.is_file() or not path.is_relative_to(ROOT):
        raise SystemExit("attestation must be a repository-controlled file")
    attestation = json.loads(path.read_text())
    required_claims = {"no_ambient_credentials", "no_held_out_fixtures", "no_preinstalled_skills", "empty_home", "non_root"}
    claims = attestation.get("claims")
    if attestation.get("image") != image or attestation.get("agent_sha256") != file_sha256(agent):
        raise SystemExit("attestation does not match the evaluator image and target agent")
    if not isinstance(claims, dict) or {name for name in required_claims if claims.get(name) is not True}:
        raise SystemExit("attestation does not assert the sterile evaluator contract")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", type=Path, required=True)
    parser.add_argument("--attestation", type=Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--trials", type=int, choices=range(3, 7), default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    agent = args.agent.resolve()
    if not agent.is_file() or not agent.is_relative_to(ROOT):
        raise SystemExit("agent must be a repository-controlled file")
    if "@sha256:" not in args.image:
        raise SystemExit("image must be pinned by digest")
    validate_attestation(args.attestation.resolve(), args.image, agent)

    records = []
    for case in json.loads(CASES.read_text())["cases"]:
        for condition in ("enabled", "disabled"):
            for trial in range(1, args.trials + 1):
                with tempfile.TemporaryDirectory() as directory:
                    workspace = Path(directory)
                    prepare_workspace(workspace, agent, case, condition)
                    result = subprocess.run(
                        isolated_command(workspace, args.image),
                        text=True,
                        capture_output=True,
                        check=True,
                        env={"PATH": os.environ["PATH"], "HOME": "/nonexistent", "LANG": "C"},
                    )
                record = json.loads(result.stdout)
                if not isinstance(record, dict) or set(record) != {"response"} or not isinstance(record["response"], str):
                    raise SystemExit("target-agent adapter must emit only a text response")
                records.append({**record, "case_id": case["id"], "condition": condition, "trial": trial, "model": args.model, "harness_version": HARNESS_VERSION})
    args.output.write_text(json.dumps(records, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
