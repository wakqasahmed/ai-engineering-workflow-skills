#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = ROOT / "support" / "ai-engineering-workflow" / "scripts" / "verify-pr-governance.py"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "ocr-disposition-gate.yml"
LEGACY_BASELINE_PATH = ROOT / "support" / "ai-engineering-workflow" / "legacy-agent-labels.json"

spec = importlib.util.spec_from_file_location("verify_pr_governance", SCRIPT_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestVerifyPrGovernance(unittest.TestCase):
    def test_no_findings_passes(self):
        failures = mod.verify_governance(
            head_sha="head123",
            review_comments=[],
            issue_comments=[],
            pr_commits=[{"sha": "head123"}],
        )
        self.assertEqual(failures, [])

    def test_undispositioned_ocr_finding_fails(self):
        finding = {
            "id": 101,
            "commit_id": "head123",
            "body": "<!-- ocr-1 --> Potential null pointer dereference",
            "user": {"login": "github-actions[bot]"},
        }
        failures = mod.verify_governance(
            head_sha="head123",
            review_comments=[finding],
            issue_comments=[],
            pr_commits=[{"sha": "head123"}],
        )
        self.assertEqual(len(failures), 1)
        self.assertIn("Undispositioned OCR finding 101", failures[0])

    def test_dispositioned_non_blocking_passes(self):
        finding = {
            "id": 102,
            "commit_id": "head123",
            "body": "<!-- ocr-2 --> Suggestion: rename variable for clarity",
            "user": {"login": "github-actions[bot]"},
        }
        disposition_comment = {
            "id": 202,
            "body": "<!-- ocr-disposition:102 -->\nDisposition: declined\nReason: Existing name reflects domain terminology.",
            "author_association": "COLLABORATOR",
        }
        failures = mod.verify_governance(
            head_sha="head123",
            review_comments=[finding],
            issue_comments=[disposition_comment],
            pr_commits=[{"sha": "head123"}],
        )
        self.assertEqual(failures, [])

    def test_blocking_finding_must_be_fixed(self):
        finding = {
            "id": 103,
            "commit_id": "head123",
            "body": "<!-- ocr-3 --> Blocking: security vulnerability detected",
            "user": {"login": "github-actions[bot]"},
        }
        disposition_comment = {
            "id": 203,
            "body": "<!-- ocr-disposition:103 -->\nDisposition: deferred\nReason: Will fix in follow up.",
            "author_association": "OWNER",
        }
        failures = mod.verify_governance(
            head_sha="head123",
            review_comments=[finding],
            issue_comments=[disposition_comment],
            pr_commits=[{"sha": "head123"}],
        )
        self.assertEqual(len(failures), 1)
        self.assertIn("Blocking OCR finding 103 must be 'Disposition: fixed'", failures[0])

    def test_valid_agent_label(self):
        failures = mod.verify_governance(
            head_sha="head123",
            review_comments=[],
            issue_comments=[],
            pr_commits=[{"sha": "head123"}],
            resolved_model_id="gpt5.6-terra",
            new_agent_label="agent:gpt5.6-terra-medium-implementer",
        )
        self.assertEqual(failures, [])

    def test_invalid_agent_label_format(self):
        failures = mod.verify_governance(
            head_sha="head123",
            review_comments=[],
            issue_comments=[],
            pr_commits=[{"sha": "head123"}],
            new_agent_label="invalid-agent-label",
        )
        self.assertEqual(len(failures), 1)
        self.assertIn("does not match format", failures[0])

    def test_non_collaborator_disposition_is_ignored(self):
        finding = {
            "id": 104,
            "commit_id": "head123",
            "body": "<!-- ocr-4 --> Suggestion: validate the caller.",
            "user": {"login": "github-actions[bot]"},
        }
        disposition_comment = {
            "id": 204,
            "body": "<!-- ocr-disposition:104 -->\nDisposition: fixed\nReason: The caller is now validated.",
            "author_association": "CONTRIBUTOR",
        }

        failures = mod.verify_governance(
            head_sha="head123",
            review_comments=[finding],
            issue_comments=[disposition_comment],
            pr_commits=[{"sha": "head123"}],
        )

        self.assertEqual(len(failures), 1)
        self.assertIn("Undispositioned OCR finding 104", failures[0])

    def test_owner_member_and_collaborator_dispositions_are_accepted(self):
        for association in ("OWNER", "MEMBER", "COLLABORATOR"):
            with self.subTest(association=association):
                comment = {
                    "body": "<!-- ocr-disposition:105 -->\nDisposition: fixed\nReason: The finding is resolved.",
                    "author_association": association,
                }
                dispositions = mod.extract_dispositions([comment], [])
                self.assertIn(105, dispositions)

    def test_other_author_associations_are_rejected(self):
        for association in (
            "CONTRIBUTOR",
            "FIRST_TIMER",
            "FIRST_TIME_CONTRIBUTOR",
            "MANNEQUIN",
            "NONE",
            None,
        ):
            with self.subTest(association=association):
                comment = {
                    "body": "<!-- ocr-disposition:105 -->\nDisposition: fixed\nReason: The finding is resolved.",
                    "author_association": association,
                }
                self.assertEqual(mod.extract_dispositions([comment], []), {})

    def test_disposition_with_trailing_content_is_rejected(self):
        comment = {
            "body": (
                "<!-- ocr-disposition:106 -->\n"
                "Disposition: fixed\n"
                "Reason: The finding is resolved.\n"
                "Additional explanation that is outside the exact record."
            ),
            "author_association": "MEMBER",
        }

        self.assertEqual(mod.extract_dispositions([comment], []), {})

    def test_repeated_disposition_block_is_rejected(self):
        block = "<!-- ocr-disposition:107 -->\nDisposition: fixed\nReason: The finding is resolved."
        comment = {
            "body": f"{block}\n{block}",
            "author_association": "OWNER",
        }

        self.assertEqual(mod.extract_dispositions([comment], []), {})

    def test_disposition_with_loose_field_spacing_is_rejected(self):
        comment = {
            "body": "<!-- ocr-disposition:108 -->\nDisposition:  fixed\nReason: The finding is resolved.",
            "author_association": "OWNER",
        }

        self.assertEqual(mod.extract_dispositions([comment], []), {})

    def test_legacy_agent_label_is_allowed_only_when_baselined(self):
        allowed = mod.verify_governance(
            head_sha="head123",
            review_comments=[],
            issue_comments=[],
            pr_commits=[{"sha": "head123"}],
            agent_labels=["agent:antigravity-default-implementer"],
            legacy_baseline_path=LEGACY_BASELINE_PATH,
        )
        rejected = mod.verify_governance(
            head_sha="head123",
            review_comments=[],
            issue_comments=[],
            pr_commits=[{"sha": "head123"}],
            agent_labels=["agent:antigravity-default-implementer"],
        )

        self.assertEqual(allowed, [])
        self.assertEqual(len(rejected), 1)
        self.assertIn("does not match format", rejected[0])


class TestResolvedModelIdEnforcement(unittest.TestCase):
    """Covers #174: a new (non-legacy) agent:* label must be checked against a
    resolved model ID, not silently passed when one is unavailable."""

    def test_matching_resolved_model_id_passes(self):
        failures = mod.verify_governance(
            head_sha="head123",
            review_comments=[],
            issue_comments=[],
            pr_commits=[{"sha": "head123"}],
            agent_labels=["agent:gpt5.6-terra-medium-implementer"],
            resolved_model_id="gpt5.6-terra",
        )
        self.assertEqual(failures, [])

    def test_mismatching_resolved_model_id_fails(self):
        failures = mod.verify_governance(
            head_sha="head123",
            review_comments=[],
            issue_comments=[],
            pr_commits=[{"sha": "head123"}],
            agent_labels=["agent:not-a-real-model-high-implementer"],
            resolved_model_id="gpt5.6-terra",
        )
        self.assertEqual(len(failures), 1)
        self.assertIn("does not match resolved model ID", failures[0])

    def test_missing_resolved_model_id_fails_a_new_label(self):
        """The exact bug #174 reports: a syntactically valid new label with no
        resolved model ID to check it against must not pass silently."""
        failures = mod.verify_governance(
            head_sha="head123",
            review_comments=[],
            issue_comments=[],
            pr_commits=[{"sha": "head123"}],
            agent_labels=["agent:not-a-real-model-high-implementer"],
        )
        self.assertEqual(len(failures), 1)
        self.assertIn("no resolved model ID is available", failures[0])

    def test_duplicate_agent_labels_each_fail_independently(self):
        failures = mod.verify_governance(
            head_sha="head123",
            review_comments=[],
            issue_comments=[],
            pr_commits=[{"sha": "head123"}],
            agent_labels=[
                "agent:not-a-real-model-high-implementer",
                "agent:not-a-real-model-high-implementer",
            ],
        )
        self.assertEqual(len(failures), 2)

    def test_unavailable_resolved_model_id_is_treated_as_missing(self):
        failures = mod.verify_governance(
            head_sha="head123",
            review_comments=[],
            issue_comments=[],
            pr_commits=[{"sha": "head123"}],
            agent_labels=["agent:gpt5.6-terra-medium-implementer"],
            resolved_model_id=mod.extract_resolved_model_id(
                "## Agent Metadata\n- Resolved model ID: unavailable\n"
            ),
        )
        self.assertEqual(len(failures), 1)
        self.assertIn("no resolved model ID is available", failures[0])

    def test_extract_resolved_model_id_reads_the_pr_template_field(self):
        body = (
            "## Agent Metadata\n\n"
            "Implementation/update agent:\n"
            "- Name: Codex GPT-5.6 Terra Medium\n"
            "- Resolved model ID: gpt5.6-terra\n"
            "- Metadata limitation: N/A\n"
        )
        self.assertEqual(mod.extract_resolved_model_id(body), "gpt5.6-terra")

    def test_extract_resolved_model_id_treats_unfilled_template_as_missing(self):
        body = (
            "- Resolved model ID: <!-- Runtime/orchestrator value, or unavailable "
            "with limitation below -->\n"
        )
        self.assertIsNone(mod.extract_resolved_model_id(body))

    def test_extract_resolved_model_id_treats_literal_unavailable_as_missing(self):
        self.assertIsNone(mod.extract_resolved_model_id("- Resolved model ID: unavailable\n"))

    def test_extract_resolved_model_id_handles_missing_body(self):
        self.assertIsNone(mod.extract_resolved_model_id(None))
        self.assertIsNone(mod.extract_resolved_model_id(""))


class TestOcrDispositionWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_checks_out_and_reports_status_on_resolved_pr_head(self):
        self.assertIn('head_sha=$(jq -er ".head.sha"', self.workflow)
        self.assertIn("ref: ${{ steps.pull_request.outputs.head_sha }}", self.workflow)
        self.assertIn('statuses/$HEAD_SHA', self.workflow)
        self.assertIn('--head-sha "$HEAD_SHA"', self.workflow)
        self.assertIn("statuses: write", self.workflow)

    def test_privileged_gate_executes_only_trusted_base_code(self):
        self.assertIn("pull_request_target:", self.workflow)
        self.assertNotIn("\n  pull_request:\n", self.workflow)
        self.assertIn("ref: ${{ steps.pull_request.outputs.base_sha }}", self.workflow)
        self.assertIn("working-directory: trusted-base", self.workflow)
        self.assertEqual(self.workflow.count("persist-credentials: false"), 2)

    def test_legacy_baseline_is_passed_to_governance_script(self):
        self.assertIn(
            "--legacy-baseline support/ai-engineering-workflow/legacy-agent-labels.json",
            self.workflow,
        )

    def test_pr_json_is_passed_to_governance_script(self):
        self.assertIn("--pr-json /tmp/pr-gov/pull-request.json", self.workflow)

    def test_api_failures_are_not_replaced_with_empty_evidence(self):
        self.assertNotIn('|| echo "[]"', self.workflow)
        self.assertNotRegex(self.workflow, re.compile(r"gh api .*\|\|", re.MULTILINE))
        self.assertGreaterEqual(self.workflow.count("set -euo pipefail"), 2)
        self.assertIn("state=failure", self.workflow)

    def test_all_evidence_api_calls_are_paginated_and_combined(self):
        evidence_calls = re.findall(
            r'^\s*gh api "repos/\$GITHUB_REPOSITORY/(?:pulls/\$PR_NUMBER/(?:comments|commits)|issues/\$PR_NUMBER/comments)\?per_page=100"[^\n]*$',
            self.workflow,
            re.MULTILINE,
        )

        self.assertEqual(len(evidence_calls), 3)
        self.assertEqual(self.workflow.count("| jq 'add'"), 3)
        for call in evidence_calls:
            self.assertIn("--paginate", call)
            self.assertIn("--slurp", call)


if __name__ == "__main__":
    unittest.main()
