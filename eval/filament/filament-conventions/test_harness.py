#!/usr/bin/env python3
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, EVAL_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def records(response: str) -> list[dict]:
    cases = json.loads((EVAL_DIR / "fixtures" / "held-out.json").read_text())["cases"]
    return [
        {
            "case_id": case["id"],
            "condition": condition,
            "trial": trial,
            "model": "test-agent",
            "harness_version": "1",
            "response": response,
            "artifact": case["expected_outcome"],
        }
        for case in cases
        for condition in ("enabled", "disabled")
        for trial in range(1, 4)
    ]


class HarnessTests(unittest.TestCase):
    def test_validator_requires_version_correct_observable_response(self):
        validator = load_module("validator", "validate-harness-results.py")
        artifacts = records("I would use Filament conventions.")
        failures, _ = validator.validate(artifacts, 3)
        self.assertTrue(any("below the 80% outcome threshold" in failure for failure in failures))

    def test_validator_accepts_enabled_outcomes_and_disabled_ablation(self):
        validator = load_module("validator", "validate-harness-results.py")
        artifacts = records("")
        for record in artifacts:
            if record["condition"] == "enabled":
                record["response"] = json.dumps(record["artifact"], sort_keys=True)
            else:
                record["response"] = "No applicable framework-specific change."
        failures, _ = validator.validate(artifacts, 3)
        self.assertEqual(failures, [])

    def test_validator_rejects_runner_verdict_fields(self):
        validator = load_module("validator", "validate-harness-results.py")
        artifact = records("anything")[0]
        artifact["outcome"] = "forged-pass"
        failures, _ = validator.validate([artifact], 3)
        self.assertTrue(any("invalid observable artifact" in failure for failure in failures))

    def test_disabled_workspace_has_no_skill_or_held_out_fixture(self):
        harness = load_module("harness", "run_harness.py")
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            agent = workspace / "source-agent"
            agent.write_text("#!/bin/sh\n")
            agent.chmod(0o755)
            harness.prepare_workspace(workspace, agent, {"prompt": "Hello"}, "disabled")
            self.assertEqual(
                {path.name for path in workspace.iterdir()},
                {"case.json", "runner", "target-agent", "source-agent"},
            )
            self.assertEqual(workspace.stat().st_mode & 0o777, 0o700)

    def test_isolated_command_disables_network_and_uses_empty_home(self):
        harness = load_module("harness", "run_harness.py")
        command = harness.isolated_command(Path("/tmp/workspace"), "agent@sha256:test")
        self.assertIn("--network", command)
        self.assertIn("none", command)
        self.assertIn(f"{os.getuid()}:{os.getgid()}", command)
        self.assertIn("HOME=/home/agent", command)
        self.assertIn("--read-only", command)

    def test_profile_rejects_unreviewed_agent_and_image(self):
        harness = load_module("harness", "run_harness.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            targets = root / "eval" / "targets"
            targets.mkdir(parents=True)
            agent = targets / "target-agent"
            agent.write_text("#!/bin/sh\n")
            profile = root / "profile.json"
            profile.write_text(json.dumps({"images": [], "targets": []}))
            harness.ROOT = root
            harness.TARGETS = targets
            with self.assertRaisesRegex(SystemExit, "reviewed sterile profile"):
                harness.validate_profile(profile, "agent@sha256:test", agent)


if __name__ == "__main__":
    unittest.main()
