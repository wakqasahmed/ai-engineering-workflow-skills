#!/usr/bin/env python3
"""Offline contract checks for the write-prompt-guide skill."""
import hashlib
import importlib.util
import json
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
SKILL = EVAL_DIR.parent / "SKILL.md"
SOURCES = EVAL_DIR.parent / "SOURCES.md"
CASES = EVAL_DIR / "fixtures" / "held-out.json"
TUNING_CASES = EVAL_DIR / "fixtures" / "tuning.json"

REQUIRED_SKILL_TERMS = (
    "Quick start",
    "Giving useful context",
    "Structuring a complex or multi-phase request",
    "Good vs. less-effective prompt examples",
    "Known limitations to mention explicitly",
    "Where to go deeper",
    "at least two pairs",
    "Never describe a capability the target pack does not have",
    "Never present an unmerged fix as shipped",
    "gh issue list --repo <owner>/<repo> --state open",
    "ANTHROPIC-PROMPTING-01",
    "OPENAI-PROMPTING-01",
    "GOOGLE-PROMPTING-01",
    "BYTEPLUS-PROMPTING-01",
)

REQUIRED_SOURCE_URLS = (
    "https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices",
    "https://developers.openai.com/api/docs/guides/prompt-engineering",
    "https://ai.google.dev/gemini-api/docs/prompting-strategies",
    "https://docs.byteplus.com/en/docs/ModelArk/prompt-engineering",
)

REQUIRED_CASE_FIELDS = {"id", "split", "guide", "known_capabilities", "allowed_terms", "expected_outcome"}


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_guide", EVAL_DIR / "validate-guide.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def guide_digest(guide: str) -> str:
    return hashlib.sha256(" ".join(guide.lower().split()).encode()).hexdigest()


def validate_corpus(held_out: list[dict], tuning: list[dict]) -> list[str]:
    failures = []
    if overlap := {c.get("id") for c in held_out} & {c.get("id") for c in tuning}:
        failures.append(f"held-out ids appear in tuning corpus: {sorted(overlap)}")
    held_out_digests = {guide_digest(c["guide"]) for c in held_out if isinstance(c.get("guide"), str)}
    if any(guide_digest(c["guide"]) in held_out_digests for c in tuning if isinstance(c.get("guide"), str)):
        failures.append("held-out guide appears in tuning corpus")
    return failures


def validate() -> list[str]:
    skill_text = SKILL.read_text()
    failures = [f"SKILL.md is missing required contract text: {term}" for term in REQUIRED_SKILL_TERMS if term not in skill_text]

    sources_text = SOURCES.read_text()
    failures.extend(f"SOURCES.md is missing a cited source URL: {url}" for url in REQUIRED_SOURCE_URLS if url not in sources_text)

    validator = load_validator()
    held_out = json.loads(CASES.read_text())["cases"]
    tuning = json.loads(TUNING_CASES.read_text())["cases"]
    failures.extend(validate_corpus(held_out, tuning))

    ids = set()
    for case in held_out:
        missing = REQUIRED_CASE_FIELDS - case.keys()
        if missing:
            failures.append(f"{case.get('id', '<unknown>')} is missing {sorted(missing)}")
            continue
        if case["id"] in ids:
            failures.append(f"duplicate held-out case id: {case['id']}")
        ids.add(case["id"])
        if case["split"] != "held_out":
            failures.append(f"{case['id']} is not held out")

        expected = case["expected_outcome"]
        if expected.get("verdict") not in {"pass", "fail"}:
            failures.append(f"{case['id']} has an invalid expected verdict")
            continue

        actual = validator.validate(case["guide"], set(case["known_capabilities"]), set(case["allowed_terms"]))
        verdict = "fail" if actual else "pass"
        if verdict != expected["verdict"]:
            failures.append(f"{case['id']}: expected {expected['verdict']}, validator said {verdict} ({actual})")
            continue
        for kind in expected["failure_kinds"]:
            if kind not in actual:
                failures.append(f"{case['id']}: expected failure '{kind}' not reported (got {actual})")

    if len(held_out) < 10:
        failures.append("held-out manifest needs at least ten cases")
    verdicts = {c["expected_outcome"]["verdict"] for c in held_out if "expected_outcome" in c}
    if not verdicts >= {"pass", "fail"}:
        failures.append("held-out manifest must exercise both a passing and a failing guide")
    if not any("names capabilities absent" in kind for c in held_out for kind in c.get("expected_outcome", {}).get("failure_kinds", [])):
        failures.append("held-out manifest must include a fabricated-capability case")
    if not any("merge state" in kind for c in held_out for kind in c.get("expected_outcome", {}).get("failure_kinds", [])):
        failures.append("held-out manifest must include an unmerged-fix-claimed-as-shipped case")

    return failures


if __name__ == "__main__":
    problems = validate()
    if problems:
        print("FAIL: deterministic write-prompt-guide contract checks")
        print("\n".join(f"- {problem}" for problem in problems))
        raise SystemExit(1)
    print("PASS: deterministic write-prompt-guide contract checks")
