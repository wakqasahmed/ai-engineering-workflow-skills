#!/usr/bin/env python3
"""Offline contract checks for the Changesets release outcome evaluation."""
import json
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
SKILL = EVAL_DIR.parent / "SKILL.md"
CASES = EVAL_DIR / "fixtures" / "held-out.json"
REQUIRED_SKILL_TERMS = (
    "Do not require Changesets for a single deployed application",
    "patch",
    "minor",
    "major",
    "no-changeset",
    "changeset status",
    "Never put registry tokens",
    "every public version surface",
)
REQUIRED_CASE_FIELDS = {
    "id",
    "split",
    "prompt",
    "expected_skill_usage",
    "expected_outcome",
    "expected_safety_outcome",
}


def validate() -> list[str]:
    failures = []
    skill = SKILL.read_text()
    for term in REQUIRED_SKILL_TERMS:
        if term not in skill:
            failures.append(f"SKILL.md is missing required contract text: {term}")

    cases = json.loads(CASES.read_text())["cases"]
    counts = {"use": 0, "do_not_use": 0}
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
        if case["expected_skill_usage"] not in counts:
            failures.append(f"{case['id']} has invalid skill usage")
        else:
            counts[case["expected_skill_usage"]] += 1
        if not case["expected_outcome"] or not case["expected_safety_outcome"]:
            failures.append(f"{case['id']} lacks an outcome or safety label")
    if len(cases) < 10 or any(count < 5 for count in counts.values()):
        failures.append("held-out manifest needs at least five use and five do-not-use cases")
    return failures


if __name__ == "__main__":
    failures = validate()
    if failures:
        print("FAIL: deterministic contract checks")
        print("\n".join(f"- {failure}" for failure in failures))
        raise SystemExit(1)
    print("PASS: deterministic contract checks")
