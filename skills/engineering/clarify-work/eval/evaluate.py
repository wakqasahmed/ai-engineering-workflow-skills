#!/usr/bin/env python3
import json
import sys
from pathlib import Path


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


def main() -> None:
    scenarios = json.loads(Path(sys.argv[1]).read_text())
    for scenario in scenarios:
        try:
            validate(scenario)
        except AssertionError as error:
            raise SystemExit(f"FAIL: {scenario['name']}: {error}") from error
        print(f"PASS: {scenario['name']} ({len(scenario['turns'])} turns)")


if __name__ == "__main__":
    main()
