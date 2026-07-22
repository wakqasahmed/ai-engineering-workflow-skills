#!/usr/bin/env python3
"""Offline contract checks for the review-gate skill."""
import json
import re
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
SKILL = EVAL_DIR.parent / "SKILL.md"
CASES = EVAL_DIR / "fixtures" / "held-out.json"
CONTRACT_RULES = {
    "issue and acceptance criteria": r"Confirm linked issue and acceptance criteria\.",
    "verification evidence": r"Confirm verification commands and results\.",
    "automation findings first": r"Read Alibaba Code Review's findings and the GitHub CI/check results on the PR before starting the independent review",
    "semantic scope": r"requirements compliance, correctness, regressions, security/authorization, contract/integration risk, and acceptance-test adequacy",
    "do not duplicate mechanical checks": r"Do not repeat resolved lint, formatting, conventional-style, or straightforward static-analysis findings",
    "explicit review record": r"Post concrete findings or explicitly state no blocking issues\.",
    "ci hard gate": r"CI remains a hard merge gate",
    "review record requirement": r"Do not merge non-trivial work without a review record\.",
}
REQUIRED_CASE_FIELDS = {"id", "split", "kind", "prompt", "artifacts", "expected", "safety"}


def validate_skill_contract(skill_text: str) -> list[str]:
    return [name for name, pattern in CONTRACT_RULES.items() if not re.search(pattern, skill_text)]


def validate_manifest() -> list[str]:
    failures, ids, kinds = [], set(), {"should_use": 0, "near_miss": 0}
    cases = json.loads(CASES.read_text())["cases"]
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
        if case["kind"] not in kinds:
            failures.append(f"{case['id']} has an invalid kind")
        else:
            kinds[case["kind"]] += 1
        if not isinstance(case.get("artifacts"), dict) or not isinstance(case.get("expected"), dict):
            failures.append(f"{case['id']} needs machine-checkable artifacts and expected outcome")
        if case["kind"] == "should_use" and not isinstance(case.get("expected", {}).get("finding"), dict):
            failures.append(f"{case['id']} needs an expected evidence-backed finding")
        if case["kind"] == "near_miss" and case.get("expected", {}).get("no_findings") is not True:
            failures.append(f"{case['id']} needs explicit no-finding behavior")
        safety = case.get("safety")
        if not isinstance(safety, dict) or not isinstance(safety.get("forbidden_actions"), list) or not isinstance(safety.get("forbidden_categories"), list):
            failures.append(f"{case['id']} has invalid independent safety rules")
    if len(cases) < 10:
        failures.append("held-out manifest needs at least ten cases")
    for kind, count in kinds.items():
        if count < 5:
            failures.append(f"held-out manifest needs at least five {kind} cases")
    return failures


if __name__ == "__main__":
    failures = [f"SKILL.md is missing required contract text: {name}" for name in validate_skill_contract(SKILL.read_text())]
    failures.extend(validate_manifest())
    if failures:
        print("FAIL: deterministic review-gate contract checks")
        print("\n".join(f"- {failure}" for failure in failures))
        raise SystemExit(1)
    print("PASS: deterministic review-gate contract checks")
