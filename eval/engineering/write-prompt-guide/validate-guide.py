#!/usr/bin/env python3
"""Structural validator for a generated PROMPT_GUIDE.md.

Given a guide's Markdown and the capability vocabulary of the pack it documents,
report every structural or fabrication failure. Used by check-contract.py over
held-out fixtures, and importable for validating a real generated guide.
"""
import re


REQUIRED_SECTIONS = (
    ("quick_start", re.compile(r"^#{2,3}\s.*quick start", re.I | re.M)),
    ("context", re.compile(r"^#{2,3}\s.*(useful context|giving .*context|what to (supply|include))", re.I | re.M)),
    ("structuring", re.compile(r"^#{2,3}\s.*structur\w*\s+(a\s+)?(complex|multi)", re.I | re.M)),
    ("prompt_pairs", re.compile(r"^#{2,3}\s.*(good vs\.? less[- ]effective|less[- ]effective)", re.I | re.M)),
    ("limitations", re.compile(r"^#{2,3}\s.*(known limitations|limitations to mention)", re.I | re.M)),
    ("deeper", re.compile(r"^#{2,3}\s.*(go deeper|where to go|further reading)", re.I | re.M)),
)

LESS_EFFECTIVE = re.compile(r"less[- ]effective", re.I)
MORE_EFFECTIVE = re.compile(r"more[- ]effective", re.I)
ISSUE_REF = re.compile(r"(#\d+|/(issues|pull)/\d+)")
UNMERGED_HEDGE = re.compile(r"\b(open|unmerged|not (yet )?merged|pending|awaiting (review|merge))\b", re.I)
CAPABILITY_CLAIM = re.compile(r"`([a-z0-9][a-z0-9-]{2,})`")


def find_fabricated_capabilities(guide: str, known: set[str], allowed: set[str]) -> list[str]:
    """Backtick-quoted hyphenated identifiers that name neither a real skill nor an allow-listed term."""
    claimed = {m.group(1) for m in CAPABILITY_CLAIM.finditer(guide)}
    return sorted(c for c in claimed if "-" in c and c not in known and c not in allowed)


def validate(guide: str, known_capabilities: set[str], allowed_terms: set[str]) -> list[str]:
    failures = []

    for name, pattern in REQUIRED_SECTIONS:
        if not pattern.search(guide):
            failures.append(f"missing required section: {name}")

    pairs = min(len(LESS_EFFECTIVE.findall(guide)), len(MORE_EFFECTIVE.findall(guide)))
    if pairs < 2:
        failures.append(f"needs at least two less-effective/more-effective prompt pairs, found {pairs}")

    if "```" not in guide:
        failures.append("no fenced code block: prompts must be copy-pasteable")

    limitations = _section_body(guide, REQUIRED_SECTIONS[4][1], guide)
    if limitations is not None:
        if not ISSUE_REF.search(limitations):
            failures.append("limitations section cites no issue or PR reference")
        if re.search(r"\bfixed\b", limitations, re.I) and not UNMERGED_HEDGE.search(limitations):
            failures.append("limitations section claims a fix without stating its merge state")

    fabricated = find_fabricated_capabilities(guide, known_capabilities, allowed_terms)
    if fabricated:
        failures.append(f"names capabilities absent from the target pack: {fabricated}")

    return failures


def _section_body(guide: str, heading: re.Pattern, _default: str) -> str | None:
    match = heading.search(guide)
    if not match:
        return None
    rest = guide[match.end():]
    following = re.search(r"^#{2,3}\s", rest, re.M)
    return rest[: following.start()] if following else rest


if __name__ == "__main__":
    import sys

    text = open(sys.argv[1]).read()
    problems = validate(text, set(sys.argv[2:]), set())
    if problems:
        print("\n".join(f"- {p}" for p in problems))
        raise SystemExit(1)
    print("PASS: guide structure")
