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
                "print('Proceed with the direct change.')\n"
            )
            target.chmod(0o755)
            result = subprocess.run(
                ["python3", str(adapter)], text=True, capture_output=True, check=True,
                env={"HARNESS_WORKSPACE": str(workspace), "TEST_CREDENTIAL": "must-not-reach-agent"},
            )
        self.assertEqual(json.loads(result.stdout), {"response": "Proceed with the direct change."})

    def test_isolated_command_uses_an_empty_home_and_non_root_user(self):
        harness_spec = importlib.util.spec_from_file_location("harness", EVAL_DIR / "run_harness.py")
        harness = importlib.util.module_from_spec(harness_spec)
        harness_spec.loader.exec_module(harness)
        command = harness.isolated_command(Path("/tmp/workspace"), "agent@sha256:test")
        self.assertNotIn("HARNESS_CONDITION", " ".join(command))
        self.assertNotIn("HARNESS_TRIAL", " ".join(command))
        self.assertIn("65532:65532", command)
        self.assertIn("HOME=/home/agent", command)
        self.assertIn("/home/agent:rw,noexec,nosuid,size=8m", command)

    def test_disabled_workspace_contains_no_skill_or_fixture(self):
        harness_spec = importlib.util.spec_from_file_location("harness", EVAL_DIR / "run_harness.py")
        harness = importlib.util.module_from_spec(harness_spec)
        harness_spec.loader.exec_module(harness)
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            agent = workspace / "source-agent"
            agent.write_text("#!/bin/sh\n")
            agent.chmod(0o755)
            harness.prepare_workspace(workspace, agent, {"prompt": "Hello"}, "disabled")
            self.assertEqual({path.name for path in workspace.iterdir()}, {"case.json", "runner", "target-agent", "source-agent"})

    def test_attestation_binds_the_sterile_image_and_agent(self):
        harness_spec = importlib.util.spec_from_file_location("harness", EVAL_DIR / "run_harness.py")
        harness = importlib.util.module_from_spec(harness_spec)
        harness_spec.loader.exec_module(harness)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agent = root / "target-agent"
            agent.write_text("#!/bin/sh\n")
            image = "agent@sha256:test"
            attestation = root / "attestation.json"
            attestation.write_text(json.dumps({
                "image": image,
                "agent_sha256": harness.file_sha256(agent),
                "claims": {name: True for name in ("no_ambient_credentials", "no_held_out_fixtures", "no_preinstalled_skills", "empty_home", "non_root")},
            }))
            harness.ROOT = root
            harness.validate_attestation(attestation, image, agent)
            with self.assertRaises(SystemExit):
                harness.validate_attestation(attestation, "other@sha256:test", agent)


if __name__ == "__main__":
    unittest.main()
