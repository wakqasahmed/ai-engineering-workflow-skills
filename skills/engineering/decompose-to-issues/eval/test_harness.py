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

    def test_validator_rejects_keyword_soup_without_structured_issues(self):
        validator = load_module("validator", "validate-harness-results.py")
        response = "Issue 1. Issue 2. Acceptance criteria. Verification. Dependencies. Catalog inventory order reconciliation event audit retention export conflict sync rollout analytics plan payment invoice entitlement support."
        failures, _ = validator.validate(records(response), 3)
        self.assertTrue(any("below the 80% outcome threshold" in failure for failure in failures))

    def test_validator_rejects_issue_plan_for_direct_action_case(self):
        validator = load_module("validator", "validate-harness-results.py")
        response = json.dumps({
            "issues": [
                {"title": "Change README", "scope": "Correct the typo.", "acceptance_criteria": ["Typo is corrected."], "verification": ["Review README."], "dependencies": ["None."], "non_goals": ["No roadmap."]},
                {"title": "Review README", "scope": "Review the correction.", "acceptance_criteria": ["Review is complete."], "verification": ["Read the file."], "dependencies": ["Change README."], "non_goals": ["No other edits."]},
            ],
            "relationships": [{"from": 1, "to": 2, "type": "depends_on"}],
        })
        case = next(case for case in json.loads((EVAL_DIR / "fixtures" / "held-out.json").read_text())["cases"] if case["id"] == "readme-typo")
        self.assertFalse(validator.outcome_matches(response, case))

    def test_validator_accepts_enabled_outcome_delta_without_skill_metadata(self):
        validator = load_module("validator", "validate-harness-results.py")
        positive = json.dumps({
            "issues": [
                {"title": "Catalog and inventory sync", "scope": "Cart catalog inventory event audit conflict sync plan payment.", "acceptance_criteria": ["Changes are accepted."], "verification": ["Run focused tests."], "dependencies": ["None."], "non_goals": ["No unrelated changes."]},
                {"title": "Orders and operations", "scope": "Order reconciliation retention export rollout invoice support payment.", "acceptance_criteria": ["Operations are supported."], "verification": ["Run integration tests."], "dependencies": ["Catalog and inventory sync."], "non_goals": ["No manual deployment."]},
            ],
            "relationships": [{"from": 1, "to": 2, "type": "depends_on"}],
        })
        results = []
        for case in json.loads((EVAL_DIR / "fixtures" / "held-out.json").read_text())["cases"]:
            response = positive if case["expected_outcome"] == "issue_plan" else json.dumps({"direct_action": {"scope": "Apply " + " and ".join(case["expected_terms"]), "verification": ["Run the requested test."], "non_goals": ["Do not decompose the work."]}})
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
                "if 'response_contract' not in request: raise SystemExit(1)\n"
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
