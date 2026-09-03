#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = ROOT / "support" / "ai-engineering-workflow" / "scripts" / "verify-pr-governance.py"

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


if __name__ == "__main__":
    unittest.main()
