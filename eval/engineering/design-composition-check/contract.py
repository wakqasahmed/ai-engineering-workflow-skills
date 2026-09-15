"""Shared outcome validator for the design-composition-check skill.

Encodes the non-negotiable rules from
skills/engineering/design-composition-check/SKILL.md as machine-checkable
functions, independent of who produced the text being checked (a
hand-authored golden fixture, or a live model response). run_eval.py
(deterministic, golden-fixture layer) imports this module so any future
model-harness layer would score outcomes the same way.

The skill's output artifact is a markdown report posted on a GitHub issue,
so these checks parse that report's structure (as defined in SKILL.md's
"Report format" section) rather than doing free-form prose matching.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

VALID_VERDICTS = (
    "Composes cleanly",
    "Composes with a filed gap",
    "Does not compose — rework before scaling",
)

SCREENS_SECTION_RE = re.compile(r"^## Screens Selected\n(.*?)(?=\n## |\Z)", re.MULTILINE | re.DOTALL)
VERDICT_SECTION_RE = re.compile(r"^## Verdict\n(.*?)(?=\n## |\Z)", re.MULTILINE | re.DOTALL)
GAPS_SECTION_RE = re.compile(r"^## Gaps\n(.*?)(?=\n## |\Z)", re.MULTILINE | re.DOTALL)
TRIGGER_SECTION_RE = re.compile(r"^## Trigger\n(.*?)(?=\n## |\Z)", re.MULTILINE | re.DOTALL)
SCREEN_LINE_RE = re.compile(r"^- (.+?) — (.+)$", re.MULTILINE)
GAP_LINE_RE = re.compile(r"^- (.+?) — (Correctable|Genuine): (.+)$", re.MULTILINE)


@dataclass
class ContractResult:
    failures: list = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures

    def add(self, message: str) -> None:
        self.failures.append(message)


def check_composition_report(
    report_text: str,
    hard_screens: list[str],
    easy_screens: list[str] | None = None,
    expected_verdict: str | None = None,
    min_gap_count: int = 0,
    expected_gap_classes: dict[str, str] | None = None,
) -> ContractResult:
    result = ContractResult()
    easy_screens = easy_screens or []
    expected_gap_classes = expected_gap_classes or {}

    if not TRIGGER_SECTION_RE.search(report_text):
        result.add("report is missing the '## Trigger' section")

    screens_match = SCREENS_SECTION_RE.search(report_text)
    if not screens_match:
        result.add("report is missing the '## Screens Selected' section")
        selected_names: list[str] = []
    else:
        selected_names = [name.strip() for name, _reason in SCREEN_LINE_RE.findall(screens_match.group(1))]

    if not (1 <= len(selected_names) <= 2):
        result.add(f"expected 1-2 selected screens, found {len(selected_names)}: {selected_names}")

    for name in selected_names:
        if name in easy_screens:
            result.add(f"'{name}' is one of the easy/skip screens and must not be selected as an anchor")
        if hard_screens and name not in hard_screens:
            result.add(f"'{name}' is not one of the hardest screens in scope for this fixture")

    if hard_screens:
        missing_hard = [name for name in hard_screens if name not in selected_names]
        if len(selected_names) < min(2, len(hard_screens)) and missing_hard:
            result.add(
                f"did not select enough of the hardest available screens; missing candidates: {missing_hard}"
            )

    verdict_match = VERDICT_SECTION_RE.search(report_text)
    verdict_text = verdict_match.group(1).strip() if verdict_match else ""
    if verdict_text not in VALID_VERDICTS:
        result.add(f"verdict '{verdict_text}' is not one of the three valid verdicts: {VALID_VERDICTS}")
    elif expected_verdict and verdict_text != expected_verdict:
        result.add(f"expected verdict '{expected_verdict}', found '{verdict_text}'")

    gaps_match = GAPS_SECTION_RE.search(report_text)
    if verdict_text == "Composes cleanly":
        if gaps_match and gaps_match.group(1).strip():
            result.add("verdict is 'Composes cleanly' but a non-empty '## Gaps' section is present")
    else:
        if not gaps_match or not gaps_match.group(1).strip():
            result.add(f"verdict '{verdict_text}' requires a non-empty '## Gaps' section")
        else:
            gap_lines = GAP_LINE_RE.findall(gaps_match.group(1))
            if len(gap_lines) < min_gap_count:
                result.add(f"expected at least {min_gap_count} classified gap(s), found {len(gap_lines)}")
            for gap_name, gap_class, detail in gap_lines:
                if gap_class == "Genuine" and "design-system amendment" not in detail and "issue #" not in detail:
                    result.add(f"genuine gap '{gap_name}' is not escalated as a design-system amendment")
                expected_class = expected_gap_classes.get(gap_name.strip())
                if expected_class and expected_class != gap_class:
                    result.add(f"gap '{gap_name}' expected classification '{expected_class}', found '{gap_class}'")

    return result


def check_skip_response(text: str, skip_signal_patterns: list[str] | None = None) -> ContractResult:
    result = ContractResult()
    if not text or not text.strip():
        result.add("skip response is empty")
        return result

    if "## Screens Selected" in text or "## Verdict" in text:
        result.add("response renders a full composition-check report for a case the skill should have skipped")

    lower = text.lower()
    patterns = skip_signal_patterns or []
    if patterns and not any(pattern.lower() in lower for pattern in patterns):
        result.add(f"skip response does not use any of the expected signal phrases: {patterns}")

    return result
