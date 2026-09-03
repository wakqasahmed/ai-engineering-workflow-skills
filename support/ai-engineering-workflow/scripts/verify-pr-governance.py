#!/usr/bin/env python3
"""Deterministic verification of PR governance: OCR finding dispositions and agent metadata labels."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


DISPOSITION_PATTERN = re.compile(
    r"<!--\s*ocr-disposition:(\d+)\s*-->\s*\n\s*Disposition:\s*(fixed|deferred|declined)\s*\n\s*Reason:\s*(.+)",
    re.MULTILINE | re.IGNORECASE,
)
AGENT_LABEL_PATTERN = re.compile(r"^agent:([a-zA-Z0-9.-]+)-(low|medium|high)-(implementer|reviewer|fixer|operator)$")


def load_json_file(path: str | Path | None) -> list[dict] | dict:
    if not path:
        return []
    p = Path(path)
    if not p.is_file():
        return []
    content = p.read_text(encoding="utf-8").strip()
    if not content:
        return []
    return json.loads(content)


def find_latest_head_sha(head_sha_arg: str | None, pr_commits: list[dict]) -> str | None:
    if head_sha_arg:
        return head_sha_arg
    if pr_commits and isinstance(pr_commits, list):
        last = pr_commits[-1]
        return last.get("sha")
    return None


def is_ocr_finding(comment: dict) -> bool:
    body = comment.get("body", "")
    user = comment.get("user", {}) or {}
    login = user.get("login", "")
    if "<!-- ocr-" in body or "<!-- ocr:" in body:
        return True
    if "alibaba-code-review" in body or "Open Code Review" in body:
        return True
    if login == "github-actions[bot]" and any(marker in body.lower() for marker in ["finding", "suggestion", "blocking:"]):
        return True
    return False


def extract_dispositions(issue_comments: list[dict], review_comments: list[dict]) -> dict[int, dict[str, str]]:
    dispositions = {}
    all_comments = []
    if isinstance(issue_comments, list):
        all_comments.extend(issue_comments)
    if isinstance(review_comments, list):
        all_comments.extend(review_comments)

    for c in all_comments:
        body = c.get("body", "")
        for match in DISPOSITION_PATTERN.finditer(body):
            comment_id = int(match.group(1))
            disposition = match.group(2).lower()
            reason = match.group(3).strip()
            dispositions[comment_id] = {
                "disposition": disposition,
                "reason": reason,
                "comment_id": comment_id,
            }
    return dispositions


def verify_governance(
    head_sha: str | None,
    review_comments: list[dict],
    issue_comments: list[dict],
    pr_commits: list[dict],
    resolved_model_id: str | None = None,
    new_agent_label: str | None = None,
    legacy_baseline_path: str | Path | None = None,
) -> list[str]:
    failures = []
    target_sha = find_latest_head_sha(head_sha, pr_commits)

    # 1. Inspect OCR review comments on latest head
    ocr_findings = []
    if isinstance(review_comments, list):
        for c in review_comments:
            c_sha = c.get("commit_id") or c.get("original_commit_id")
            # If target_sha is known, only inspect comments targeting latest head
            if target_sha and c_sha and c_sha != target_sha:
                continue
            if is_ocr_finding(c):
                ocr_findings.append(c)

    dispositions = extract_dispositions(issue_comments, review_comments)

    for finding in ocr_findings:
        fid = finding.get("id")
        if fid is None:
            continue
        body = finding.get("body", "")
        is_blocking = "blocking:" in body.lower()

        if fid not in dispositions:
            failures.append(f"Undispositioned OCR finding {fid} on commit {target_sha or 'unknown'}")
        else:
            disp = dispositions[fid]
            if is_blocking and disp["disposition"] != "fixed":
                failures.append(
                    f"Blocking OCR finding {fid} must be 'Disposition: fixed', but found '{disp['disposition']}'"
                )

    # 2. Validate agent label if provided
    if new_agent_label:
        match = AGENT_LABEL_PATTERN.match(new_agent_label)
        if not match:
            failures.append(
                f"Proposed agent label '{new_agent_label}' does not match format 'agent:<model>-<effort>-<role>'"
            )
        elif resolved_model_id:
            label_model = match.group(1)
            if label_model != resolved_model_id:
                failures.append(
                    f"Agent label model '{label_model}' does not match resolved model ID '{resolved_model_id}'"
                )

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify PR governance: OCR dispositions and agent metadata.")
    parser.add_argument("--head-sha", required=False, help="Target head commit SHA")
    parser.add_argument("--review-comments", required=True, help="Path to JSON file of pull request review comments")
    parser.add_argument("--issue-comments", required=True, help="Path to JSON file of issue comments")
    parser.add_argument("--pr-commits", required=True, help="Path to JSON file of PR commits")
    parser.add_argument("--resolved-model-id", required=False, help="Resolved runtime model identifier")
    parser.add_argument("--new-agent-label", required=False, help="Proposed new agent label to validate")
    parser.add_argument("--legacy-baseline", required=False, help="Path to legacy agent labels baseline JSON")

    args = parser.parse_args()

    review_comments = load_json_file(args.review_comments)
    issue_comments = load_json_file(args.issue_comments)
    pr_commits = load_json_file(args.pr_commits)

    failures = verify_governance(
        head_sha=args.head_sha,
        review_comments=review_comments,
        issue_comments=issue_comments,
        pr_commits=pr_commits,
        resolved_model_id=args.resolved_model_id,
        new_agent_label=args.new_agent_label,
        legacy_baseline_path=args.legacy_baseline,
    )

    if failures:
        print("FAIL: PR governance verification failed:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print("PASS: OCR disposition gate and PR governance verification passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
