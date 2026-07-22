#!/usr/bin/env python3
import importlib.util
import json
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
            "harness_version": "1",
            "response": response,
        }
        for case in cases
        for condition in ("enabled", "disabled")
        for trial in range(1, 4)
    ]


class HarnessTests(unittest.TestCase):
    def test_outcome_workflow_passes_dispatch_inputs_through_step_environment(self):
        workflow = (EVAL_DIR.parents[3] / ".github" / "workflows" / "decompose-to-issues-outcome-eval.yml").read_text()
        enabled_step = workflow.split("      - name: Run isolated enabled and disabled trials")[1]
        validator_step = enabled_step.split("      - name: Validate outcome delta and safety threshold")[1]
        run_sections = [
            enabled_step.split("      - name: Validate outcome delta and safety threshold")[0].split("run: >-\n", 1)[1],
            validator_step.split("      - uses: actions/upload-artifact@v4")[0].split("run: >-\n", 1)[1],
        ]

        self.assertEqual(len(run_sections), 2)
        self.assertNotIn("${{ inputs.", "".join(run_sections))
        self.assertIn("AGENT: ${{ inputs.agent }}", workflow)
        self.assertIn('"$AGENT"', workflow)
        self.assertIn('"$TRIALS"', workflow)

    def test_validator_rejects_runner_verdict_fields(self):
        validator = load_module("validator", "validate-harness-results.py")
        artifact = records("Create issue one.")[0]
        artifact["outcome"] = "forged-pass"
        failures, _ = validator.validate([artifact], 3)
        self.assertTrue(any("invalid observable artifact" in failure for failure in failures))

    def test_validator_scores_observable_issue_output(self):
        validator = load_module("validator", "validate-harness-results.py")
        failures, _ = validator.validate(records("I will implement this as one issue."), 3)
        self.assertTrue(any("below the 80% outcome threshold" in failure for failure in failures))

    def test_validator_accepts_enabled_outcome_delta_without_skill_metadata(self):
        validator = load_module("validator", "validate-harness-results.py")
        positive = "Issue 1. Issue 2. Acceptance criteria. Verification. Dependencies. Catalog inventory order reconciliation event audit retention export conflict sync rollout analytics plan payment invoice entitlement support."
        negative = "README teh parseDate UTC Button.css padding 12px UserFormatter Unknown user null lodash 4.17.21 npm test regression test."
        results = []
        for case in json.loads((EVAL_DIR / "fixtures" / "held-out.json").read_text())["cases"]:
            response = positive if case["id"] in {
                "multi-surface-checkout", "marketplace-integration-roadmap", "tenant-audit-program",
                "mobile-offline-capability", "self-service-billing",
            } else negative
            for trial in range(1, 4):
                results.append({"case_id": case["id"], "condition": "enabled", "trial": trial, "model": "test-agent", "harness_version": "1", "response": response})
                results.append({"case_id": case["id"], "condition": "disabled", "trial": trial, "model": "test-agent", "harness_version": "1", "response": "I will implement this as one issue."})
        failures, _ = validator.validate(results, 3)
        self.assertFalse(failures)

    def test_disabled_workspace_contains_no_skill_or_fixture(self):
        harness = load_module("harness", "run_harness.py")
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            agent = workspace / "source-agent"
            agent.write_text("#!/bin/sh\n")
            agent.chmod(0o755)
            harness.prepare_workspace(workspace, agent, {"prompt": "Split this work."}, "disabled")
            self.assertEqual(
                {path.name for path in workspace.iterdir()},
                {"case.json", "runner", "source-agent", "target-agent"},
            )

    def test_disabled_adapter_cannot_load_a_skill(self):
        adapter = EVAL_DIR / "target-agent-adapter.py"
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "case.json").write_text(json.dumps({"prompt": "Split this work."}))
            target = workspace / "target-agent"
            target.write_text(
                "#!/usr/bin/env python3\n"
                "import json, pathlib, sys\n"
                "request = json.load(sys.stdin)\n"
                "if 'skill_path' in request or pathlib.Path('SKILL.md').exists(): raise SystemExit(1)\n"
                "print('Proceed with the exact requested change.')\n"
            )
            target.chmod(0o755)
            result = subprocess.run(
                ["python3", str(adapter)], text=True, capture_output=True, check=True,
                env={"HARNESS_WORKSPACE": str(workspace), "HOME": str(workspace), "PATH": "/usr/local/bin:/usr/bin:/bin"},
            )
        self.assertEqual(json.loads(result.stdout), {"response": "Proceed with the exact requested change."})

    def test_isolated_command_uses_empty_home_non_root_and_no_network(self):
        harness = load_module("harness", "run_harness.py")
        command = harness.isolated_command(Path("/tmp/workspace"), "agent@sha256:test")
        self.assertIn("--network", command)
        self.assertIn("none", command)
        self.assertIn("65532:65532", command)
        self.assertIn("HOME=/home/agent", command)
        self.assertIn("/home/agent:rw,noexec,nosuid,size=8m", command)


if __name__ == "__main__":
    unittest.main()
