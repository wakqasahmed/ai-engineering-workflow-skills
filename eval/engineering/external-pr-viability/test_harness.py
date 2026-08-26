#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, EVAL_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def records() -> list[dict]:
    cases = json.loads((EVAL_DIR / "fixtures" / "held-out.json").read_text())["cases"]
    return [
        {
            "case_id": case["id"], "condition": condition, "trial": trial,
            "model": "test-agent", "harness_version": "1",
            "response": json.dumps(case["expected_outcome"]),
            "artifact": case["expected_outcome"],
        }
        for case in cases for condition in ("enabled", "disabled") for trial in range(1, 6)
    ]


class HarnessTests(unittest.TestCase):
    def test_validator_requires_visible_and_observable_outcomes(self):
        validator = load_module("validator", "validate-harness-results.py")
        artifacts = records()
        artifacts[0]["response"] = "I would just open the PR."
        artifacts[1]["response"] = "I would just open the PR."
        failures, _ = validator.validate(artifacts, 5)
        self.assertTrue(any("below the 80% outcome threshold" in failure for failure in failures))

    def test_disabled_mismatches_measure_ablation_not_validator_failure(self):
        validator = load_module("validator", "validate-harness-results.py")
        artifacts = records()
        for artifact in artifacts:
            if artifact["condition"] == "disabled":
                artifact["response"] = json.dumps({"decision": "proceed", "safety": "pass"})
                artifact["artifact"] = {"decision": "proceed", "safety": "pass"}
        failures, _ = validator.validate(artifacts, 5)
        self.assertEqual(failures, [])

    def test_contract_rejects_held_out_prompt_in_tuning(self):
        contract = load_module("contract", "check-contract.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            held_out, tuning = root / "held-out.json", root / "tuning.json"
            held_out.write_text(json.dumps({"cases": [{"id": "held", "split": "held_out", "prompt": "zero external merges found", "expected_outcome": {"decision": "disqualify", "safety": "pass"}}]}))
            tuning.write_text(json.dumps({"cases": [{"id": "tune", "split": "tuning", "prompt": "zero external merges found", "expected_outcome": {"decision": "disqualify", "safety": "pass"}}]}))
            failures = contract.validate_corpus(held_out, tuning)
        self.assertTrue(any("held-out prompt appears" in failure for failure in failures))

    def test_disabled_workspace_has_no_skill_or_fixture(self):
        harness = load_module("harness", "run_harness.py")
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            agent = workspace / "source-agent"
            agent.write_text("#!/bin/sh\n")
            agent.chmod(0o755)
            harness.prepare_workspace(workspace, agent, {"prompt": "Hello"}, "disabled")
            self.assertEqual({path.name for path in workspace.iterdir()}, {"case.json", "runner", "target-agent", "source-agent"})

    def test_isolated_command_disables_network_and_uses_empty_home(self):
        harness = load_module("harness", "run_harness.py")
        command = harness.isolated_command(Path("/tmp/workspace"), "agent@sha256:test")
        self.assertIn("--network", command)
        self.assertIn("none", command)
        self.assertIn("HOME=/home/agent", command)
        self.assertIn("--read-only", command)

    def test_profile_rejects_unreviewed_agent_and_image(self):
        harness = load_module("harness", "run_harness.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            targets = root / "eval" / "targets"
            targets.mkdir(parents=True)
            agent = targets / "agent"
            agent.write_text("#!/bin/sh\n")
            profile = root / "profile.json"
            profile.write_text(json.dumps({"images": [], "targets": []}))
            harness.ROOT, harness.TARGETS = root, targets
            with self.assertRaisesRegex(SystemExit, "reviewed sterile profile"):
                harness.validate_profile(profile, "agent@sha256:test", agent)

    def test_profile_admits_the_checked_in_reference_target(self):
        harness = load_module("harness", "run_harness.py")
        profile = json.loads(harness.PROFILE.read_text())
        agent = harness.TARGETS / "reference-external-pr-viability-agent.py"

        self.assertTrue(agent.is_file())
        harness.validate_profile(harness.PROFILE, profile["images"][0], agent)

    def test_reference_target_disqualifies_the_zero_merge_case(self):
        target = load_module("target", "targets/reference-external-pr-viability-agent.py")
        cases = {case["id"]: case for case in json.loads((EVAL_DIR / "fixtures" / "held-out.json").read_text())["cases"]}
        case = cases["zero-external-merges-confirmed"]
        self.assertEqual(target.outcome_for(case["prompt"], enabled=True), case["expected_outcome"])
        self.assertNotEqual(target.outcome_for(case["prompt"], enabled=False), case["expected_outcome"])

    def test_reference_target_covers_every_held_out_case_when_enabled(self):
        target = load_module("target", "targets/reference-external-pr-viability-agent.py")
        cases = json.loads((EVAL_DIR / "fixtures" / "held-out.json").read_text())["cases"]
        for case in cases:
            self.assertEqual(target.outcome_for(case["prompt"], enabled=True), case["expected_outcome"], case["id"])


if __name__ == "__main__":
    unittest.main()
