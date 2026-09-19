#!/usr/bin/env python3
"""Offline contract checks for the external PR style skill."""
import hashlib
import json
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
SKILL = EVAL_DIR.parent / "SKILL.md"
if not SKILL.is_file():
    SKILL = EVAL_DIR.parents[2] / "skills" / "engineering" / "external-pr-style" / "SKILL.md"
CASES = EVAL_DIR / "fixtures" / "held-out.json"
TUNING_CASES = EVAL_DIR / "fixtures" / "tuning.json"
REQUIRED_SKILL_TERMS = (
    "1-2 concise sentences on symptom and fix",
    "one compact paragraph (3-5 sentences)",
    "two focused paragraphs: what changed and why, then what was verified",
    "~40 words",
    "~90 words",
    "~220 words",
    "match the reply's length to what the maintainer actually asked",
    "Only go longer when the maintainer explicitly asks for more",
    "Don't hedge excessively, enumerate edge cases nobody asked about, or offer unrequested follow-up work",
    "Before posting, name the diff's size tier from the table above",
)
REQUIRED_CASE_FIELDS = {"id", "split", "prompt", "expected_outcome"}
VALID_TIERS = {"small", "medium", "large", "reply", "reply_detailed"}


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
    skill_text = SKILL.read_text()
    failures = [f"SKILL.md is missing required contract text: {term}" for term in REQUIRED_SKILL_TERMS if term not in skill_text]
    cases = json.loads(CASES.read_text())["cases"]
    failures.extend(validate_corpus(CASES, TUNING_CASES))
    ids, tiers = set(), set()
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
        if (not isinstance(outcome, dict) or outcome.get("tier") not in VALID_TIERS
                or type(outcome.get("max_words")) is not int or outcome["max_words"] <= 0
                or outcome.get("safety") != "pass"):
            failures.append(f"{case['id']} has an invalid expected outcome")
        else:
            tiers.add(outcome["tier"])
    if len(cases) < 10:
        failures.append("held-out manifest needs at least ten cases")
    if not tiers >= {"small", "medium", "large", "reply"}:
        failures.append("held-out manifest must exercise small, medium, large, and reply tiers")
    return failures


if __name__ == "__main__":
    failures = validate()
    if failures:
        print("FAIL: deterministic external PR style contract checks")
        print("\n".join(f"- {failure}" for failure in failures))
        raise SystemExit(1)
    print("PASS: deterministic external PR style contract checks")
