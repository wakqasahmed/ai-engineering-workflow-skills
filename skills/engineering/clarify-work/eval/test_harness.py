#!/usr/bin/env python3
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent


def load_validator():
    spec = importlib.util.spec_from_file_location("validator", EVAL_DIR / "validate-harness-results.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def records(response: str) -> list[dict]:
    cases = json.loads((EVAL_DIR / "fixtures" / "held-out.json").read_text())["cases"]
    return [
        {"case_id": case["id"], "condition": condition, "trial": trial, "model": "test-agent", "harness_version": "1", "response": response}
        for case in cases for condition in ("enabled", "disabled") for trial in range(1, 4)
    ]


class HarnessTests(unittest.TestCase):
    def test_validator_rejects_runner_verdict_fields(self):
        validator = load_validator()
        artifact = records("What owner should decide this?")[0]
        artifact["outcome"] = "forged-pass"
        failures, _ = validator.validate([artifact], 3)
        self.assertTrue(any("invalid observable artifact" in failure for failure in failures))

    def test_validator_scores_text_not_verdicts(self):
        validator = load_validator()
        failures, _ = validator.validate(records("I will implement this now."), 3)
        self.assertTrue(any("below the 80% outcome threshold" in failure for failure in failures))

    def test_adapter_returns_only_target_agent_text(self):
        adapter = EVAL_DIR / "target-agent-adapter.py"
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "case.json").write_text(json.dumps({"prompt": "Hello"}))
            target = workspace / "target.py"
            target.write_text("import sys; sys.stdin.read(); print('What owner should decide this?')")
            result = subprocess.run(
                ["python3", str(adapter)], text=True, capture_output=True, check=True,
                env={"HARNESS_WORKSPACE": str(workspace), "TARGET_AGENT_COMMAND": f"python3 {target}"},
            )
        self.assertEqual(json.loads(result.stdout), {"response": "What owner should decide this?"})

    def test_isolated_command_hides_trial_and_condition(self):
        harness_spec = importlib.util.spec_from_file_location("harness", EVAL_DIR / "run_harness.py")
        harness = importlib.util.module_from_spec(harness_spec)
        harness_spec.loader.exec_module(harness)
        command = harness.isolated_command(Path("/tmp/workspace"), "agent@sha256:test", "agent --json")
        self.assertNotIn("HARNESS_CONDITION", " ".join(command))
        self.assertNotIn("HARNESS_TRIAL", " ".join(command))


if __name__ == "__main__":
    unittest.main()
