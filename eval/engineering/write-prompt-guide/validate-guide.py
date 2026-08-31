#!/usr/bin/env python3
"""Structural validator for a generated PROMPT_GUIDE.md.

Given a guide's Markdown and the target pack's own documentation text, report
every structural or fabrication failure. The capability vocabulary is derived
from the pack's documentation, never accepted as a caller-supplied allow-list:
a run being audited must not be able to declare its own inventions legitimate.
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
ISSUE_REF = re.compile(r"(?:#(\d+)|/(?:issues|pull)/(\d+))")

FIX_CLAIM = re.compile(
    r"\b(fixed|fixes|resolved|resolves|shipped|landed|addressed|handled|solved|patched|"
    r"corrected|remedied|closed|released|merged|live|no longer (?:an? )?(?:issue|concern|problem|possible))\b",
    re.I,
)
UNMERGED_HEDGE = re.compile(
    r"\b(open|unmerged|not (?:yet )?(?:merged|released|shipped|on main)|"
    r"un(?:released|shipped)|pending|proposed|in review|under review|awaiting (?:review|merge)|"
    r"draft|queued|will be|once merged)\b",
    re.I,
)
DISMISSIVE = re.compile(
    r"\b(nothing (?:significant|major|much|notable)|no (?:known|significant|major) "
    r"(?:limitations|issues|caveats)|none (?:known|significant)|works as expected|no caveats)\b",
    re.I,
)

CAPABILITY_CLAIM = re.compile(r"`([a-z0-9][a-z0-9-]{2,})`")
VOCAB_TOKEN = re.compile(r"[a-z0-9][a-z0-9-]{2,}", re.I)

# Hyphenated English/prompt-craft vocabulary that is never a pack capability.
# Fixed in code so that no caller can extend it.
GENERIC_HYPHENATED = frozenset({
    "prompt-guide", "copy-pasteable", "multi-phase", "multi-step", "step-by-step",
    "follow-up", "up-to-date", "read-only", "end-to-end", "high-level", "low-level",
    "few-shot", "zero-shot", "one-shot", "well-known", "real-world", "out-of-the-box",
    "long-running", "self-contained", "non-negotiable", "case-by-case", "so-called",
})

PROSE_CAPABILITY_CLAIM = re.compile(
    r"[^.\n]*\b(?:pack|skill|skills)\b[^.\n]*?"
    r"\b(?:can|will|is able to|are able to|lets you|allows you to|automatically)\b[^.\n]*\.",
    re.I,
)

MIN_LIMITATION_ENTRIES = 2
MIN_LIMITATION_WORDS = 25


def derive_vocabulary(pack_docs: str) -> set[str]:
    """Every hyphenated identifier the target pack's own documentation actually uses."""
    return {t.lower() for t in VOCAB_TOKEN.findall(pack_docs) if "-" in t}


def find_fabricated_capabilities(guide: str, pack_docs: str) -> list[str]:
    """Backtick-quoted hyphenated identifiers absent from the target pack's documentation."""
    vocabulary = derive_vocabulary(pack_docs)
    claimed = {m.group(1).lower() for m in CAPABILITY_CLAIM.finditer(guide)}
    return sorted(
        c for c in claimed
        if "-" in c and c not in vocabulary and c not in GENERIC_HYPHENATED
    )


def find_ungrounded_prose_claims(guide: str, pack_docs: str) -> list[str]:
    """Prose sentences asserting a pack capability without naming a capability the pack ships."""
    vocabulary = derive_vocabulary(pack_docs)
    ungrounded = []
    for match in PROSE_CAPABILITY_CLAIM.finditer(guide):
        sentence = " ".join(match.group(0).split())
        named = {t.lower() for t in VOCAB_TOKEN.findall(sentence) if "-" in t}
        if not named & vocabulary:
            ungrounded.append(sentence)
    return ungrounded


def _limitation_entries(limitations: str) -> list[str]:
    entries = []
    for line in limitations.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        entries.append(re.sub(r"^([-*+]|\d+\.)\s+", "", stripped))
    return entries


def _claim_units(entry: str) -> list[str]:
    return [u.strip() for u in re.split(r"(?<=[.;])\s+", entry) if u.strip()]


def check_limitations(limitations: str) -> list[str]:
    failures = []
    entries = _limitation_entries(limitations)

    if DISMISSIVE.search(limitations):
        failures.append("limitations section dismisses limitations instead of disclosing them")
    if len(entries) < MIN_LIMITATION_ENTRIES:
        failures.append(
            f"limitations section needs at least {MIN_LIMITATION_ENTRIES} disclosed limitations, found {len(entries)}"
        )
    words = len(limitations.split())
    if words < MIN_LIMITATION_WORDS:
        failures.append(
            f"limitations section is too thin to be a disclosure: {words} words, needs {MIN_LIMITATION_WORDS}"
        )
    if not ISSUE_REF.search(limitations):
        failures.append("limitations section cites no issue or PR reference")
    else:
        unreferenced = [e for e in entries if not ISSUE_REF.search(e)]
        if unreferenced:
            failures.append(f"limitations without an issue or PR reference: {unreferenced}")

    for entry in entries:
        for unit in _claim_units(entry):
            if FIX_CLAIM.search(unit) and not UNMERGED_HEDGE.search(unit):
                failures.append(f"fix claimed without its merge state in the same claim: {unit!r}")

    return failures


def issue_refs(guide: str) -> list[str]:
    return sorted({m.group(1) or m.group(2) for m in ISSUE_REF.finditer(guide)}, key=int)


def validate(guide: str, pack_docs: str) -> list[str]:
    failures = []

    for name, pattern in REQUIRED_SECTIONS:
        if not pattern.search(guide):
            failures.append(f"missing required section: {name}")

    pairs = min(len(LESS_EFFECTIVE.findall(guide)), len(MORE_EFFECTIVE.findall(guide)))
    if pairs < 2:
        failures.append(f"needs at least two less-effective/more-effective prompt pairs, found {pairs}")

    if "```" not in guide:
        failures.append("no fenced code block: prompts must be copy-pasteable")

    limitations = _section_body(guide, REQUIRED_SECTIONS[4][1])
    if limitations is not None:
        failures.extend(check_limitations(limitations))

    fabricated = find_fabricated_capabilities(guide, pack_docs)
    if fabricated:
        failures.append(f"names capabilities absent from the target pack: {fabricated}")

    ungrounded = find_ungrounded_prose_claims(guide, pack_docs)
    if ungrounded:
        failures.append(f"prose capability claims naming no capability the pack ships: {ungrounded}")

    return failures


def _section_body(guide: str, heading: re.Pattern) -> str | None:
    match = heading.search(guide)
    if not match:
        return None
    line_end = guide.find("\n", match.end())
    rest = guide[line_end + 1:] if line_end != -1 else ""
    following = re.search(r"^#{2,3}\s", rest, re.M)
    return rest[: following.start()] if following else rest


def _verify_refs(guide: str, repo: str) -> list[str]:
    import json
    import subprocess

    failures = []
    for ref in issue_refs(guide):
        probe = subprocess.run(
            ["gh", "api", f"repos/{repo}/issues/{ref}", "--jq",
             '{state: .state, merged: (.pull_request.merged_at != null)}'],
            capture_output=True, text=True,
        )
        if probe.returncode != 0:
            failures.append(f"#{ref} does not resolve in {repo}")
            continue
        state = json.loads(probe.stdout)
        if state["merged"]:
            failures.append(f"#{ref} is already merged and must not be listed as an open limitation")
    return failures


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("guide", help="path to the generated PROMPT_GUIDE.md")
    parser.add_argument("pack_docs", nargs="+", help="paths to the target pack's SKILL.md / README.md files")
    parser.add_argument("--verify-refs", metavar="OWNER/REPO",
                        help="resolve every #N in the guide against a real repo (requires network and gh)")
    args = parser.parse_args()

    text = Path(args.guide).read_text()
    docs = "\n".join(Path(p).read_text() for p in args.pack_docs)
    problems = validate(text, docs)
    if args.verify_refs:
        problems += _verify_refs(text, args.verify_refs)
    if problems:
        print("\n".join(f"- {p}" for p in problems))
        raise SystemExit(1)
    print("PASS: guide structure")
