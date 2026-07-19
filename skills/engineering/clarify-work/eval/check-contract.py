#!/usr/bin/env python3
"""Offline contract checks for the clarify-work skill."""
import json
import re
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
SKILL = EVAL_DIR.parent / "SKILL.md"
CASES = EVAL_DIR / "fixtures" / "held-out.json"
CONTRACT_RULES = {
    "initial estimate": r"Estimate the initial number of blocking questions from all available context before asking any\.",
    "zero-blocker fast path": r"If the estimate is zero, skip the interview and continue to the execution boundary\.",
    "one question per turn": r"Ask exactly one blocking question per user turn, then wait for the answer\.",
    "arbitrary-N progress": r"Render the bar with exactly `N` cells: `n` filled `■` cells followed by `N - n` empty `□` cells\.",
    "follow-up conditions": r"Treat an incomplete or ambiguous answer, or a newly discovered blocker, as a follow-up labeled `Follow-up k \(after Question n/N\) · \[bar\]`\.",
    "stable follow-up denominator": r"Keep the original `N`",
    "unresolved blocker does not advance": r"do not advance `n` or consume the next planned question until the current blocker is resolved\.",
    "stable follow-up position": r"Render the follow-up bar at position `n`, without changing `N`\.",
    "concise interview output": r"During the interview, include only the current question and context needed to answer it\.",
}
REQUIRED_CASE_FIELDS = {
    "id",
    "split",
    "prompt",
    "response_rubric",
    "safety_rubric",
}


def validate_skill_contract(skill_text: str) -> list[str]:
    return [name for name, pattern in CONTRACT_RULES.items() if not re.search(pattern, skill_text)]


def validate_manifest() -> list[str]:
    failures = []
    cases = json.loads(CASES.read_text())["cases"]
    ids = set()
    for case in cases:
        missing = REQUIRED_CASE_FIELDS - case.keys()
        if missing:
            failures.append(f"{case.get('id', '<unknown>')} is missing {sorted(missing)}")
            continue
        if case["id"] in ids:
            failures.append(f"duplicate held-out case id: {case['id']}")
        ids.add(case["id"])
        if case["split"] != "held_out":
            failures.append(f"{case['id']} is not held out")
        for rubric_name in ("response_rubric", "safety_rubric"):
            rubric = case.get(rubric_name)
            if not isinstance(rubric, dict) or not rubric.get("must_match") or not isinstance(rubric.get("must_not_match", []), list):
                failures.append(f"{case['id']} has an invalid {rubric_name}")
    if len(cases) < 10:
        failures.append("held-out manifest needs at least ten cases")
    return failures


if __name__ == "__main__":
    failures = [f"SKILL.md is missing required contract text: {name}" for name in validate_skill_contract(SKILL.read_text())]
    failures.extend(validate_manifest())
    if failures:
        print("FAIL: deterministic clarify-work contract checks")
        print("\n".join(f"- {failure}" for failure in failures))
        raise SystemExit(1)
    print("PASS: deterministic clarify-work contract checks")
