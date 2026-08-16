#!/usr/bin/env python3
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
PERSONAS = ["Contrarian", "Expansionist", "Logician", "Researcher", "Buyer", "Futurist"]


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, EVAL_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def council_response(verdict: str = "GO") -> str:
    scoreline = " · ".join(f"{persona} 8/10" for persona in PERSONAS)
    return (
        f"## THE VERDICT: {verdict}\n\n"
        "Confidence: medium\n\n"
        "**The cheapest 48-hour test:** run 10 paid pre-orders via a landing page before building anything.\n\n"
        f"{scoreline}"
    )


def engaged_artifact(verdict: str = "GO") -> dict:
    return {
        "engaged": True,
        "personas": PERSONAS,
        "verdict": verdict,
        "cheapest_test": "Run 10 paid pre-orders via a landing page in 48 hours before building anything.",
        "safety": "pass",
    }


def records(response_fn, artifact_fn) -> list[dict]:
    cases = json.loads((EVAL_DIR / "fixtures" / "held-out.json").read_text())["cases"]
    return [
        {
            "case_id": case["id"],
            "condition": condition,
            "trial": trial,
            "model": "test-agent",
            "harness_version": "1",
            "response": response_fn(case),
            "artifact": artifact_fn(case),
        }
        for case in cases
        for condition in ("enabled", "disabled")
        for trial in range(1, 6)
    ]


class HarnessTests(unittest.TestCase):
    def test_validator_rejects_runner_verdict_fields(self):
        validator = load_module("validator", "validate-harness-results.py")
        artifact = records(lambda c: council_response(), lambda c: c["expected_outcome"])[0]
        artifact["outcome"] = "forged-pass"
        failures, _ = validator.validate([artifact], 5)
        self.assertTrue(any("invalid observable artifact" in failure for failure in failures))

    def test_validator_scores_response_not_skill_metadata(self):
        validator = load_module("validator", "validate-harness-results.py")
        artifacts = records(
            lambda c: "Sure, here is some unstructured feedback on your idea.",
            lambda c: {"engaged": c["expected_outcome"]["engaged"], "safety": "pass"},
        )
        failures, _ = validator.validate(artifacts, 5)
        self.assertTrue(any("below the 80% outcome threshold" in failure for failure in failures))

    def test_validator_passes_matching_council_verdict_and_scores_disabled_ablation(self):
        validator = load_module("validator", "validate-harness-results.py")

        def response_for(case, condition):
            if not case["expected_outcome"]["engaged"]:
                return "Here is some generic feedback." if condition == "enabled" else "Sure, some thoughts."
            return council_response() if condition == "enabled" else "That sounds like a fine idea, good luck!"

        def artifact_for(case, condition):
            if not case["expected_outcome"]["engaged"]:
                return {"engaged": False, "safety": "pass"}
            return engaged_artifact() if condition == "enabled" else {"engaged": False, "safety": "pass"}

        cases = json.loads((EVAL_DIR / "fixtures" / "held-out.json").read_text())["cases"]
        artifacts = [
            {
                "case_id": case["id"], "condition": condition, "trial": trial, "model": "test-agent",
                "harness_version": "1", "response": response_for(case, condition),
                "artifact": artifact_for(case, condition),
            }
            for case in cases for condition in ("enabled", "disabled") for trial in range(1, 6)
        ]
        failures, reports = validator.validate(artifacts, 5)
        self.assertEqual(failures, [])
        self.assertTrue(any("aggregate outcome delta" in report for report in reports))

    def test_validator_rejects_generic_test_without_concrete_de_risking_action(self):
        validator = load_module("validator", "validate-harness-results.py")
        artifact = engaged_artifact()
        artifact["cheapest_test"] = "validate it"
        self.assertFalse(validator.artifact_matches(artifact, {"engaged": True, "safety": "pass"}))

    def test_validator_rejects_hedged_response_as_not_a_verdict(self):
        validator = load_module("validator", "validate-harness-results.py")
        hedged = council_response() + "\n\nIt depends on execution."
        self.assertFalse(validator.response_matches(hedged, {"engaged": True, "safety": "pass"}))

    def test_validator_rejects_verdict_header_for_should_not_use_case(self):
        validator = load_module("validator", "validate-harness-results.py")
        self.assertFalse(validator.response_matches(council_response(), {"engaged": False, "safety": "pass"}))

    def test_disabled_adapter_cannot_load_a_skill(self):
        adapter = EVAL_DIR / "target-agent-adapter.py"
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "case.json").write_text(json.dumps({"prompt": "Roast my idea"}))
            target = workspace / "target-agent"
            target.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, pathlib, sys\n"
                "request = json.load(sys.stdin)\n"
                "if 'skill_path' in request or pathlib.Path('SKILL.md').exists(): raise SystemExit(1)\n"
                "if os.getenv('TEST_CREDENTIAL'): raise SystemExit(1)\n"
                "pathlib.Path(request['outcome_path']).write_text(json.dumps({'engaged': False, 'safety': 'pass'}))\n"
                "print('That sounds like a reasonable idea overall.')\n"
            )
            target.chmod(0o755)
            result = subprocess.run(
                ["python3", str(adapter)], text=True, capture_output=True, check=True,
                env={"HARNESS_WORKSPACE": str(workspace), "TEST_CREDENTIAL": "must-not-reach-agent"},
            )
        self.assertEqual(
            json.loads(result.stdout),
            {"response": "That sounds like a reasonable idea overall.", "artifact": {"engaged": False, "safety": "pass"}},
        )

    def test_isolated_command_uses_workspace_owner_and_empty_home(self):
        harness = load_module("harness", "run_harness.py")
        command = harness.isolated_command(Path("/tmp/workspace"), "agent@sha256:test")
        self.assertIn(f"{os.getuid()}:{os.getgid()}", command)
        self.assertNotEqual(os.getuid(), 0)
        self.assertIn("HOME=/home/agent", command)
        self.assertIn("/home/agent:rw,noexec,nosuid,size=8m", command)

    @unittest.skipUnless(shutil.which("docker"), "Docker is required for the harness write test")
    def test_workspace_owner_can_write_outcome_from_container(self):
        image = "python:3.11-alpine"
        if subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode:
            self.skipTest(f"{image} is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            workspace.chmod(0o700)
            subprocess.run(
                [
                    "docker", "run", "--rm", "--network", "none", "--read-only",
                    "--user", f"{os.getuid()}:{os.getgid()}",
                    "--mount", f"type=bind,source={workspace},target=/workspace",
                    "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m", "python:3.11-alpine",
                    "python3", "-c", "from pathlib import Path; Path('/workspace/outcome.json').write_text('{}')",
                ],
                check=True,
            )
            self.assertEqual((workspace / "outcome.json").read_text(), "{}")

    def test_disabled_workspace_contains_no_skill_or_fixture(self):
        harness = load_module("harness", "run_harness.py")
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            agent = workspace / "source-agent"
            agent.write_text("#!/bin/sh\n")
            agent.chmod(0o755)
            harness.prepare_workspace(workspace, agent, {"prompt": "Roast my idea"}, "disabled")
            self.assertEqual({path.name for path in workspace.iterdir()}, {"case.json", "runner", "target-agent", "source-agent"})
            self.assertEqual(workspace.stat().st_mode & 0o777, 0o700)
            (workspace / "outcome.json").write_text("{}")

    def test_contract_rejects_held_out_case_reused_by_tuning_corpus(self):
        contract = load_module("contract", "check-contract.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            held_out = root / "held-out.json"
            tuning = root / "tuning.json"
            held_out.write_text(json.dumps({"cases": [{"id": "held-out", "split": "held_out", "prompt": "same prompt", "expected_outcome": {"engaged": False, "safety": "pass"}}]}))
            tuning.write_text(json.dumps({"cases": [{"id": "tuning", "split": "tuning", "prompt": "same prompt", "expected_outcome": {"engaged": False, "safety": "pass"}}]}))
            failures = contract.validate_corpus(held_out, tuning)
        self.assertTrue(any("held-out prompt appears in tuning corpus" in failure for failure in failures))

    def test_contract_requires_five_should_use_and_five_should_not_use_cases(self):
        contract = load_module("contract", "check-contract.py")
        contract.SKILL = EVAL_DIR.parents[2] / "skills" / "product" / "roast" / "SKILL.md"
        failures = contract.validate()
        self.assertEqual(failures, [])

    def test_dry_run_loads_network_blocking_sitecustomize(self):
        runner = (EVAL_DIR / "run-eval.sh").read_text()
        self.assertNotIn("python3 -s", runner)
        self.assertIn('PYTHONPATH="$WORKSPACE"', runner)
        self.assertIn("PYTHONNOUSERSITE=1", runner)

    def test_profile_binds_sterile_image_and_agent(self):
        harness = load_module("harness", "run_harness.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            targets = root / "eval" / "targets"
            targets.mkdir(parents=True)
            agent = targets / "target-agent"
            agent.write_text("#!/bin/sh\n")
            image = "agent@sha256:test"
            profile = root / "profile.json"
            profile.write_text(json.dumps({"images": [image], "targets": [{"path": "eval/targets/target-agent", "sha256": harness.file_sha256(agent)}]}))
            harness.ROOT = root
            harness.TARGETS = targets
            harness.validate_profile(profile, image, agent)
            with self.assertRaises(SystemExit):
                harness.validate_profile(profile, "other@sha256:test", agent)

    def test_profile_rejects_unreviewed_agent_and_image(self):
        harness = load_module("harness", "run_harness.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            targets = root / "eval" / "targets"
            targets.mkdir(parents=True)
            agent = targets / "agent"
            agent.write_text("#!/bin/sh\n")
            image = "registry.example/evaluator@sha256:test"
            profile = root / "profile.json"
            profile.write_text(json.dumps({"images": [], "targets": []}))
            harness.ROOT = root
            harness.TARGETS = targets
            with self.assertRaisesRegex(SystemExit, "reviewed sterile profile"):
                harness.validate_profile(profile, image, agent)


if __name__ == "__main__":
    unittest.main()
