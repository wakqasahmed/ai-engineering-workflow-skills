#!/usr/bin/env python3
"""Deterministic verification of PR governance: OCR finding dispositions and agent metadata labels."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


DISPOSITION_PATTERN = re.compile(
    r"\A<!-- ocr-disposition:(\d+) -->\r?\n"
    r"Disposition: (fixed|deferred|declined)\r?\n"
    r"Reason: (\S(?:[^\r\n]*\S)?)\Z",
)
AGENT_LABEL_PATTERN = re.compile(r"^agent:([a-zA-Z0-9.-]+)-(low|medium|high)-(implementer|reviewer|fixer|operator)$")
AUTHORIZED_DISPOSITION_ASSOCIATIONS = frozenset({"OWNER", "MEMBER", "COLLABORATOR"})
RESOLVED_MODEL_ID_PATTERN = re.compile(
    r"^-\s*Resolved model ID:\s*(.+?)\s*$", re.MULTILINE
)
HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)


def extract_resolved_model_id(pr_body: str | None) -> str | None:
    """Pull the single 'Resolved model ID' value out of the PR body's Agent
    Metadata section (see the PR template in ai-agent-pr-metadata/SKILL.md).
    Returns None when the field is missing, still the unfilled template
    placeholder, or literally 'unavailable' — all three mean the same thing
    for verification purposes: no resolved model ID to check a label against.
    """
    if not pr_body:
        return None
    match = RESOLVED_MODEL_ID_PATTERN.search(pr_body)
    if not match:
        return None
    value = HTML_COMMENT_PATTERN.sub("", match.group(1)).strip()
    if not value or value.lower() == "unavailable":
        return None
    return value


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
        if c.get("author_association") not in AUTHORIZED_DISPOSITION_ASSOCIATIONS:
            continue
        match = DISPOSITION_PATTERN.fullmatch(c.get("body") or "")
        if not match:
            continue
        comment_id = int(match.group(1))
        dispositions[comment_id] = {
            "disposition": match.group(2),
            "reason": match.group(3),
            "comment_id": comment_id,
        }
    return dispositions


def load_allowed_legacy_labels(path: str | Path | None) -> set[str]:
    if not path:
        return set()
    baseline = load_json_file(path)
    if not isinstance(baseline, dict) or not isinstance(baseline.get("allowed_legacy_labels"), list):
        raise ValueError("Legacy agent label baseline must contain an 'allowed_legacy_labels' list")
    labels = baseline["allowed_legacy_labels"]
    if not all(isinstance(label, str) for label in labels):
        raise ValueError("Legacy agent label baseline entries must be strings")
    return set(labels)


def verify_governance(
    head_sha: str | None,
    review_comments: list[dict],
    issue_comments: list[dict],
    pr_commits: list[dict],
    resolved_model_id: str | None = None,
    new_agent_label: str | None = None,
    agent_labels: list[str] | None = None,
    legacy_baseline_path: str | Path | None = None,
) -> list[str]:
    failures = []
    target_sha = find_latest_head_sha(head_sha, pr_commits)

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

    try:
        allowed_legacy_labels = load_allowed_legacy_labels(legacy_baseline_path)
    except (json.JSONDecodeError, OSError, ValueError) as error:
        failures.append(f"Invalid legacy agent label baseline: {error}")
        allowed_legacy_labels = set()

    if agent_labels is not None and (
        not isinstance(agent_labels, list) or not all(isinstance(label, str) for label in agent_labels)
    ):
        failures.append("Current PR agent labels must be a JSON list of strings")
        labels_to_validate = []
    else:
        labels_to_validate = list(agent_labels or [])
    if new_agent_label:
        labels_to_validate.append(new_agent_label)

    for agent_label in labels_to_validate:
        if agent_label in allowed_legacy_labels:
            continue
        match = AGENT_LABEL_PATTERN.fullmatch(agent_label)
        if not match:
            failures.append(
                f"Agent label '{agent_label}' does not match format 'agent:<model>-<effort>-<role>'"
            )
            continue
        # A label not in the legacy baseline is new on this PR. A new label with no
        # resolved model ID to check it against is not a pass-by-default case — it
        # means the provenance claim the label makes cannot be verified at all.
        if not resolved_model_id:
            failures.append(
                f"Agent label '{agent_label}' is new (not in the legacy baseline) but no "
                f"resolved model ID is available to verify it against"
            )
            continue
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
    parser.add_argument("--agent-labels", required=False, help="Path to JSON list of current PR agent labels")
    parser.add_argument("--legacy-baseline", required=False, help="Path to legacy agent labels baseline JSON")
    parser.add_argument(
        "--pr-json",
        required=False,
        help=(
            "Path to the PR's raw API JSON ('gh api .../pulls/N'). Used to extract "
            "'Resolved model ID' from the PR body's Agent Metadata section when "
            "--resolved-model-id is not passed explicitly."
        ),
    )

    args = parser.parse_args()

    review_comments = load_json_file(args.review_comments)
    issue_comments = load_json_file(args.issue_comments)
    pr_commits = load_json_file(args.pr_commits)
    agent_labels = load_json_file(args.agent_labels)

    resolved_model_id = args.resolved_model_id
    if not resolved_model_id and args.pr_json:
        pr_json = load_json_file(args.pr_json)
        pr_body = pr_json.get("body") if isinstance(pr_json, dict) else None
        resolved_model_id = extract_resolved_model_id(pr_body)

    failures = verify_governance(
        head_sha=args.head_sha,
        review_comments=review_comments,
        issue_comments=issue_comments,
        pr_commits=pr_commits,
        resolved_model_id=resolved_model_id,
        new_agent_label=args.new_agent_label,
        agent_labels=agent_labels,
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
