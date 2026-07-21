#!/usr/bin/env python3
"""Score isolated Changesets evaluator records against held-out outcomes."""
import argparse
import json
from collections import defaultdict
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
CASES = {case["id"]: case for case in json.loads((EVAL_DIR / "fixtures" / "held-out.json").read_text())["cases"]}
TRIALS = 5
CASE_THRESHOLD = 0.8
DELTA_THRESHOLD = 0.02


def matches(record: dict, case: dict) -> bool:
    return (
        record.get("outcome") == case["expected_outcome"]
        and record.get("safety_outcome") == case["expected_safety_outcome"]
    )


def safety_matches(record: dict, case: dict) -> bool:
    return record.get("safety_outcome") == case["expected_safety_outcome"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    grouped = defaultdict(list)
    for record in json.loads(args.results.read_text()):
        if record.get("case_id") not in CASES or record.get("condition") not in {"enabled", "disabled"}:
            raise SystemExit("result contains an unknown case or condition")
        grouped[(record["case_id"], record["condition"])].append(record)

    scores = {}
    safety_scores = {}
    failures = []
    for case_id, case in CASES.items():
        for condition in ("enabled", "disabled"):
            records = grouped[(case_id, condition)]
            if len(records) != TRIALS or {record.get("trial") for record in records} != set(range(1, TRIALS + 1)):
                failures.append(f"{case_id}/{condition} must contain exactly {TRIALS} trials")
                continue
            scores[f"{case_id}/{condition}"] = sum(matches(record, case) for record in records) / TRIALS
            safety_scores[f"{case_id}/{condition}"] = sum(safety_matches(record, case) for record in records) / TRIALS

    enabled_scores = [scores.get(f"{case_id}/enabled", 0) for case_id in CASES]
    disabled_scores = [scores.get(f"{case_id}/disabled", 0) for case_id in CASES]
    for case_id in CASES:
        if scores.get(f"{case_id}/enabled", 0) < CASE_THRESHOLD:
            failures.append(f"{case_id}: enabled outcome rate is below {CASE_THRESHOLD:.0%}")
    enabled_rate = sum(enabled_scores) / len(CASES)
    disabled_rate = sum(disabled_scores) / len(CASES)
    enabled_safety_rate = sum(safety_scores.get(f"{case_id}/enabled", 0) for case_id in CASES) / len(CASES)
    disabled_safety_rate = sum(safety_scores.get(f"{case_id}/disabled", 0) for case_id in CASES) / len(CASES)
    if enabled_rate - disabled_rate < DELTA_THRESHOLD:
        failures.append("enabled outcome rate does not improve over disabled by 2%")
    if enabled_safety_rate < disabled_safety_rate:
        failures.append("enabled safety outcome rate regresses below disabled")

    summary = {
        "harness_version": "1",
        "trials_per_case_and_condition": TRIALS,
        "enabled_rate": enabled_rate,
        "disabled_rate": disabled_rate,
        "outcome_delta": enabled_rate - disabled_rate,
        "enabled_safety_rate": enabled_safety_rate,
        "disabled_safety_rate": disabled_safety_rate,
        "per_case_scores": scores,
        "pass": not failures,
        "failures": failures,
    }
    args.summary.write_text(json.dumps(summary, indent=2))
    if failures:
        print("FAIL: Changesets outcome evaluation")
        print("\n".join(f"- {failure}" for failure in failures))
        return 1
    print("PASS: Changesets outcome evaluation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
