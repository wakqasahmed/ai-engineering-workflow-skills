#!/usr/bin/env python3
"""Offline checks for non-negotiable decompose-to-issues instructions."""
import json
import re
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
SKILL = EVAL_DIR.parent / "SKILL.md"
CASES = EVAL_DIR / "fixtures" / "held-out.json"
CONTRACT_RULES = {
    "outcome first": r"Identify the user-visible or operational outcome\.",
    "vertical slices": r"Split by vertical slices that can be implemented, reviewed, and verified independently\.",
    "explicit dependencies": r"Mark dependencies explicitly\.",
    "fresh-agent scope": r"Keep each issue small enough for a fresh agent to complete in one focused pass when possible\.",
    "acceptance criteria": r"Acceptance criteria",
    "verification plan": r"Verification plan",
    "risk level": r"Risk level",
    "avoid horizontal slices": r"Avoid horizontal slices like \"build backend\" and \"build frontend\"",
    "standalone context": r"Do not create issues that require inherited conversation context to understand\.",
    "follow-up scope": r"Create follow-up issues for scope discovered during implementation\.",
}
REQUIRED_CASE_FIELDS = {"id", "split", "prompt", "expected_outcome"}


def validate() -> list[str]:
    failures = []
    skill = SKILL.read_text()
    for name, pattern in CONTRACT_RULES.items():
        if not re.search(pattern, skill):
            failures.append(f"SKILL.md is missing required contract text: {name}")

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
        if case["expected_outcome"] not in {"issue_plan", "direct_action"}:
            failures.append(f"{case['id']} has an invalid expected_outcome")
        if case["expected_outcome"] == "issue_plan" and (not isinstance(case.get("expected_scopes"), list) or len(case["expected_scopes"]) < 2 or not all(isinstance(scope, str) and scope for scope in case["expected_scopes"])):
            failures.append(f"{case['id']} needs at least two expected scopes")
        if case["expected_outcome"] == "direct_action" and (not isinstance(case.get("expected_terms"), list) or not case["expected_terms"] or not all(isinstance(term, str) and term for term in case["expected_terms"])):
            failures.append(f"{case['id']} needs expected direct-action terms")
    if len(cases) < 10:
        failures.append("held-out manifest needs at least ten cases")
    return failures


if __name__ == "__main__":
    failures = validate()
    if failures:
        print("FAIL: deterministic decompose-to-issues contract checks")
        print("\n".join(f"- {failure}" for failure in failures))
        raise SystemExit(1)
    print("PASS: deterministic decompose-to-issues contract checks")
