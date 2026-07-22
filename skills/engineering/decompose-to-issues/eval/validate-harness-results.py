#!/usr/bin/env python3
"""Score isolated decomposition responses against held-out observable outcomes."""
import argparse
import json
from collections import defaultdict
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
CASES = EVAL_DIR / "fixtures" / "held-out.json"
ENABLED_OUTCOME_THRESHOLD = 0.8
MINIMUM_ENABLED_OUTCOME_DELTA = 0.1


ISSUE_FIELDS = {"title", "scope", "acceptance_criteria", "verification", "dependencies", "non_goals"}


def non_empty_strings(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item.strip() for item in value)


def outcome_matches(response: str, case: dict) -> bool:
    try:
        artifact = json.loads(response)
    except json.JSONDecodeError:
        return False

    if case["expected_outcome"] == "direct_action":
        if set(artifact) != {"direct_action"} or not isinstance(artifact["direct_action"], dict):
            return False
        action = artifact["direct_action"]
        return set(action) == {"scope", "verification", "non_goals"} and isinstance(action["scope"], str) and action["scope"].strip() and all(term.lower() in action["scope"].lower() for term in case["expected_terms"]) and non_empty_strings(action["verification"]) and non_empty_strings(action["non_goals"])

    if set(artifact) != {"issues", "relationships"} or not isinstance(artifact["issues"], list) or len(artifact["issues"]) < 2 or not isinstance(artifact["relationships"], list):
        return False
    expected_scopes = case["expected_scopes"]
    covered_scopes = []
    for issue in artifact["issues"]:
        if not isinstance(issue, dict) or set(issue) != ISSUE_FIELDS:
            return False
        if not isinstance(issue["title"], str) or not issue["title"].strip() or not isinstance(issue["scope"], str) or not issue["scope"].strip():
            return False
        if not all(non_empty_strings(issue[field]) for field in ISSUE_FIELDS - {"title", "scope"}):
            return False
        covered_scopes.append(f"{issue['title']} {issue['scope']}".lower())
    if not all(any(term.lower() in scope for scope in covered_scopes) for term in expected_scopes):
        return False
    return any(
        isinstance(relationship, dict)
        and set(relationship) == {"from", "to", "type"}
        and isinstance(relationship["from"], int)
        and isinstance(relationship["to"], int)
        and 1 <= relationship["from"] <= len(artifact["issues"])
        and 1 <= relationship["to"] <= len(artifact["issues"])
        and relationship["from"] != relationship["to"]
        and relationship["type"] == "depends_on"
        for relationship in artifact["relationships"]
    )


def validate(records: list[dict], trials: int) -> tuple[list[str], list[str]]:
    cases = {case["id"]: case for case in json.loads(CASES.read_text())["cases"]}
    failures, reports, grouped, seen = [], [], defaultdict(list), set()
    totals = {condition: {"outcome": 0, "safety": 0, "trials": 0} for condition in ("enabled", "disabled")}
    for record in records:
        key = tuple(record.get(name) for name in ("case_id", "condition", "trial"))
        case_id, condition, trial = key
        if case_id not in cases or condition not in totals or not isinstance(trial, int) or not 1 <= trial <= trials:
            failures.append(f"invalid result identity: {key}")
        elif key in seen:
            failures.append(f"duplicate trial: {key}")
        elif set(record) != {"case_id", "condition", "trial", "model", "harness_version", "response"} or not record.get("model") or not record.get("harness_version") or not isinstance(record.get("response"), str):
            failures.append(f"invalid observable artifact: {key}")
        else:
            seen.add(key)
            grouped[(case_id, condition)].append(record)

    for case_id, case in cases.items():
        rates = {}
        for condition in ("enabled", "disabled"):
            results = grouped[(case_id, condition)]
            if len(results) != trials:
                failures.append(f"{case_id}/{condition} needs {trials} trials")
                continue
            outcomes = sum(outcome_matches(record["response"], case) for record in results)
            safeties = outcomes
            rates[condition] = outcomes / trials
            totals[condition]["outcome"] += outcomes
            totals[condition]["safety"] += safeties
            totals[condition]["trials"] += trials
            reports.append(f"{case_id}: {condition} outcome {rates[condition]:.0%} ({outcomes}/{trials})")
            if condition == "enabled" and rates[condition] < ENABLED_OUTCOME_THRESHOLD:
                failures.append(f"{case_id}/enabled is below the {ENABLED_OUTCOME_THRESHOLD:.0%} outcome threshold")
        if len(rates) == 2:
            reports.append(f"{case_id}: outcome delta {rates['enabled'] - rates['disabled']:+.0%}")

    if all(totals[condition]["trials"] for condition in totals):
        outcome_delta = totals["enabled"]["outcome"] / totals["enabled"]["trials"] - totals["disabled"]["outcome"] / totals["disabled"]["trials"]
        safety_delta = totals["enabled"]["safety"] / totals["enabled"]["trials"] - totals["disabled"]["safety"] / totals["disabled"]["trials"]
        reports.extend((f"aggregate outcome delta {outcome_delta:+.0%}", f"aggregate safety delta {safety_delta:+.0%}"))
        if outcome_delta < MINIMUM_ENABLED_OUTCOME_DELTA:
            failures.append(f"aggregate enabled outcome delta is below {MINIMUM_ENABLED_OUTCOME_DELTA:.0%}; retire or revise the skill")
        if safety_delta < 0:
            failures.append("enabled condition has a safety regression; retire or revise the skill")
    return failures, reports


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--trials", type=int, choices=range(3, 7), required=True)
    args = parser.parse_args()
    failures, reports = validate(json.loads(args.results.read_text()), args.trials)
    print("\n".join(reports))
    if failures:
        print("\n".join(f"FAIL: {failure}" for failure in failures))
        raise SystemExit(1)
    print("PASS: isolated decompose-to-issues harness meets outcome and safety thresholds")
