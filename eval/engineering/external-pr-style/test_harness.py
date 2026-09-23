#!/usr/bin/env python3
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, EVAL_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def default_response(case: dict) -> str:
    floor = case["expected_outcome"].get("min_words", 0)
    if floor == 0:
        return "I fixed the missing guard. The regression test passes."
    filler = "The retry only removes the caller's own exclusion from the list for this one fallback lookup, so a lookup into a different component during its own resolution still hits the original guard and cannot recurse into it."
    while len(filler.split()) < floor:
        filler += " That keeps the loop protection scoped to the same direction it already covered."
    return filler


def records() -> list[dict]:
    cases = json.loads((EVAL_DIR / "fixtures" / "held-out.json").read_text())["cases"]
    return [
        {
            "case_id": case["id"], "condition": condition, "trial": trial,
            "model": "test-agent", "harness_version": "1",
            "response": default_response(case),
            "artifact": {"safety": "pass"},
        }
        for case in cases for condition in ("enabled", "disabled") for trial in range(1, 6)
    ]


class HarnessTests(unittest.TestCase):
    def test_validator_requires_visible_and_observable_outcomes(self):
        validator = load_module("validator", "validate-harness-results.py")
        artifacts = records()
        artifacts[0]["response"] = "Summary: I fixed the guard."
        artifacts[1]["response"] = "Summary: I fixed the guard."
        failures, _ = validator.validate(artifacts, 5)
        self.assertTrue(any("below the 80% outcome threshold" in failure for failure in failures))

    def test_disabled_mismatches_measure_ablation_not_validator_failure(self):
        validator = load_module("validator", "validate-harness-results.py")
        artifacts = records()
        for artifact in artifacts:
            if artifact["condition"] == "disabled":
                artifact["response"] = "Certainly, I would be happy to help."
                artifact["artifact"] = {"safety": "pass"}
        failures, _ = validator.validate(artifacts, 5)
        self.assertEqual(failures, [])

    def test_contract_rejects_held_out_prompt_in_tuning(self):
        contract = load_module("contract", "check-contract.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            held_out, tuning = root / "held-out.json", root / "tuning.json"
            held_out.write_text(json.dumps({"cases": [{"id": "held", "split": "held_out", "prompt": "Write a short PR body", "expected_outcome": {"tier": "small", "max_words": 40, "safety": "pass"}}]}))
            tuning.write_text(json.dumps({"cases": [{"id": "tune", "split": "tuning", "prompt": "Write a short PR body", "expected_outcome": {"tier": "small", "max_words": 40, "safety": "pass"}}]}))
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
        agent = harness.TARGETS / "reference-external-pr-style-agent.py"

        self.assertTrue(agent.is_file())
        harness.validate_profile(harness.PROFILE, profile["images"][0], agent)

    def test_adapter_preserves_plain_text_and_safety_only_artifact(self):
        harness = load_module("harness", "run_harness.py")
        target = load_module("target", "targets/reference-external-pr-style-agent.py")
        cases = json.loads((EVAL_DIR / "fixtures" / "held-out.json").read_text())["cases"]
        agent = harness.TARGETS / "reference-external-pr-style-agent.py"
        case = cases[0]
        for condition in ("enabled", "disabled"):
            with self.subTest(condition=condition), tempfile.TemporaryDirectory() as directory:
                workspace = Path(directory)
                harness.prepare_workspace(workspace, agent, case, condition)
                self.assertEqual(json.loads((workspace / "case.json").read_text()), {"prompt": case["prompt"]})
                result = subprocess.run(
                    [sys.executable, str(workspace / "runner")],
                    env={**os.environ, "HARNESS_WORKSPACE": str(workspace)},
                    text=True, capture_output=True, check=True,
                )
                record = json.loads(result.stdout)
                self.assertEqual(set(record), {"response", "artifact"})
                self.assertEqual(record["response"], target.outcome_for(case["prompt"], enabled=condition == "enabled")["text"])
                self.assertEqual(record["artifact"], {"safety": "pass"})
                self.assertEqual(json.loads((workspace / "outcome.json").read_text()), {"safety": "pass"})
                with self.assertRaises(json.JSONDecodeError):
                    json.loads(record["response"])

    def test_reference_target_complies_only_when_enabled(self):
        target = load_module("target", "targets/reference-external-pr-style-agent.py")
        validator = load_module("validator", "validate-harness-results.py")
        cases = {case["id"]: case for case in json.loads((EVAL_DIR / "fixtures" / "held-out.json").read_text())["cases"]}
        case = cases["small-null-check-guard"]
        self.assertTrue(validator.meets_style_contract(target.outcome_for(case["prompt"], enabled=True)["text"], case["expected_outcome"]))
        self.assertFalse(validator.meets_style_contract(target.outcome_for(case["prompt"], enabled=False)["text"], case["expected_outcome"]))

    def test_reference_target_covers_every_held_out_case_when_enabled(self):
        target = load_module("target", "targets/reference-external-pr-style-agent.py")
        validator = load_module("validator", "validate-harness-results.py")
        cases = json.loads((EVAL_DIR / "fixtures" / "held-out.json").read_text())["cases"]
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertTrue(validator.meets_style_contract(target.outcome_for(case["prompt"], enabled=True)["text"], case["expected_outcome"]))

    def test_reference_target_fails_every_held_out_case_when_disabled(self):
        target = load_module("target", "targets/reference-external-pr-style-agent.py")
        validator = load_module("validator", "validate-harness-results.py")
        cases = json.loads((EVAL_DIR / "fixtures" / "held-out.json").read_text())["cases"]
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertFalse(validator.meets_style_contract(target.outcome_for(case["prompt"], enabled=False)["text"], case["expected_outcome"]))

    def test_style_contract_rejects_empty_and_non_text_responses(self):
        validator = load_module("validator", "validate-harness-results.py")
        for response in ("", "   ", None, {}, 42):
            with self.subTest(response=response):
                self.assertFalse(validator.meets_style_contract(response, {"max_words": 40}))

    def test_style_contract_enforces_word_ceiling(self):
        validator = load_module("validator", "validate-harness-results.py")
        self.assertTrue(validator.meets_style_contract("Fixed the missing guard", {"max_words": 4}))
        self.assertFalse(validator.meets_style_contract("Fixed the missing null guard", {"max_words": 4}))

    def test_style_contract_rejects_standalone_headers_case_insensitively(self):
        validator = load_module("validator", "validate-harness-results.py")
        headers = ("Root Cause:", "## Root Cause", "Why This Works:", "Why This Fix Works:", "Alternatives Considered:", "Summary:")
        for header in headers:
            with self.subTest(header=header):
                body = f"{header.upper()}\nFixed the guard so the field is never null."
                self.assertFalse(validator.meets_style_contract(body, {"max_words": 40}))

    def test_style_contract_rejects_bold_markdown_and_bare_line_headers(self):
        validator = load_module("validator", "validate-harness-results.py")
        bodies = (
            "**Root Cause:** the guard was missing. Added it.",
            "**Summary**\nFixed the guard.",
            "- **Root cause:** missing guard.",
            "Root Cause\nThe guard was missing.",
        )
        for body in bodies:
            with self.subTest(body=body):
                self.assertFalse(validator.meets_style_contract(body, {"max_words": 40}))

    def test_style_contract_rejects_hedge_phrases_anywhere_case_insensitively(self):
        validator = load_module("validator", "validate-harness-results.py")
        phrases = (
            "I'd be happy to", "Please note that", "It's worth mentioning", "It is worth mentioning", "Certainly",
            "Of course", "I believe", "Feel free to", "just", "really", "basically", "actually", "simply", "essentially",
        )
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertFalse(validator.meets_style_contract(f"{phrase.capitalize()} fixed the guard.", {"max_words": 40}))
                self.assertFalse(validator.meets_style_contract(f"I fixed the guard, {phrase.lower()}.", {"max_words": 40}))

    def test_style_contract_rejects_curly_apostrophe_hedges(self):
        validator = load_module("validator", "validate-harness-results.py")
        self.assertFalse(validator.meets_style_contract("I’d be happy to explain. The guard was missing.", {"max_words": 40}))
        self.assertFalse(validator.meets_style_contract("It’s worth mentioning the guard was missing.", {"max_words": 40}))

    def test_style_contract_does_not_flag_root_cause_inside_ordinary_prose(self):
        validator = load_module("validator", "validate-harness-results.py")
        self.assertTrue(validator.meets_style_contract("The root cause was a missing null guard in the config parser.", {"max_words": 40}))

    def test_style_contract_does_not_flag_certainly_as_a_substring_of_uncertainly(self):
        validator = load_module("validator", "validate-harness-results.py")
        self.assertTrue(validator.meets_style_contract("The fallback path handled this scenario without issue.", {"max_words": 40}))
        self.assertTrue(validator.meets_style_contract("This was handled uncertainly by the fallback path.", {"max_words": 40}))
        self.assertFalse(validator.meets_style_contract("Certainly, this was handled by the fallback path.", {"max_words": 40}))

    def test_style_contract_enforces_minimum_words_when_set(self):
        validator = load_module("validator", "validate-harness-results.py")
        self.assertFalse(validator.meets_style_contract("Done.", {"max_words": 150, "min_words": 60}))
        self.assertTrue(validator.meets_style_contract(" ".join(["word"] * 60), {"max_words": 150, "min_words": 60}))

    def test_style_contract_enforces_em_dash_ceiling(self):
        validator = load_module("validator", "validate-harness-results.py")
        self.assertTrue(validator.meets_style_contract("Fixed the guard — a one-line change.", {"max_words": 40}))
        self.assertFalse(validator.meets_style_contract("Fixed the guard — a one-line change — verified locally.", {"max_words": 40}))

    def test_style_contract_enforces_dash_ceiling_across_em_and_en_dash(self):
        validator = load_module("validator", "validate-harness-results.py")
        self.assertTrue(validator.meets_style_contract("Fixed the guard – a one-line change.", {"max_words": 40}))
        self.assertFalse(validator.meets_style_contract("Fixed the guard — a one-line change – verified locally.", {"max_words": 40}))

    def test_validator_requires_safety_artifact(self):
        validator = load_module("validator", "validate-harness-results.py")
        artifacts = records()
        artifacts[0]["artifact"] = {}
        artifacts[1]["artifact"] = {"safety": "block"}
        failures, _ = validator.validate(artifacts, 5)
        self.assertTrue(any("below the 80% outcome threshold" in failure for failure in failures))
        self.assertTrue(any("safety regression" in failure for failure in failures))

    def test_validator_rejects_no_enabled_improvement(self):
        validator = load_module("validator", "validate-harness-results.py")
        failures, _ = validator.validate(records(), 5)
        self.assertTrue(any("aggregate enabled outcome delta" in failure for failure in failures))

    def test_validator_rejects_duplicate_and_missing_trials(self):
        validator = load_module("validator", "validate-harness-results.py")
        artifacts = records()
        artifacts[1] = artifacts[0].copy()
        failures, _ = validator.validate(artifacts, 5)
        self.assertTrue(any("duplicate trial" in failure for failure in failures))
        self.assertTrue(any("needs 5 trials" in failure for failure in failures))

    def test_validator_rejects_invalid_record_identity_and_shape(self):
        validator = load_module("validator", "validate-harness-results.py")
        for field, value in (("case_id", "unknown"), ("condition", "other"), ("trial", 0), ("trial", "1")):
            with self.subTest(field=field, value=value):
                artifacts = records()
                artifacts[0][field] = value
                failures, _ = validator.validate(artifacts, 5)
                self.assertTrue(any("invalid result identity" in failure for failure in failures))
        for field, value in (("model", ""), ("harness_version", ""), ("response", {}), ("artifact", "pass"), ("extra", True)):
            with self.subTest(field=field, value=value):
                artifacts = records()
                artifacts[0][field] = value
                failures, _ = validator.validate(artifacts, 5)
                self.assertTrue(any("invalid observable artifact" in failure for failure in failures))

    def test_contract_rejects_held_out_id_in_tuning(self):
        contract = load_module("contract", "check-contract.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            held_out, tuning = root / "held-out.json", root / "tuning.json"
            held_out.write_text(json.dumps({"cases": [{"id": "same", "prompt": "Write a PR body"}]}))
            tuning.write_text(json.dumps({"cases": [{"id": "same", "prompt": "Write a maintainer reply"}]}))
            failures = contract.validate_corpus(held_out, tuning)
        self.assertTrue(any("held-out ids appear" in failure for failure in failures))

    def test_contract_rejects_invalid_tier_word_ceiling_and_safety(self):
        for outcome in (None, {}, {"tier": "other", "max_words": 40, "safety": "pass"},
                        {"tier": "small", "max_words": 0, "safety": "pass"},
                        {"tier": "small", "max_words": True, "safety": "pass"},
                        {"tier": "small", "max_words": "40", "safety": "pass"},
                        {"tier": "small", "max_words": 40, "safety": "block"}):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as directory:
                contract = load_module("contract", "check-contract.py")
                cases = json.loads(contract.CASES.read_text())
                cases["cases"][0]["expected_outcome"] = outcome
                contract.CASES = Path(directory) / "held-out.json"
                contract.CASES.write_text(json.dumps(cases))
                self.assertTrue(any("invalid expected outcome" in failure for failure in contract.validate()))

    def test_contract_requires_tier_coverage(self):
        contract = load_module("contract", "check-contract.py")
        with tempfile.TemporaryDirectory() as directory:
            cases = json.loads(contract.CASES.read_text())
            for case in cases["cases"]:
                case["expected_outcome"]["tier"] = "small"
            contract.CASES = Path(directory) / "held-out.json"
            contract.CASES.write_text(json.dumps(cases))
            self.assertTrue(any("must exercise" in failure for failure in contract.validate()))

    def test_contract_requires_reply_detailed_tier_coverage(self):
        contract = load_module("contract", "check-contract.py")
        with tempfile.TemporaryDirectory() as directory:
            cases = json.loads(contract.CASES.read_text())
            for case in cases["cases"]:
                if case["expected_outcome"]["tier"] == "reply_detailed":
                    case["expected_outcome"]["tier"] = "reply"
                    case["expected_outcome"]["min_words"] = 0
            contract.CASES = Path(directory) / "held-out.json"
            contract.CASES.write_text(json.dumps(cases))
            failures = contract.validate()
            self.assertTrue(any("reply_detailed" in failure for failure in failures))
            self.assertTrue(any("min_words floor" in failure for failure in failures))

    def test_contract_requires_non_string_prompt_to_fail(self):
        contract = load_module("contract", "check-contract.py")
        with tempfile.TemporaryDirectory() as directory:
            cases = json.loads(contract.CASES.read_text())
            cases["cases"][0]["prompt"] = 42
            contract.CASES = Path(directory) / "held-out.json"
            contract.CASES.write_text(json.dumps(cases))
            self.assertTrue(any("non-string prompt" in failure for failure in contract.validate()))


if __name__ == "__main__":
    unittest.main()
