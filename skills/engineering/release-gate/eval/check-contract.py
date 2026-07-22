#!/usr/bin/env python3
"""Offline contract checks for the release-gate skill."""
import json
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
SKILL = EVAL_DIR.parent / "SKILL.md"
CASES = EVAL_DIR / "fixtures" / "held-out.json"
REQUIRED_SKILL_TERMS = (
    "Confirm the reviewed commit or artifact being released.",
    "Confirm environment and deployment mechanism.",
    "Run the smallest deployment validation available.",
    "Smoke-test the critical route or workflow.",
    "Record rollback path.",
    "Create a HITL issue if deployment needs missing human-held access.",
    "Do not deploy production from unreviewed PRs.",
)
REQUIRED_CASE_FIELDS = {"id", "split", "prompt", "response_rubric", "safety_rubric"}


def validate() -> list[str]:
    failures = []
    skill = SKILL.read_text()
    for term in REQUIRED_SKILL_TERMS:
        if term not in skill:
            failures.append(f"SKILL.md is missing required contract text: {term}")

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
            rubric = case[rubric_name]
            if not isinstance(rubric, dict) or not rubric.get("must_match") or not isinstance(rubric.get("must_not_match", []), list):
                failures.append(f"{case['id']} has an invalid {rubric_name}")
    if len(cases) < 10:
        failures.append("held-out manifest needs at least ten cases")
    return failures


if __name__ == "__main__":
    failures = validate()
    if failures:
        print("FAIL: deterministic release-gate contract checks")
        print("\n".join(f"- {failure}" for failure in failures))
        raise SystemExit(1)
    print("PASS: deterministic release-gate contract checks")
