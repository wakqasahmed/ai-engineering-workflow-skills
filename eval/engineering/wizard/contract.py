"""Shared outcome validator for the wizard skill.

Encodes the non-negotiable rules from skills/engineering/wizard/SKILL.md as
machine-checkable functions, independent of who produced the text being
checked (a hand-authored golden fixture, or a live model response). Both
run_eval.py (deterministic, golden-fixture layer) and any future model-harness
layer import this module so they score outcomes the same way.

A wizard's output artifact is an executable bash script, not markdown, so
`check_wizard_script_contract` does light static analysis of the generated
script rather than pattern-matching prose.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


ASK_SECRET_RE = re.compile(r"^\s*ask_secret\s+(\S+)", re.MULTILINE)
ASK_RE = re.compile(r"^\s*ask\s+(\S+)", re.MULTILINE)
WRITE_ENV_RE = re.compile(r"^\s*write_env\s+(\S+)", re.MULTILINE)
SET_SECRET_RE = re.compile(r"^\s*set_secret\s+(\S+)", re.MULTILINE)
STAGE_RE = re.compile(r"^\s*stage\s+\"", re.MULTILINE)
CONFIRM_RE = re.compile(r"^\s*confirm\s+\"", re.MULTILINE)
TOTAL_STAGES_RE = re.compile(r"^TOTAL_STAGES=(\d+)\s*$", re.MULTILINE)
STAGES_MARKER = "# STAGES: author this section."


@dataclass
class ContractResult:
    failures: list = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures

    def add(self, message: str) -> None:
        self.failures.append(message)


def check_wizard_script_contract(
    script_text: str,
    expected_stage_count: int | None = None,
    expected_env_names: list[str] | None = None,
    expected_secret_names: list[str] | None = None,
    requires_confirm_before_irreversible: bool = False,
) -> ContractResult:
    result = ContractResult()

    if not script_text.startswith("#!/usr/bin/env bash"):
        result.add("script has no bash shebang")
    if "set -euo pipefail" not in script_text:
        result.add("script does not set -euo pipefail")
    if STAGES_MARKER not in script_text:
        result.add(
            "script does not carry the library/STAGES boundary — it may be hand-rolled "
            "instead of built from template.sh"
        )

    asked_secret_names = set(ASK_SECRET_RE.findall(script_text))
    asked_plain_names = set(ASK_RE.findall(script_text)) - asked_secret_names
    written_env_names = set(WRITE_ENV_RE.findall(script_text))
    set_secret_names = set(SET_SECRET_RE.findall(script_text))

    for secret_name in expected_secret_names or []:
        if secret_name not in asked_secret_names:
            result.add(
                f"'{secret_name}' is not captured with ask_secret (hidden entry) — "
                f"either missing entirely or captured with plain ask"
            )
        if secret_name in asked_plain_names:
            result.add(f"'{secret_name}' is captured with plain ask, not ask_secret")
        if secret_name not in set_secret_names:
            result.add(f"'{secret_name}' is never set_secret'd to CI")

    for env_name in expected_env_names or []:
        if env_name not in written_env_names:
            result.add(f"'{env_name}' is never write_env'd — value would not persist locally")

    stage_count = len(STAGE_RE.findall(script_text))
    if expected_stage_count is not None and stage_count != expected_stage_count:
        result.add(f"expected {expected_stage_count} stage(s), found {stage_count}")

    total_stages_match = TOTAL_STAGES_RE.search(
        script_text[script_text.find(STAGES_MARKER):]
        if STAGES_MARKER in script_text
        else script_text
    )
    if total_stages_match and int(total_stages_match.group(1)) != stage_count:
        result.add(
            f"TOTAL_STAGES={total_stages_match.group(1)} does not match the actual "
            f"{stage_count} stage() call(s) — progress display would be wrong"
        )

    if requires_confirm_before_irreversible and not CONFIRM_RE.search(script_text):
        result.add(
            "this scenario is irreversible/destructive but the script never calls "
            "confirm before proceeding"
        )

    return result


def check_decline_response(text: str, decline_signal_patterns: list[str] | None = None) -> ContractResult:
    result = ContractResult()
    if not text or not text.strip():
        result.add("decline response is empty")
        return result

    if "TOTAL_STAGES=" in text or STAGE_RE.search(text):
        result.add(
            "response produces wizard-script content for a task the skill should have "
            "declined instead"
        )

    lower = text.lower()
    patterns = decline_signal_patterns or []
    if patterns and not any(pattern.lower() in lower for pattern in patterns):
        result.add(
            f"decline does not use any of the expected signal phrases: {patterns}"
        )

    return result
