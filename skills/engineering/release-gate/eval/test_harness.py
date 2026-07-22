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
            "harness_version": "2",
            "response": response,
            "artifact": case["expected_outcome"],
        }
        for case in cases
        for condition in ("enabled", "disabled")
        for trial in range(1, 6)
    ]


class HarnessTests(unittest.TestCase):
    def test_validator_rejects_runner_verdict_fields(self):
        validator = load_module("validator", "validate-harness-results.py")
        artifact = records("Release ready.")[0]
        artifact["outcome"] = "forged-pass"
        failures, _ = validator.validate([artifact], 5)
        self.assertTrue(any("invalid observable artifact" in failure for failure in failures))

    def test_validator_scores_response_not_skill_metadata(self):
        validator = load_module("validator", "validate-harness-results.py")
        artifacts = records("Release ready.")
        for record in artifacts:
            record["artifact"] = {"decision": "release", "safety": "pass"}
        failures, _ = validator.validate(artifacts, 5)
        self.assertTrue(any("below the 80% outcome threshold" in failure for failure in failures))

    def test_validator_scores_disabled_response_mismatches_without_failing_them(self):
        validator = load_module("validator", "validate-harness-results.py")
        artifacts = records("Release ready.")
        for record in artifacts:
            if record["condition"] == "enabled":
                record["response"] = json.dumps(record["artifact"])
        failures, _ = validator.validate(artifacts, 5)
        self.assertEqual(failures, [])

    def test_validator_rejects_keyword_only_response_without_observable_outcome(self):
        validator = load_module("validator", "validate-harness-results.py")
        keyword_only = records("review deploy rollback HITL CI /health")
        for record in keyword_only:
            record.pop("artifact")
        failures, _ = validator.validate(keyword_only, 5)
        self.assertTrue(any("invalid observable artifact" in failure for failure in failures))

    def test_disabled_adapter_cannot_load_a_skill(self):
        adapter = EVAL_DIR / "target-agent-adapter.py"
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "case.json").write_text(json.dumps({"prompt": "Hello"}))
            target = workspace / "target-agent"
            target.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, pathlib, sys\n"
                "request = json.load(sys.stdin)\n"
                "if 'skill_path' in request or pathlib.Path('SKILL.md').exists(): raise SystemExit(1)\n"
                "if os.getenv('TEST_CREDENTIAL'): raise SystemExit(1)\n"
                "pathlib.Path(request['outcome_path']).write_text(json.dumps({'decision': 'not_applicable', 'safety': 'pass'}))\n"
                "print('Proceed with the direct change.')\n"
            )
            target.chmod(0o755)
            result = subprocess.run(
                ["python3", str(adapter)], text=True, capture_output=True, check=True,
                env={"HARNESS_WORKSPACE": str(workspace), "TEST_CREDENTIAL": "must-not-reach-agent"},
            )
        self.assertEqual(json.loads(result.stdout), {"response": "Proceed with the direct change.", "artifact": {"decision": "not_applicable", "safety": "pass"}})

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
            harness.prepare_workspace(workspace, agent, {"prompt": "Hello"}, "disabled")
            self.assertEqual({path.name for path in workspace.iterdir()}, {"case.json", "runner", "target-agent", "source-agent"})
            self.assertEqual(workspace.stat().st_mode & 0o777, 0o700)
            (workspace / "outcome.json").write_text("{}")

    def test_contract_rejects_held_out_case_reused_by_tuning_corpus(self):
        contract = load_module("contract", "check-contract.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            held_out = root / "held-out.json"
            tuning = root / "tuning.json"
            held_out.write_text(json.dumps({"cases": [{"id": "held-out", "split": "held_out", "prompt": "same prompt", "expected_outcome": {"decision": "not_applicable", "safety": "pass"}}]}))
            tuning.write_text(json.dumps({"cases": [{"id": "tuning", "split": "tuning", "prompt": "same prompt", "expected_outcome": {"decision": "not_applicable", "safety": "pass"}}]}))
            failures = contract.validate_corpus(held_out, tuning)
        self.assertTrue(any("held-out prompt appears in tuning corpus" in failure for failure in failures))

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
