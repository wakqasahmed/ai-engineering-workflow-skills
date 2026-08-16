#!/usr/bin/env python3
"""Offline contract checks for the Filament conventions skill."""
import json
import re
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
SKILL = EVAL_DIR.parent / "SKILL.md"
HELD_OUT = EVAL_DIR / "fixtures" / "held-out.json"
TUNING = EVAL_DIR / "fixtures" / "tuning.json"
CONTRACT_RULES = {
    "version detection": r"Match the project's installed major version\. Never mix v3 and v4 snippets\.",
    "v4 schema": r"v4 unifies forms and infolists under `Filament\\Schemas\\Schema`",
    "v3 forms": r"v3 uses `Filament\\Forms\\Form` and `Filament\\Infolists\\Infolist`",
    "relation managers": r"Use relation managers for related data, not custom inline tables\.",
    "action classes": r"Implement custom actions as action classes, not inline closures\.",
    "tenant scope": r"Apply tenant constraints at the query level, not scattered in resources\.",
}
REQUIRED_FIELDS = {"id", "split", "prompt", "expected_outcome"}
OUTCOME_FIELDS = {"decision", "filament_major", "implementation", "relation_management", "action_style", "tenant_scope", "safety"}


def validate_corpus(held_out_path: Path = HELD_OUT, tuning_path: Path = TUNING) -> list[str]:
    failures, prompts, ids = [], set(), set()
    cases = json.loads(held_out_path.read_text())["cases"]
    for case in cases:
        missing = REQUIRED_FIELDS - case.keys()
        if missing:
            failures.append(f"{case.get('id', '<unknown>')} is missing {sorted(missing)}")
            continue
        if case["id"] in ids:
            failures.append(f"duplicate held-out case id: {case['id']}")
        ids.add(case["id"])
        prompts.add(case["prompt"])
        if case["split"] != "held_out":
            failures.append(f"{case['id']} is not held out")
        if set(case["expected_outcome"]) != OUTCOME_FIELDS:
            failures.append(f"{case['id']} has an invalid expected outcome")
    if len(cases) < 10:
        failures.append("held-out manifest needs at least ten cases")
    if sum(case["expected_outcome"]["decision"] == "filament_change" for case in cases) < 5:
        failures.append("held-out manifest needs at least five Filament cases")
    if sum(case["expected_outcome"]["decision"] == "not_applicable" for case in cases) < 5:
        failures.append("held-out manifest needs at least five near-miss cases")
    tuning_prompts = {case["prompt"] for case in json.loads(tuning_path.read_text())["cases"]}
    if prompts & tuning_prompts:
        failures.append("held-out prompt appears in tuning corpus")
    return failures


if __name__ == "__main__":
    text = SKILL.read_text()
    failures = [f"SKILL.md is missing required contract text: {name}" for name, pattern in CONTRACT_RULES.items() if not re.search(pattern, text)]
    failures.extend(validate_corpus())
    if failures:
        print("FAIL: deterministic Filament contract checks")
        print("\n".join(f"- {failure}" for failure in failures))
        raise SystemExit(1)
    print("PASS: deterministic Filament contract checks")
