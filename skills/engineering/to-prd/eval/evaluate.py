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
    "readiness gate": r"Apply `ready-for-agent` only after every blocker is resolved",
    "all blocker categories": r"Product, test-seam, implementation or architecture, publication or access, and other blockers all prevent readiness",
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
    "readiness gate": "Apply `ready-for-agent` while any blocker remains.",
    "all blocker categories": "Treat architecture and publishing blockers as non-blocking implementation details.",
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


BLOCKER_CATEGORIES = {
    "product",
    "test_seam",
    "implementation_architecture",
    "publication_access",
    "other",
}
REQUIRED_SECTIONS = [
    "Problem",
    "Goal and solution",
    "Prioritized user stories",
    "Success criteria",
    "Non-goals",
    "Constraints",
    "Open product decisions",
    "Implementation decisions",
    "Testing decisions",
]
VOLATILE_PATH = re.compile(
    r"(?:^|[\s`(])(?:/|\.?\.?/)?(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.[A-Za-z0-9]+"
)
REDUNDANT_INTERVIEW = re.compile(
    r"always\s+(?:begin\s+with\s+)?(?:another\s+)?(?:requirements\s+)?interview|"
    r"requirements\s+(?:interview|again)|walk\s+me\s+through\s+the\s+requirements",
    re.IGNORECASE,
)
READY_TERM = r"(?:ready-for-agent|implementation-ready|ready\s+for\s+(?:an?\s+)?agent)"
READY_CLAIM = re.compile(
    rf"\b{READY_TERM}\b|\b(?:marked|labelled|labeled|tagged)\b.{{0,30}}\bready\b|"
    r"\breadiness\s+label\s+(?:was\s+)?applied\b",
    re.IGNORECASE,
)
NEGATED_READY_CLAIM = re.compile(
    rf"\b(?:is|was|remains?)\s+(?:not|never)\s+(?:marked\s+or\s+labelled\s+)?(?:as\s+)?{READY_TERM}\b|"
    rf"\bwithout\s+(?:(?:the|a)\s+)?{READY_TERM}(?:\s+label)?\b|"
    r"\bnot\s+(?:marked|labelled|labeled)(?:\s+or\s+(?:marked|labelled|labeled))?\s+"
    r"(?:as\s+)?ready-for-agent\b|"
    r"\breadiness\s+label\s+(?:was\s+)?(?:withheld(?:\s+and\s+not\s+applied)?|not\s+applied)\b",
    re.IGNORECASE,
)
PUBLISHED_CLAIM = re.compile(
    r"(?:^|[.!]\s+|\n\n)(?:i\s+)?published(?:\s+successfully\b|\s+(?:the\s+)?(?:spec|issue)\b)|"
    r"\b(?:created|opened|posted)\s+(?:the\s+)?issue",
    re.IGNORECASE,
)
HANDOFF_CLAIM = re.compile(
    r"\bhand(?:ed|\s+off)\b.*\bdecompos|sent\s+it\s+to\s+decomposition",
    re.IGNORECASE | re.DOTALL,
)
STOP_WORDS = {"and", "are", "for", "must", "owner", "the", "to"}
CONTEXT_STOP_WORDS = STOP_WORDS | {
    "available",
    "covers",
    "existing",
    "externally",
    "github",
    "issue",
    "observable",
    "project",
    "publishing",
    "repository",
    "settled",
    "suite",
    "test",
    "tests",
    "with",
}


def blocker_is_reported(blocker: str, output: str) -> bool:
    words = [
        word
        for word in re.findall(r"[a-z0-9]+", blocker.lower())
        if len(word) > 3 and word not in STOP_WORDS
    ]
    required_matches = min(2, len(words))
    return required_matches > 0 and sum(word in output.lower() for word in words) >= required_matches


def claims_readiness(output: str) -> bool:
    positive_claims = NEGATED_READY_CLAIM.sub("", output)
    return bool(READY_CLAIM.search(positive_claims))


def section_contents(output: str) -> dict[str, str]:
    contents = {}
    headings = [
        (section, re.search(rf"^{re.escape(section)}$", output, re.MULTILINE))
        for section in REQUIRED_SECTIONS
    ]
    if any(match is None for _, match in headings):
        return contents
    for index, (section, heading) in enumerate(headings):
        end = headings[index + 1][1].start() if index + 1 < len(headings) else len(output)
        body = output[heading.end() : end].strip().split("\n\n", 1)[0].strip()
        if section == "Testing decisions" and PUBLISHED_CLAIM.search(body):
            body = ""
        if body:
            contents[section] = body
    return contents


def has_substantive_spec(output: str) -> bool:
    contents = section_contents(output)
    if set(contents) != set(REQUIRED_SECTIONS):
        return False
    placeholders = {"none", "none.", "n/a", "tbd", "unknown"}
    return all(contents[section].lower() not in placeholders for section in ("Implementation decisions", "Testing decisions"))


def is_grounded(repository_context: str, output: str) -> bool:
    context_terms = {
        word
        for word in re.findall(r"[a-z0-9]+", repository_context.lower())
        if len(word) > 3 and word not in CONTEXT_STOP_WORDS
    }
    required_matches = min(2, len(context_terms))
    return required_matches == 0 or sum(word in output.lower() for word in context_terms) >= required_matches


def candidate_errors(scenario_input: dict, output: str) -> list[str]:
    errors = []
    blockers = scenario_input["blockers"]
    all_blockers = [blocker for category in blockers.values() for blocker in category]
    seam_blockers = blockers["test_seam"]
    publication_blockers = blockers["publication_access"]
    questions = re.findall(r"[^?]*\?", output)
    question_count = len(questions)
    has_spec = has_substantive_spec(output)
    claims_ready = claims_readiness(output)
    claims_published = bool(PUBLISHED_CLAIM.search(output))
    claims_handoff = bool(HANDOFF_CLAIM.search(output))

    if VOLATILE_PATH.search(output):
        errors.append("volatile-path")

    if not seam_blockers and (question_count or REDUNDANT_INTERVIEW.search(output)):
        errors.append("redundant-interview")
    if seam_blockers:
        focused_question = question_count == 1 and all(
            blocker_is_reported(blocker, questions[0]) for blocker in seam_blockers
        )
        if not focused_question:
            errors.append("invalid-seam-confirmation")
        if has_spec or claims_published or claims_ready:
            errors.append("did-not-pause-for-seam")
    elif not has_spec:
        errors.append("missing-spec")
    elif not is_grounded(scenario_input["repository_context"], output):
        errors.append("ungrounded-spec")

    if any(not blocker_is_reported(blocker, output) for blocker in all_blockers):
        errors.append("unreported-blocker")

    if all_blockers and claims_ready:
        errors.append("ready-with-blockers")
    if not all_blockers and not claims_ready:
        errors.append("not-ready")

    if publication_blockers and claims_published:
        errors.append("publication-without-access")
    if not publication_blockers and not seam_blockers and not claims_published:
        errors.append("not-published")

    if all_blockers and claims_handoff:
        errors.append("handoff-with-blockers")
    if not all_blockers and not claims_handoff:
        errors.append("missing-handoff")

    return errors


def validate_capture(candidate: dict) -> None:
    capture = candidate["capture"]
    kind = capture["kind"]
    if kind == "authored-fixture":
        return
    if kind == "cold-agent-capture":
        required = {"model", "captured_at", "run_id"}
        if not required.issubset(capture):
            raise AssertionError("cold-agent capture requires model, captured_at, and run_id")
        if any(not isinstance(capture[field], str) or not capture[field] for field in required):
            raise AssertionError("cold-agent capture metadata must be non-empty text")
        return
    raise AssertionError(f"unknown capture kind: {kind}")


def validate_scenarios(fixture: dict) -> None:
    if fixture["schema_version"] != 2:
        raise AssertionError("unsupported fixture schema")
    required_cold_captures = {"well-specified-no-interview", "genuinely-unresolved-test-seam"}
    captured_scenarios = {
        scenario["name"]
        for scenario in fixture["scenarios"]
        if any(
            candidate["expected_valid"] and candidate["capture"]["kind"] == "cold-agent-capture"
            for candidate in scenario["candidates"]
        )
    }
    if not required_cold_captures.issubset(captured_scenarios):
        missing = required_cold_captures - captured_scenarios
        raise AssertionError(f"missing required cold-agent captures: {', '.join(sorted(missing))}")
    for scenario in fixture["scenarios"]:
        if not isinstance(scenario["prompt"], str) or not isinstance(scenario["input"], dict):
            raise AssertionError(f"{scenario['name']}: prompt/input do not match capture schema")
        if set(scenario["input"]["blockers"]) != BLOCKER_CATEGORIES:
            raise AssertionError(f"{scenario['name']}: blocker categories do not match schema")
        for candidate in scenario["candidates"]:
            if not isinstance(candidate["output"], str):
                raise AssertionError(f"{scenario['name']}/{candidate['name']}: output is not text")
            validate_capture(candidate)
            errors = candidate_errors(scenario["input"], candidate["output"])
            actual_valid = not errors
            expected_valid = candidate["expected_valid"]
            missing_errors = set(candidate["expected_errors"]) - set(errors)
            if actual_valid != expected_valid or missing_errors:
                detail = "; ".join(errors) or "candidate unexpectedly passed"
                if missing_errors:
                    detail += f"; missing expected errors: {', '.join(sorted(missing_errors))}"
                raise AssertionError(f"{scenario['name']}/{candidate['name']}: {detail}")
            result = "accepted" if actual_valid else "rejected"
            print(f"PASS: {scenario['name']}/{candidate['name']} ({result}: {', '.join(errors) or 'clean'})")


def main() -> None:
    scenarios = json.loads(Path(sys.argv[1]).read_text())
    skill_text = Path(sys.argv[2]).read_text()
    validate_skill_contract(skill_text)
    mutation_check(skill_text)
    print(f"PASS: to-prd contract ({len(CONTRACT_RULES) * 2} mutation checks)")
    validate_scenarios(scenarios)


if __name__ == "__main__":
    main()
