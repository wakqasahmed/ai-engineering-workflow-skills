#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


CONTRACT_RULES = {
    "initial estimate": r"Estimate the initial number of blocking questions from all available context before asking any\.",
    "zero-blocker fast path": r"If the estimate is zero, skip the interview and continue to the execution boundary\.",
    "one question per turn": r"Ask exactly one blocking question per user turn, then wait for the answer\.",
    "arbitrary-N progress": r"Render the bar with exactly `N` cells: `n` filled `■` cells followed by `N - n` empty `□` cells\.",
    "follow-up conditions": r"Treat an incomplete or ambiguous answer, or a newly discovered blocker, as a follow-up labeled `Follow-up k \(after Question n/N\) · \[bar\]`\.",
    "stable follow-up denominator": r"Keep the original `N`",
    "unresolved blocker does not advance": r"do not advance `n` or consume the next planned question until the current blocker is resolved\.",
    "stable follow-up position": r"Render the follow-up bar at position `n`, without changing `N`\.",
    "concise interview output": r"During the interview, include only the current question and context needed to answer it\.",
}

CONTRACT_CONTRADICTIONS = {
    "initial estimate": "Estimate the initial number of blocking questions after asking the first question.",
    "zero-blocker fast path": "If the estimate is zero, start the interview.",
    "one question per turn": "Ask multiple blocking questions per user turn.",
    "arbitrary-N progress": "Render the bar with exactly three cells.",
    "follow-up conditions": "Treat an incomplete answer as the next planned question.",
    "stable follow-up denominator": "Increase `N` for follow-up questions.",
    "unresolved blocker does not advance": "Advance `n` before the current blocker is resolved.",
    "stable follow-up position": "Advance `n` for follow-up questions.",
    "concise interview output": "During the interview, include all remaining questions.",
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


def bar(position: int, total: int) -> str:
    return "■" * position + "□" * (total - position)


def expected_turns(scenario: dict) -> list[dict]:
    questions = scenario["initial_questions"]
    total = len(questions)
    if scenario["initial_estimate"] != total:
        raise AssertionError("initial estimate must match the planned questions")
    if total == 0:
        return [{"output": "Execution boundary · quick", "position": 0}]

    follow_ups = {}
    for follow_up in scenario.get("follow_ups", []):
        follow_ups.setdefault(follow_up["after"], []).append(follow_up["question"])

    turns = []
    follow_up_number = 0
    for position, question in enumerate(questions, start=1):
        turns.append(
            {
                "output": f"Question {position}/{total} · [{bar(position, total)}]\n{question}",
                "position": position,
            }
        )
        for follow_up_question in follow_ups.get(position, []):
            follow_up_number += 1
            turns.append(
                {
                    "output": (
                        f"Follow-up {follow_up_number} (after Question {position}/{total}) "
                        f"· [{bar(position, total)}]\n{follow_up_question}"
                    ),
                    "position": position,
                }
            )

    track = "quick" if total == 1 else "standard"
    turns.append({"output": f"Execution boundary · {track}", "position": total})
    return turns


def validate(scenario: dict) -> None:
    actual = scenario["turns"]
    expected = expected_turns(scenario)
    if len(actual) != len(expected):
        raise AssertionError(f"expected {len(expected)} turns, got {len(actual)}")

    for index, (actual_turn, expected_turn) in enumerate(zip(actual, expected), start=1):
        if index == 1:
            if actual_turn["answer"] is not None:
                raise AssertionError("the first assistant turn must not consume an answer")
        elif not actual_turn["answer"]:
            raise AssertionError(f"turn {index} must follow one user answer")
        if actual_turn["output"] != expected_turn["output"]:
            raise AssertionError(f"turn {index} output mismatch")
        if actual_turn["position"] != expected_turn["position"]:
            raise AssertionError(f"turn {index} changed clarification position")
        if actual_turn["output"].startswith(("Question", "Follow-up")):
            if len(actual_turn["output"].splitlines()) != 2:
                raise AssertionError(f"turn {index} must contain exactly one question")
        answer = actual_turn["answer"]
        if isinstance(answer, dict) and not answer["resolved"]:
            if not actual_turn["output"].startswith("Follow-up"):
                raise AssertionError(f"turn {index} must label an unresolved answer as a follow-up")
            if actual_turn["position"] != actual[index - 2]["position"]:
                raise AssertionError(f"turn {index} advanced past an unresolved blocker")


def main() -> None:
    scenarios = json.loads(Path(sys.argv[1]).read_text())
    skill_text = Path(sys.argv[2]).read_text()
    validate_skill_contract(skill_text)
    mutation_check(skill_text)
    print(f"PASS: skill contract ({len(CONTRACT_RULES) * 2} mutation checks)")
    for scenario in scenarios:
        try:
            validate(scenario)
        except AssertionError as error:
            raise SystemExit(f"FAIL: {scenario['name']}: {error}") from error
        print(f"PASS: {scenario['name']} ({len(scenario['turns'])} turns)")


if __name__ == "__main__":
    main()
