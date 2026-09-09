#!/usr/bin/env python3
"""caveman_compressor.py — Apply Matt Pocock's caveman compression rules to text.

Stdlib-only. Deterministic regex-based compression matching the rules in
Matt Pocock's caveman skill SKILL.md:

  1. Drop articles (a/an/the)
  2. Drop filler (just/really/basically/actual/actually/simply)
  3. Drop pleasantries (sure/certainly/of course/happy to)
  4. Drop hedging (might/maybe/perhaps/likely/possibly)
  5. Abbreviate common technical terms (database -> DB, configuration -> config, etc.)
  6. Strip conjunctions where safe (and/but at sentence start)
  7. Use arrows for unambiguous causality phrases such as "leads to" (-> )
  8. Strip "as you can see / it should be noted / it's worth mentioning"

PRESERVES:
- Security and irreversible-action warnings unchanged
- Code blocks (```...```) unchanged
- Inline code (`...`) unchanged
- Technical terms named verbatim
- Quoted strings unchanged

NO LLM CALLS. Stdlib only.

Usage:
    python caveman_compressor.py                          # uses embedded sample
    python caveman_compressor.py "your text here"
    python caveman_compressor.py --file path/to/input.txt
    python caveman_compressor.py "text" --output json
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Tuple

from caveman_rules import (
    FILLER_WORDS,
    HEDGING_WORDS,
    METATALK_PHRASES,
    PLEASANTRY_PHRASES,
    SINGLE_QUOTED_LITERAL_PATTERN,
)

ABBREVIATIONS = [
    (r"\bdatabase\b", "DB"),
    (r"\bauthentication\b", "auth"),
    (r"\bconfiguration\b", "config"),
    (r"\brequest\b", "req"),
    (r"\bresponse\b", "res"),
    (r"\bfunction\b", "fn"),
    (r"\bimplementation\b", "impl"),
    (r"\benvironment\b", "env"),
    (r"\bdependencies\b", "deps"),
    (r"\bdependency\b", "dep"),
    (r"\brepository\b", "repo"),
    (r"\brepositories\b", "repos"),
    (r"\bdocumentation\b", "docs"),
    (r"\bapplication\b", "app"),
]

CAUSALITY_PATTERNS = [
    (
        re.compile(
            r"\b(?:which[^\S\n]+)?(?:leads?[^\S\n]+to|results?[^\S\n]+in|gives?[^\S\n]+you)[^\S\n]+",
            re.IGNORECASE,
        ),
        "-> ",
    ),
    (re.compile(r"\bbecause\s+of\b", re.IGNORECASE), "<- "),
]

EXCEPTION_MARKERS = [
    re.compile(r"\*\*warning:\*\*", re.IGNORECASE),
    re.compile(r"\bdestructive\b", re.IGNORECASE),
    re.compile(r"\birreversible\b", re.IGNORECASE),
    re.compile(r"\bcannot be undone\b", re.IGNORECASE),
]

SAMPLE_INPUT = (
    "Sure! I'd be happy to help you with that. The issue you're experiencing is "
    "likely caused by a misconfiguration in the authentication middleware, where "
    "the token expiry check is actually using a strict less-than comparison "
    "instead of less-than-or-equal. This basically means tokens at the exact "
    "expiry timestamp will get rejected. To fix this, you should simply update "
    "the configuration of the auth function to use `<=` instead of `<`."
)


def _has_exception_context(text: str) -> bool:
    return any(pattern.search(text) for pattern in EXCEPTION_MARKERS)


def _protect_literals(text: str) -> Tuple[str, List[str]]:
    protected: List[str] = []

    def replace_literal(match: re.Match) -> str:
        protected.append(match.group(0))
        return f"\x00LITERAL{len(protected) - 1}\x00"

    text = re.sub(r"```.*?```", replace_literal, text, flags=re.DOTALL)
    text = re.sub(r"`[^`]+`", replace_literal, text)
    text = re.sub(r'(?<!\w)"(?:\\.|[^"\\])*"', replace_literal, text)
    text = re.sub(SINGLE_QUOTED_LITERAL_PATTERN, replace_literal, text)
    return text, protected


def _restore_literals(text: str, protected: List[str]) -> str:
    for index, literal in enumerate(protected):
        text = text.replace(f"\x00LITERAL{index}\x00", literal)
    return text


def _drop_articles(text: str) -> str:
    pattern = re.compile(r"\b(an|the)[^\S\n]+", re.IGNORECASE)
    text = pattern.sub("", text)
    return re.sub(
        r"\ba[^\S\n]+(?!(?:==|!=|<=|>=|=|->|[+*/%&|^-]))",
        "",
        text,
        flags=re.IGNORECASE,
    )


def _drop_word_set(text: str, words: set) -> str:
    pattern = re.compile(r"\b(" + "|".join(words) + r")\b[^\S\n]*", re.IGNORECASE)
    return pattern.sub("", text)


def _drop_phrases(text: str, phrases: Tuple[str, ...]) -> str:
    for phrase in sorted(phrases, key=len, reverse=True):
        pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)[!,]?[^\S\n]*"
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text


def _apply_abbreviations(text: str) -> str:
    for pattern, replacement in ABBREVIATIONS:
        def replace_abbreviation(match: re.Match) -> str:
            if match.group(0)[0].isupper() and replacement[0].islower():
                return replacement[0].upper() + replacement[1:]
            return replacement

        text = re.sub(pattern, replace_abbreviation, text, flags=re.IGNORECASE)
    return text


def _apply_causality_arrows(text: str) -> str:
    for pattern, replacement in CAUSALITY_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _strip_leading_conjunctions(text: str) -> str:
    return re.sub(r"(^|\.\s+)(and|but|so)\s+", r"\1", text, flags=re.IGNORECASE)


def _collapse_whitespace(text: str) -> str:
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"[^\S\n]+([.,;:!?])", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def compress(text: str) -> str:
    """Apply Matt Pocock's caveman rules. Returns compressed text."""
    if _has_exception_context(text):
        return text

    text, protected = _protect_literals(text)
    text = _drop_phrases(text, PLEASANTRY_PHRASES)
    text = _drop_phrases(text, METATALK_PHRASES)
    text = _drop_word_set(text, FILLER_WORDS)
    text = _drop_word_set(text, HEDGING_WORDS)
    text = _drop_articles(text)
    text = _apply_abbreviations(text)
    text = _apply_causality_arrows(text)
    text = _strip_leading_conjunctions(text)
    text = _collapse_whitespace(text)
    return _restore_literals(text, protected)


def analyze(original: str, compressed: str) -> Dict[str, Any]:
    orig_words = len(original.split())
    new_words = len(compressed.split())
    saved = orig_words - new_words
    pct = round(100.0 * saved / max(orig_words, 1), 1)
    return {
        "original_chars": len(original),
        "compressed_chars": len(compressed),
        "original_words": orig_words,
        "compressed_words": new_words,
        "words_saved": saved,
        "percent_savings": pct,
        "compressed_text": compressed,
    }


def render_text(original: str, result: Dict[str, Any]) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append("CAVEMAN COMPRESSOR")
    lines.append("=" * 72)
    lines.append("")
    lines.append("ORIGINAL:")
    lines.append(f"  {original}")
    lines.append("")
    lines.append("COMPRESSED:")
    lines.append(f"  {result['compressed_text']}")
    lines.append("")
    lines.append("-" * 72)
    lines.append(f"Chars: {result['original_chars']} -> {result['compressed_chars']}")
    lines.append(f"Words: {result['original_words']} -> {result['compressed_words']}")
    lines.append(f"Savings: {result['words_saved']} words ({result['percent_savings']}%)")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compress text per Matt Pocock's caveman rules.",
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
                original = file.read()
        except (OSError, UnicodeDecodeError) as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
    elif args.text:
        original = args.text
    else:
        original = SAMPLE_INPUT

    compressed = compress(original)
    result = analyze(original, compressed)

    if args.output == "json":
        print(json.dumps(result, indent=2))
    else:
        print(render_text(original, result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
