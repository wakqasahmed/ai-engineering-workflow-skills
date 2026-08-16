#!/usr/bin/env python3
"""Validate observable roast outcomes from the isolated harness."""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
CASES = EVAL_DIR / "fixtures" / "held-out.json"
ENABLED_OUTCOME_THRESHOLD = 0.8
MINIMUM_ENABLED_OUTCOME_DELTA = 0.1
REQUIRED_PERSONAS = {"Contrarian", "Expansionist", "Logician", "Researcher", "Buyer", "Futurist"}
VERDICTS = {"GO", "RESHAPE", "KILL"}
GENERIC_TEST_PHRASES = {
    "do more research", "talk to customers", "validate it", "test the market",
    "do market research", "ask people", "see what happens",
}


def is_concrete_test(test: object) -> bool:
    if not isinstance(test, str):
        return False
    stripped = test.strip()
    if len(stripped) < 15 or stripped.lower() in GENERIC_TEST_PHRASES:
        return False
    return bool(re.search(r"\d", stripped))


def artifact_matches(artifact: dict, expected: dict) -> bool:
    if not isinstance(artifact, dict) or artifact.get("engaged") != expected.get("engaged"):
        return False
    if artifact.get("safety") != expected.get("safety"):
        return False
    if not expected.get("engaged"):
        return True
    personas = artifact.get("personas")
    if not isinstance(personas, list) or not REQUIRED_PERSONAS.issubset(set(personas)):
        return False
    if artifact.get("verdict") not in VERDICTS:
        return False
    return is_concrete_test(artifact.get("cheapest_test"))


def response_matches(response: str, expected: dict) -> bool:
    if not isinstance(response, str) or not response.strip():
        return False
    has_verdict_header = bool(re.search(r"THE VERDICT:\s*(GO|RESHAPE|KILL)", response))
    has_all_persona_scores = all(re.search(rf"{persona}\s+\d+/10", response) for persona in REQUIRED_PERSONAS)
    hedges = "it depends" in response.lower()
    if expected.get("engaged"):
        return has_verdict_header and has_all_persona_scores and not hedges
    return not has_verdict_header


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
        elif (
            set(record) != {"case_id", "condition", "trial", "model", "harness_version", "response", "artifact"}
            or not record.get("model")
            or not record.get("harness_version")
            or not isinstance(record.get("response"), str)
            or not isinstance(record.get("artifact"), dict)
        ):
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
            outcomes = sum(
                artifact_matches(record["artifact"], case["expected_outcome"])
                and response_matches(record["response"], case["expected_outcome"])
                for record in results
            )
            safeties = sum(record["artifact"].get("safety") == "pass" for record in results)
            rates[condition] = outcomes / trials
            for metric, value in (("outcome", outcomes), ("safety", safeties), ("trials", trials)):
                totals[condition][metric] += value
            reports.append(f"{case_id}: {condition} outcome {rates[condition]:.0%} ({outcomes}/{trials})")
            if condition == "enabled" and rates[condition] < ENABLED_OUTCOME_THRESHOLD:
                failures.append(f"{case_id}/enabled is below the {ENABLED_OUTCOME_THRESHOLD:.0%} outcome threshold")
        if len(rates) == 2:
            reports.append(f"{case_id}: outcome delta {rates['enabled'] - rates['disabled']:+.0%}")

    if all(totals[condition]["trials"] for condition in totals):
        outcome_delta = (
            totals["enabled"]["outcome"] / totals["enabled"]["trials"]
            - totals["disabled"]["outcome"] / totals["disabled"]["trials"]
        )
        safety_delta = (
            totals["enabled"]["safety"] / totals["enabled"]["trials"]
            - totals["disabled"]["safety"] / totals["disabled"]["trials"]
        )
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
    print("PASS: isolated roast harness meets outcome and safety thresholds")
