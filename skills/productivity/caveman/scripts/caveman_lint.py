#!/usr/bin/env python3
"""caveman_lint.py — Lint a response for caveman-mode compliance.

Stdlib-only. Detects banned vocabulary in a response that's supposed to be in
caveman mode. Returns specific findings + verdict.

Banned categories per Matt Pocock's caveman rules:
  - Pleasantries (sure, certainly, of course, happy to)
  - Filler (just, really, basically, actually, simply)
  - Hedging (might, maybe, perhaps, likely)
  - Metatalk (as you can see, worth noting)
  - Verbose phrases ("the implementation of a solution for")

Whitelist (NOT banned even in caveman mode):
  - Words inside code blocks
  - Words inside inline code
  - Words inside quoted strings
  - Caveman exception zones (security warnings, destructive op confirmations)

Usage:
    python caveman_lint.py                          # uses embedded samples
    python caveman_lint.py "response text"
    python caveman_lint.py --file path/to/response.txt
    python caveman_lint.py "text" --output json
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List

from caveman_rules import (
    FILLER_WORDS,
    HEDGING_WORDS,
    METATALK_PHRASES,
    PLEASANTRY_PHRASES,
    SINGLE_QUOTED_LITERAL_PATTERN,
)

BANNED_PHRASES = {
    "pleasantry": PLEASANTRY_PHRASES,
    "filler": FILLER_WORDS,
    "hedging": HEDGING_WORDS,
    "metatalk": METATALK_PHRASES,
    "verbose": [
        "implement a solution for", "the implementation of",
        "in order to", "for the purpose of", "with respect to",
        "due to the fact that",
    ],
}

EXCEPTION_MARKERS = [
    re.compile(r"\*\*warning:\*\*", re.IGNORECASE),
    re.compile(r"\bdestructive\b", re.IGNORECASE),
    re.compile(r"\birreversible\b", re.IGNORECASE),
    re.compile(r"\bcannot be undone\b", re.IGNORECASE),
]


SAMPLE_BAD = (
    "Sure! I'd be happy to help. The issue is actually quite simple — basically, "
    "you just need to update the configuration. It's worth mentioning that this might "
    "cause a slight performance hit, but probably not noticeable."
)
SAMPLE_GOOD = "Bug in auth middleware. Token expiry check use `<` not `<=`. Fix: change to `<=`."


def _protect_literals(text: str) -> str:
    """Mask code and quoted strings so banned-word matching skips them."""
    text = re.sub(r"```.*?```", lambda match: "\x00" * len(match.group(0)), text, flags=re.DOTALL)
    text = re.sub(r"`[^`]+`", lambda match: "\x00" * len(match.group(0)), text)
    text = re.sub(
        r'(?<!\w)"(?:\\.|[^"\\])*"',
        lambda match: "\x00" * len(match.group(0)),
        text,
    )
    return re.sub(
        SINGLE_QUOTED_LITERAL_PATTERN,
        lambda match: "\x00" * len(match.group(0)),
        text,
    )


def _has_exception_context(text: str) -> bool:
    return any(pattern.search(text) for pattern in EXCEPTION_MARKERS)


def _count_phrase(phrase: str, masked: str) -> int:
    pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"
    return len(re.findall(pattern, masked, re.IGNORECASE))


def _violation_record(category: str, phrase: str, count: int) -> Dict[str, Any]:
    return {"category": category, "phrase": phrase, "count": count}


def _find_violations_in_masked(masked: str) -> List[Dict[str, Any]]:
    violations: List[Dict[str, Any]] = []
    for category, phrases in BANNED_PHRASES.items():
        for phrase in phrases:
            count = _count_phrase(phrase, masked)
            if count > 0:
                violations.append(_violation_record(category, phrase, count))
    return violations


def find_violations(text: str) -> List[Dict[str, Any]]:
    """Find banned phrases. Returns list of {category, phrase, count}."""
    return _find_violations_in_masked(_protect_literals(text))


def analyze(text: str) -> Dict[str, Any]:
    masked = _protect_literals(text)
    violations = _find_violations_in_masked(masked)
    total_violations = sum(violation["count"] for violation in violations)
    has_exception = _has_exception_context(masked)
    softened_violations = 0

    for paragraph in re.split(r"\n[^\S\n]*\n+", masked):
        if _has_exception_context(paragraph):
            softened_violations += sum(
                violation["count"]
                for violation in _find_violations_in_masked(paragraph)
            )

    if total_violations == 0:
        verdict = "CLEAN"
    elif softened_violations == total_violations:
        verdict = "WARN"
    else:
        verdict = "FAIL"

    return {
        "char_count": len(text),
        "word_count": len(text.split()),
        "violation_categories": sorted(set(violation["category"] for violation in violations)),
        "total_violations": total_violations,
        "has_exception_context": has_exception,
        "violations": violations,
        "verdict": verdict,
    }


def render_text(text: str, result: Dict[str, Any]) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append("CAVEMAN LINT")
    lines.append("=" * 72)
    lines.append("")
    preview = text[:200] + ("..." if len(text) > 200 else "")
    lines.append(f"Text ({result['char_count']} chars, {result['word_count']} words):")
    lines.append(f"  {preview}")
    lines.append("")
    lines.append("-" * 72)
    lines.append(f"Violations: {result['total_violations']}")
    lines.append(f"Categories hit: {result['violation_categories']}")
    if result["has_exception_context"]:
        lines.append("Exception context detected (warning/destructive zone — some prose allowed)")
    lines.append("")
    if result["violations"]:
        for violation in result["violations"]:
            lines.append(
                f"  [{violation['category']:11s}] x{violation['count']:2d}  "
                f"'{violation['phrase']}'"
            )
    else:
        lines.append("  No banned phrases found.")
    lines.append("")
    lines.append("-" * 72)
    lines.append(f"Verdict: {result['verdict']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lint a response for caveman-mode compliance.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("text", nargs="?", help="Input text (uses embedded sample if omitted)")
    parser.add_argument("--file", help="Read input from file")
    parser.add_argument("--output", choices=("text", "json"), default="text", help="Output format")
    args = parser.parse_args()

    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as file:
                text = file.read()
        except (OSError, UnicodeDecodeError) as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
    elif args.text:
        text = args.text
    else:
        text = SAMPLE_BAD

    result = analyze(text)
    if args.output == "json":
        print(json.dumps({"text": text, **result}, indent=2))
    else:
        print(render_text(text, result))
    return 0 if result["verdict"] in {"CLEAN", "WARN"} else 1


if __name__ == "__main__":
    sys.exit(main())
