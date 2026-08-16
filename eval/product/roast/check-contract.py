#!/usr/bin/env python3
"""Offline contract checks for the roast skill."""
import hashlib
import json
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
SKILL = EVAL_DIR.parent / "SKILL.md"
CASES = EVAL_DIR / "fixtures" / "held-out.json"
TUNING_CASES = EVAL_DIR / "fixtures" / "tuning.json"
REQUIRED_SKILL_TERMS = (
    "Spin up **all six agents in parallel in a single message**",
    "Once all six return, YOU act as the Judge — do not spawn a seventh agent.",
    "Do not average the six scores; they measure different dimensions",
    "## THE VERDICT: GO / RESHAPE / KILL",
    "The Judge must make an actual call. \"It depends\" is not a verdict.",
    "**1. The Contrarian (Red Team)**",
    "**2. The Expansionist (Bull)**",
    "**3. The Logician (First principles)**",
    "**4. The Researcher (Evidence)**",
    "**5. The Buyer (Voice of customer)**",
    "**6. The Futurist (Industry trends)**",
    "Contrarian X/10 · Expansionist X/10 · Logician X/10 · Researcher X/10 · Buyer X/10 · Futurist X/10",
)
REQUIRED_CASE_FIELDS = {"id", "split", "prompt", "expected_outcome"}


def prompt_digest(prompt: str) -> str:
    return hashlib.sha256(" ".join(prompt.lower().split()).encode()).hexdigest()


def validate_corpus(held_out_path: Path, tuning_path: Path) -> list[str]:
    held_out = json.loads(held_out_path.read_text())["cases"]
    tuning = json.loads(tuning_path.read_text())["cases"]
    held_out_ids = {case.get("id") for case in held_out}
    tuning_ids = {case.get("id") for case in tuning}
    failures = []
    if overlap := held_out_ids & tuning_ids:
        failures.append(f"held-out ids appear in tuning corpus: {sorted(overlap)}")
    held_out_prompts = {prompt_digest(case["prompt"]) for case in held_out if isinstance(case.get("prompt"), str)}
    if any(prompt_digest(case["prompt"]) in held_out_prompts for case in tuning if isinstance(case.get("prompt"), str)):
        failures.append("held-out prompt appears in tuning corpus")
    return failures


def validate() -> list[str]:
    failures = []
    skill = SKILL.read_text()
    for term in REQUIRED_SKILL_TERMS:
        if term not in skill:
            failures.append(f"SKILL.md is missing required contract text: {term}")

    cases = json.loads(CASES.read_text())["cases"]
    failures.extend(validate_corpus(CASES, TUNING_CASES))
    ids = set()
    should_use = should_not_use = 0
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
        if not isinstance(outcome, dict) or "engaged" not in outcome or outcome.get("safety") not in {"pass", "block"}:
            failures.append(f"{case['id']} has an invalid expected outcome")
            continue
        if outcome["engaged"] is True:
            should_use += 1
        elif outcome["engaged"] is False:
            should_not_use += 1
        else:
            failures.append(f"{case['id']} expected_outcome.engaged must be a boolean")
    if len(cases) < 10:
        failures.append("held-out manifest needs at least ten cases")
    if should_use < 5:
        failures.append(f"held-out manifest needs at least five should-use cases, found {should_use}")
    if should_not_use < 5:
        failures.append(f"held-out manifest needs at least five should-not-use cases, found {should_not_use}")
    return failures


if __name__ == "__main__":
    failures = validate()
    if failures:
        print("FAIL: deterministic roast contract checks")
        print("\n".join(f"- {failure}" for failure in failures))
        raise SystemExit(1)
    print("PASS: deterministic roast contract checks")
