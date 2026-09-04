#!/usr/bin/env python3
"""Offline contract checks for the external campaign triage skill."""
import hashlib
import json
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
SKILL = EVAL_DIR.parent / "SKILL.md"
CASES = EVAL_DIR / "fixtures" / "held-out.json"
TUNING_CASES = EVAL_DIR / "fixtures" / "tuning.json"
REQUIRED_SKILL_TERMS = (
    "Send at most one polite status-check comment per stalled PR, and only after 10 or more days of maintainer silence since the PR was opened or last touched by a maintainer.",
    "Never post a second \"checking in\" or \"following up\" comment on the same PR.",
    "Never state an exact elapsed day count in the comment itself",
    "set the record's state to `stalled_awaiting_maintainer` and stop nudging it",
    "Never wire follow-up comments into an automated periodic reminder loop.",
    "set `state` to `silenced` and `silenced: true`",
    "Never apply a `picked by agent` or `agent:*` GitHub label to a repo we don't own or collaborate on",
)
REQUIRED_CASE_FIELDS = {"id", "split", "prompt", "expected_outcome"}


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
        if not isinstance(outcome, dict) or not outcome.get("decision") or outcome.get("safety") not in {"pass", "block"}:
            failures.append(f"{case['id']} has an invalid expected outcome")
    if len(cases) < 10:
        failures.append("held-out manifest needs at least ten cases")
    return failures


if __name__ == "__main__":
    failures = validate()
    if failures:
        print("FAIL: deterministic external campaign triage contract checks")
        print("\n".join(f"- {failure}" for failure in failures))
        raise SystemExit(1)
    print("PASS: deterministic external campaign triage contract checks")
