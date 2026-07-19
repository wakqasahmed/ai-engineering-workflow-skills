#!/usr/bin/env python3
"""Offline contract checks for the AI agent PR metadata evaluation."""
import json
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
SKILL = EVAL_DIR.parent / "SKILL.md"
CASES = EVAL_DIR / "fixtures" / "held-out.json"
REQUIRED_SKILL_TERMS = (
    "Never guess the model name.", "agent:<model+version>-<effort>-<role>",
    "never remove other agents' `agent:*` labels", "Co-Authored-By",
    "Review metadata:", "AI Agent update:",
)
REQUIRED_CASE_FIELDS = {"id", "split", "case_type", "prompt", "expected_skill_usage", "expected_outcome", "expected_safety_outcome"}

def validate() -> list[str]:
    failures = []
    skill = SKILL.read_text()
    for term in REQUIRED_SKILL_TERMS:
        if term not in skill:
            failures.append(f"SKILL.md is missing required contract text: {term}")
    cases = json.loads(CASES.read_text())["cases"]
    counts, types, ids = {"use": 0, "do_not_use": 0}, {"direct": 0, "safety": 0, "near_miss": 0}, set()
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
        if case["case_type"] not in types:
            failures.append(f"{case['id']} has invalid case type")
        else:
            types[case["case_type"]] += 1
        if not case["expected_outcome"] or not case["expected_safety_outcome"]:
            failures.append(f"{case['id']} lacks a machine-checkable outcome")
    if len(cases) < 10 or counts["use"] < 5 or types["direct"] < 5 or types["safety"] + types["near_miss"] < 5:
        failures.append("held-out manifest needs five direct use and five safety/near-miss cases")
    return failures

if __name__ == "__main__":
    failures = validate()
    if failures:
        print("FAIL: deterministic contract checks")
        print("\n".join(f"- {failure}" for failure in failures))
        raise SystemExit(1)
    print("PASS: deterministic contract checks")
