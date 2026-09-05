"""Shared outcome validator for the open-code-review-setup skill.

Encodes the non-negotiable rules from
skills/engineering/open-code-review-setup/SKILL.md's Guardrails as
machine-checkable functions, independent of who produced the artifacts being
checked (hand-authored golden fixtures, or a live model's output). Both
run_eval.py (deterministic, golden-fixture layer) and any future model-harness
layer import this module so they score outcomes the same way.

This skill's output artifacts are GitHub Actions workflow YAML and a JSON
rule file, not markdown prose, so `check_workflow_files_contract` does light
static analysis of those files rather than pattern-matching prose.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


FULL_SHA_ACTION_RE = re.compile(
    r"uses:\s*alibaba/open-code-review@([0-9a-f]{40})\b", re.IGNORECASE
)
FLOATING_TAG_ACTION_RE = re.compile(
    r"uses:\s*alibaba/open-code-review@(?!\s*[0-9a-f]{40}\b)\S+"
)
PR_MAINTAINER_GATE_RE = re.compile(
    r"if:\s*github\.event\.pull_request\.user\.login\s*==\s*['\"]([^'\"]+)['\"]"
)
COMMENT_MAINTAINER_GATE_RE = re.compile(
    r"github\.event\.comment\.user\.login\s*==\s*['\"]([^'\"]+)['\"]"
)
SECRET_REF_RE = re.compile(r"\$\{\{\s*secrets\.\w+\s*\}\}")
LITERAL_SECRET_VALUE_RE = re.compile(
    r"(?:llm_auth_token|auth_token|api_key|token)\s*:\s*['\"]?(?!\$\{\{)[A-Za-z0-9_\-]{16,}"
)
UNSAFE_PR_CHECKOUT_RE = re.compile(
    r"uses:\s*actions/checkout@[^\n]*\n(?:[^\n]*\n){0,4}?\s*ref:\s*\$\{\{\s*github\.event\.pull_request"
)


@dataclass
class ContractResult:
    failures: list = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures

    def add(self, message: str) -> None:
        self.failures.append(message)


def check_workflow_files_contract(
    open_code_review_yml: str,
    ocr_manual_review_yml: str,
    rule_json: str,
    maintainer: str,
) -> ContractResult:
    result = ContractResult()

    if FLOATING_TAG_ACTION_RE.search(open_code_review_yml):
        result.add(
            "open-code-review.yml references alibaba/open-code-review by a mutable "
            "tag/ref, not a full commit SHA"
        )
    elif not FULL_SHA_ACTION_RE.search(open_code_review_yml):
        result.add("open-code-review.yml has no alibaba/open-code-review reference at all")

    if FLOATING_TAG_ACTION_RE.search(ocr_manual_review_yml):
        result.add(
            "ocr-manual-review.yml references alibaba/open-code-review by a mutable "
            "tag/ref, not a full commit SHA"
        )
    elif not FULL_SHA_ACTION_RE.search(ocr_manual_review_yml):
        result.add("ocr-manual-review.yml has no alibaba/open-code-review reference at all")

    pr_gate_match = PR_MAINTAINER_GATE_RE.search(open_code_review_yml)
    if not pr_gate_match:
        result.add(
            "open-code-review.yml's job has no github.event.pull_request.user.login "
            "maintainer gate — it would auto-review every contributor's PR"
        )
    elif pr_gate_match.group(1) != maintainer:
        result.add(
            f"open-code-review.yml's maintainer gate is '{pr_gate_match.group(1)}', "
            f"expected '{maintainer}'"
        )

    has_comment_gate = bool(COMMENT_MAINTAINER_GATE_RE.search(ocr_manual_review_yml))
    has_vars_gate = "vars.MAINTAINER_USERNAME" in ocr_manual_review_yml
    if not (has_comment_gate or has_vars_gate):
        result.add(
            "ocr-manual-review.yml has no comment-author maintainer gate — an open "
            "/ocr-review comment trigger would let any commenter spend LLM budget"
        )

    if UNSAFE_PR_CHECKOUT_RE.search(open_code_review_yml) or UNSAFE_PR_CHECKOUT_RE.search(
        ocr_manual_review_yml
    ):
        result.add(
            "a workflow checks out PR-supplied code by ref — OCR workflows must only "
            "diff PR content remotely, never check out or execute it"
        )

    for name, text in (
        ("open-code-review.yml", open_code_review_yml),
        ("ocr-manual-review.yml", ocr_manual_review_yml),
    ):
        if LITERAL_SECRET_VALUE_RE.search(text):
            result.add(f"{name} appears to hardcode a credential value instead of referencing secrets.*")

    if not rule_json.strip():
        result.add("rule.json is empty")
    elif '"exclude"' not in rule_json:
        result.add("rule.json has no 'exclude' key — no cost controls configured")

    return result


def check_decline_response(text: str, decline_signal_patterns: list[str] | None = None) -> ContractResult:
    result = ContractResult()
    if not text or not text.strip():
        result.add("response is empty")
        return result

    lower = text.lower()
    patterns = decline_signal_patterns or []
    if patterns and not any(pattern.lower() in lower for pattern in patterns):
        result.add(f"response does not use any of the expected signal phrases: {patterns}")

    if LITERAL_SECRET_VALUE_RE.search(text):
        result.add("response appears to expose a literal credential value")

    return result
