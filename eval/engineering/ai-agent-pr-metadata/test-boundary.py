#!/usr/bin/env python3
"""Prove fake-GitHub state is host-owned, not evaluator-writable evidence."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

from fake_github import FakeGithub


EVAL_DIR = Path(__file__).resolve().parent


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        audit = root / "workspace" / "audit"
        audit.mkdir(parents=True)
        state_path = root / "state.json"
        github = FakeGithub(audit / "github.sock", state_path)
        github.start()
        shim = root / "gh"
        shim.write_text((EVAL_DIR / "fake_cli.py").read_text())
        subprocess.run(
            ["python3", str(shim), "issue", "edit", "81", "--add-label", "agent:model-medium-implementer"],
            check=True,
            env={"HARNESS_GITHUB_SOCKET": str(audit / "github.sock"), "PATH": os.environ["PATH"]},
        )
        github.stop()
        state = json.loads(state_path.read_text())
        if state["issues"]["81"]["labels"] != ["agent:model-medium-implementer"]:
            raise SystemExit("fake GitHub did not apply the observed label state")
    harness = (EVAL_DIR / "run_harness.py").read_text()
    if "HARNESS_ARTIFACT" in harness or "events.jsonl" in harness or "source={workspace / 'artifact'}" in harness:
        raise SystemExit("evaluator still receives writable evidence storage")
    print("PASS: host-owned fake GitHub boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
