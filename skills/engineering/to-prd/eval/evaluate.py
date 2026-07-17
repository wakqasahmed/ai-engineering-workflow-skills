#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


CONTRACT_RULES = {
    "repository grounding": r"Inspect relevant code, the domain glossary, and applicable ADRs before drafting when they are available\.",
    "no redundant interview": r"Synthesize the current conversation; do not repeat a general requirements interview\.",
    "highest test seam": r"Reuse the highest existing test seam that proves external behavior\.",
    "single seam confirmation": r"Ask at most one focused confirmation only when the highest existing test seam is genuinely unresolved",
    "confirmation pause": r"Wait for that answer before drafting or publishing\.",
    "required sections": r"Problem, Goal and solution, Prioritized user stories, Success criteria, Non-goals, Constraints, Open product decisions, Implementation decisions, and Testing decisions",
    "conditional stories": r"Include prioritized user stories only when they clarify distinct actors, outcomes, or ordering",
    "no volatile paths": r"Exclude volatile file paths and code snippets\.",
    "prototype exception": r"Include a prototype artifact only when it records a decision more clearly than prose",
    "publish issue": r"Publish the spec to the detected project issue tracker\.",
    "readiness gate": r"Apply `ready-for-agent` only when no blocking product decisions remain",
    "product decisions stay blocking": r"Unresolved product decisions remain explicit blockers",
    "decomposition handoff": r"Hand the published spec to `decompose-to-issues`; do not turn the PRD into an issue breakdown\.",
}

CONTRACT_CONTRADICTIONS = {
    "repository grounding": "Draft before inspecting repository context.",
    "no redundant interview": "Repeat a general requirements interview before writing the spec.",
    "highest test seam": "Prefer a new low-level test seam over existing high-level seams.",
    "single seam confirmation": "Ask a focused confirmation for any unresolved implementation decision.",
    "confirmation pause": "Draft and publish before the focused confirmation is answered.",
    "required sections": "Omit implementation and testing decisions from the spec.",
    "conditional stories": "Always write a long and exhaustive list of user stories.",
    "no volatile paths": "Include specific file paths in implementation decisions.",
    "prototype exception": "Include complete prototype code whether or not it records a decision.",
    "publish issue": "Leave the spec only in the conversation.",
    "readiness gate": "Apply `ready-for-agent` while blocking product decisions remain.",
    "product decisions stay blocking": "Treat unresolved product decisions as non-blocking implementation details.",
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


def candidate_errors(context: dict, candidate: dict) -> list[str]:
    errors = []
    seam_is_resolved = context["test_seam"] is not None
    product_blockers = context["blocking_product_decisions"]
    can_publish = context["tracker_available"] and context["publishing_access"]

    if candidate["includes_volatile_paths"]:
        errors.append("spec includes volatile paths")

    if seam_is_resolved and candidate["questions"]:
        errors.append("interviews despite a settled test seam")
    if not seam_is_resolved:
        if len(candidate["questions"]) != 1:
            errors.append("unresolved test seam requires exactly one question")
        if candidate["drafted"] or candidate["published"]:
            errors.append("drafts or publishes before the seam confirmation")

    if product_blockers:
        if candidate["questions"]:
            errors.append("uses the seam confirmation for a product decision")
        if candidate["ready_for_agent"]:
            errors.append("claims readiness with unresolved product decisions")
        if candidate["blockers_reported"] != product_blockers:
            errors.append("does not preserve the product blockers")

    if candidate["drafted"] and not candidate["includes_required_sections"]:
        errors.append("draft omits required sections")

    if can_publish and seam_is_resolved and not candidate["published"]:
        errors.append("does not publish when the tracker is available")
    if not can_publish:
        if candidate["published"]:
            errors.append("claims publication without tracker access")
        if candidate["ready_for_agent"]:
            errors.append("claims readiness without publication")
        if not candidate["blockers_reported"]:
            errors.append("does not report the publishing blocker")

    should_be_ready = can_publish and seam_is_resolved and not product_blockers
    if candidate["ready_for_agent"] != should_be_ready:
        errors.append("readiness does not match the publishing gate")
    if candidate["handoff_to_decompose"] != should_be_ready:
        errors.append("decomposition handoff bypasses the readiness gate")

    return errors


def validate_scenarios(scenarios: list[dict]) -> None:
    for scenario in scenarios:
        for candidate in scenario["candidates"]:
            errors = candidate_errors(scenario["context"], candidate)
            actual_valid = not errors
            if actual_valid != candidate["expected_valid"]:
                detail = "; ".join(errors) or "candidate unexpectedly passed"
                raise AssertionError(f"{scenario['name']}/{candidate['name']}: {detail}")
            result = "accepted" if actual_valid else "rejected"
            print(f"PASS: {scenario['name']}/{candidate['name']} ({result})")


def main() -> None:
    scenarios = json.loads(Path(sys.argv[1]).read_text())
    skill_text = Path(sys.argv[2]).read_text()
    validate_skill_contract(skill_text)
    mutation_check(skill_text)
    print(f"PASS: to-prd contract ({len(CONTRACT_RULES) * 2} mutation checks)")
    validate_scenarios(scenarios)


if __name__ == "__main__":
    main()
