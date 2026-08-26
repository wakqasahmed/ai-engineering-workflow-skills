#!/usr/bin/env python3
"""Offline contract checks for the external PR viability skill."""
import hashlib
import json
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
SKILL = EVAL_DIR.parent / "SKILL.md"
CASES = EVAL_DIR / "fixtures" / "held-out.json"
TUNING_CASES = EVAL_DIR / "fixtures" / "tuning.json"
REQUIRED_SKILL_TERMS = (
    "gh pr list --repo <owner>/<repo> --state merged --limit 100 --json author,authorAssociation",
    "gh api orgs/<org>/members/<login>",
    "Zero distinct external authors, or fewer than 5",
    "Fewer than ~20 total merged PRs exist to sample",
    "5 to 15 distinct external authors",
    "16 or more distinct external authors",
    "Never disqualify a repo from a single closed PR alone",
    "Never fabricate the merge-count evidence",
)
REQUIRED_CASE_FIELDS = {"id", "split", "prompt", "expected_outcome"}
VALID_DECISIONS = {"proceed", "disqualify", "check_required", "proceed_low_confidence"}


def prompt_digest(prompt: str) -> str:
    return hashlib.sha256(" ".join(prompt.lower().split()).encode()).hexdigest()


def validate_corpus(held_out_path: Path, tuning_path: Path) -> list[str]:
    held_out = json.loads(held_out_path.read_text())["cases"]
    tuning = json.loads(tuning_path.read_text())["cases"]
    failures = []
    if overlap := {case.get("id") for case in held_out} & {case.get("id") for case in tuning}:
        failures.append(f"held-out ids appear in tuning corpus: {sorted(overlap)}")
    held_out_prompts = {prompt_digest(case["prompt"]) for case in held_out if isinstance(case.get("prompt"), str)}
    if any(prompt_digest(case["prompt"]) in held_out_prompts for case in tuning if isinstance(case.get("prompt"), str)):
        failures.append("held-out prompt appears in tuning corpus")
    return failures


def validate() -> list[str]:
    failures = [f"SKILL.md is missing required contract text: {term}" for term in REQUIRED_SKILL_TERMS if term not in SKILL.read_text()]
    cases = json.loads(CASES.read_text())["cases"]
    failures.extend(validate_corpus(CASES, TUNING_CASES))
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
        outcome = case["expected_outcome"]
        if not isinstance(outcome, dict) or outcome.get("decision") not in VALID_DECISIONS or outcome.get("safety") not in {"pass", "block"}:
            failures.append(f"{case['id']} has an invalid expected outcome")
    if len(cases) < 10:
        failures.append("held-out manifest needs at least ten cases")
    if not {case["expected_outcome"]["decision"] for case in cases if "expected_outcome" in case} >= {"proceed", "disqualify"}:
        failures.append("held-out manifest must exercise both proceed and disqualify outcomes")
    return failures


if __name__ == "__main__":
    failures = validate()
    if failures:
        print("FAIL: deterministic external PR viability contract checks")
        print("\n".join(f"- {failure}" for failure in failures))
        raise SystemExit(1)
    print("PASS: deterministic external PR viability contract checks")
