#!/usr/bin/env python3
import json
import sys
from pathlib import Path


REQUIRED_SETUP_TERMS = (
    "GitHub remotes",
    "local tracker files",
    "target branch",
    "Labels",
    "docs/` layout",
    "AGENTS.md",
    "test commands",
    "Ask for approval before writing",
    "Never overwrite",
)


def route_for(request: str) -> str:
    text = request.casefold()
    waiting_for_access = any(term in text for term in ("missing", "waiting", "needs")) and any(
        term in text for term in ("permission", "approval")
    )
    if any(term in text for term in ("credential", "dns", "billing", "human")) or waiting_for_access:
        return "human-held-blocker"
    if any(term in text for term in ("release", "reviewed build", "production")):
        return "release"
    if any(term in text for term in ("500", "error", "broken", "regression")):
        return "bug"
    if "claimed" in text and "non-trivial" in text and ("github" in text or "issue" in text):
        return "claimed-github-issue"
    if any(term in text for term in ("vague", "broad", "marketplace", "independent slices", "unsettled")):
        return "idea-to-staging"
    return "small-feature"


def route_text(skill_text: str, route: str) -> str:
    sections = {
        "idea-to-staging": ("#### Vague or multi-issue request", "\n#### "),
        "small-feature": ("#### Concrete single behavior change", "\n#### "),
        "claimed-github-issue": ("#### Claimed non-trivial GitHub issue", "\n### "),
        "bug": ("### Bug or regression", "\n### "),
        "release": ("### Release", "\n### "),
        "human-held-blocker": ("### Human-held blocker", "\n### "),
    }
    heading, separator = sections[route]
    start = skill_text.find(heading)
    if start == -1:
        raise AssertionError(f"route heading not found: {heading}")
    remainder = skill_text[start:]
    next_heading = remainder.find(separator, 1)
    return remainder if next_heading == -1 else remainder[:next_heading]


def validate(skill_text: str, scenarios: list[dict]) -> None:
    missing = [term for term in REQUIRED_SETUP_TERMS if term not in skill_text]
    if missing:
        raise AssertionError("missing setup safeguards: " + ", ".join(missing))
    for scenario in scenarios:
        actual_route = route_for(scenario["request"])
        if actual_route != scenario["route"]:
            raise AssertionError(
                f"{scenario['name']} routed to {actual_route}, expected {scenario['route']}"
            )
        section = route_text(skill_text, scenario["route"])
        missing_steps = [step for step in scenario["sequence"] if step not in section]
        if missing_steps:
            raise AssertionError(f"{scenario['name']} missing: {', '.join(missing_steps)}")
        unexpected_steps = [step for step in scenario.get("excluded_steps", []) if step in section]
        if unexpected_steps:
            raise AssertionError(f"{scenario['name']} is not minimal: {', '.join(unexpected_steps)}")
        if "Transition rationale:" not in section or scenario["rationale"] not in section:
            raise AssertionError(f"{scenario['name']} has no route-specific transition rationale")


def main() -> None:
    scenarios = json.loads(Path(sys.argv[1]).read_text())
    skill_text = Path(sys.argv[2]).read_text()
    validate(skill_text, scenarios)
    for scenario in scenarios:
        print(f"PASS: {scenario['name']}")


if __name__ == "__main__":
    main()
