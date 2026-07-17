#!/usr/bin/env python3
import re
import sys
from pathlib import Path


CONTRACT_RULES = {
    "repository grounding": r"Inspect relevant code, the domain glossary, and applicable ADRs before drafting when they are available\.",
    "no redundant interview": r"Synthesize the current conversation; do not repeat a general requirements interview\.",
    "highest test seam": r"Reuse the highest existing test seam that proves external behavior\.",
    "single seam confirmation": r"Ask at most one focused confirmation only when the test seam or a blocking implementation decision cannot be inferred",
    "confirmation pause": r"Wait for that answer before drafting or publishing\.",
    "required sections": r"Problem, Goal and solution, Prioritized user stories, Success criteria, Non-goals, Constraints, Open product decisions, Implementation decisions, and Testing decisions",
    "conditional stories": r"Include prioritized user stories only when they clarify distinct actors, outcomes, or ordering",
    "no volatile paths": r"Exclude volatile file paths and code snippets\.",
    "prototype exception": r"Include a prototype artifact only when it records a decision more clearly than prose",
    "publish issue": r"Publish the spec to the detected project issue tracker\.",
    "readiness gate": r"Apply `ready-for-agent` only when no blocking product decisions remain",
    "decomposition handoff": r"Hand the published spec to `decompose-to-issues`; do not turn the PRD into an issue breakdown\.",
}

CONTRACT_CONTRADICTIONS = {
    "repository grounding": "Draft before inspecting repository context.",
    "no redundant interview": "Repeat a general requirements interview before writing the spec.",
    "highest test seam": "Prefer a new low-level test seam over existing high-level seams.",
    "single seam confirmation": "Ask several confirmation questions about test seams.",
    "confirmation pause": "Draft and publish before the focused confirmation is answered.",
    "required sections": "Omit implementation and testing decisions from the spec.",
    "conditional stories": "Always write a long and exhaustive list of user stories.",
    "no volatile paths": "Include specific file paths in implementation decisions.",
    "prototype exception": "Include complete prototype code whether or not it records a decision.",
    "publish issue": "Leave the spec only in the conversation.",
    "readiness gate": "Apply `ready-for-agent` while blocking product decisions remain.",
    "decomposition handoff": "Break the PRD into implementation issues in this skill.",
}


def validate_skill_contract(skill_text: str) -> None:
    missing = [name for name, pattern in CONTRACT_RULES.items() if not re.search(pattern, skill_text)]
    if missing:
        raise AssertionError(f"missing skill rules: {', '.join(missing)}")

    contradicted = [
        name for name, contradiction in CONTRACT_CONTRADICTIONS.items() if contradiction in skill_text
    ]
    if contradicted:
        raise AssertionError(f"contradicted skill rules: {', '.join(contradicted)}")


def mutation_check(skill_text: str) -> None:
    for name, pattern in CONTRACT_RULES.items():
        mutated, replacements = re.subn(pattern, "", skill_text, count=1)
        if replacements != 1:
            raise AssertionError(f"cannot mutate skill rule: {name}")
        try:
            validate_skill_contract(mutated)
        except AssertionError:
            continue
        raise AssertionError(f"removing skill rule did not fail validation: {name}")

    for name, contradiction in CONTRACT_CONTRADICTIONS.items():
        try:
            validate_skill_contract(f"{skill_text}\n{contradiction}")
        except AssertionError:
            continue
        raise AssertionError(f"contradicting skill rule did not fail validation: {name}")


def main() -> None:
    skill_text = Path(sys.argv[1]).read_text()
    validate_skill_contract(skill_text)
    mutation_check(skill_text)
    print(f"PASS: to-prd contract ({len(CONTRACT_RULES) * 2} mutation checks)")


if __name__ == "__main__":
    main()
