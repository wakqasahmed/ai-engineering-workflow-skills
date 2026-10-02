#!/usr/bin/env python3
"""Fail when tracked files leak local or private details: absolute home paths,
token-file paths, credential-shaped strings, or names on a private denylist.

With no arguments, scans every file `git ls-files` tracks. With paths, scans
those files (directories recursively) instead.

The private denylist is never committed: it is read from the `LEAK_DENYLIST`
environment variable (newline- or comma-separated, matched case-insensitively
as substrings), which CI fills from a repository secret. Denylist hits are
reported by file, line, and entry number only, so the CI log never echoes a
private name. Credential hits are redacted the same way.

A line containing `leak-check: allow` is skipped, for a reviewed mention that
must stay (for example, docs telling an agent never to read a credential
store).
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOW_MARKER = "leak-check: allow"
# This checker's own tests must spell out home and token-file paths to prove
# they are caught; credential and denylist rules still apply to them.
PATH_RULE_EXEMPT = {"tests/test_check_leaks.py"}

# `/home/agent` and `/home/evaluator` are the eval container's sandbox users,
# not anyone's real machine. The lookbehind skips URL paths such as
# `https://example.com/home/docs`; a placeholder like `/home/<user>` never
# matches because `<` is outside the username character class.
HOME_PATH_PATTERN = re.compile(
    r"(?<![\w.-])/home/(?!(?:agent|evaluator)(?![\w.-]))[A-Za-z0-9_][A-Za-z0-9._-]*"
    r"|(?<![\w.-])/Users/(?!Shared(?![\w.-]))[A-Za-z0-9_][A-Za-z0-9._-]*"
)
TOKEN_FILE_PATTERN = re.compile(
    # Well-known credential stores, wherever they are referenced.
    r"(?<![\w-])(?:\.git-credentials|\.netrc|\.pgpass|gh/hosts\.ya?ml)(?![\w-])"  # leak-check: allow
    # A home-rooted path whose name says it holds a secret.
    r"|(?:~|\$HOME|\$\{HOME\}|/root|/home/[\w.-]+|/Users/[\w.-]+)/[\w./-]*?"
    r"(?:token|credential|secret|api[_-]?key|(?<![a-z])pat(?![a-z]))",
    re.IGNORECASE,
)
CREDENTIAL_PATTERNS = (
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}")),
    # `\b` keeps `task-`, `disk-`, `risk-` out (no word boundary inside a
    # word), and requiring a digit in a 20+ character body keeps long
    # kebab-case identifiers that merely start with `sk-` out too.
    ("API secret key", re.compile(r"\bsk-(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]{20,}")),
)


def parse_denylist(raw):
    if not raw:
        return []
    entries = (entry.strip() for entry in re.split(r"[\n,]", raw))
    return [entry.lower() for entry in entries if entry]


def redact(text):
    return f"{text[:4]}... ({len(text)} chars)"


def scan_line(line, denylist, path_rules=True):
    """Return (column, message) for every leak on one line."""
    if ALLOW_MARKER in line:
        return []
    findings = []
    if path_rules:
        for match in HOME_PATH_PATTERN.finditer(line):
            findings.append((match.start() + 1, f"absolute home path {match.group(0)}"))
        for match in TOKEN_FILE_PATTERN.finditer(line):
            findings.append((match.start() + 1, f"token-file path {match.group(0)}"))
    for label, pattern in CREDENTIAL_PATTERNS:
        for match in pattern.finditer(line):
            findings.append((match.start() + 1, f"{label} {redact(match.group(0))}"))
    lowered = line.lower()
    for number, entry in enumerate(denylist, start=1):
        column = lowered.find(entry)
        if column != -1:
            findings.append((column + 1, f"private denylist entry #{number}"))
    return findings


def tracked_files():
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    )
    for name in result.stdout.decode("utf-8").split("\0"):
        if name:
            yield ROOT / name


def expand(paths):
    for path in paths:
        if path.is_dir():
            yield from sorted(p for p in path.rglob("*") if p.is_file())
        else:
            yield path


def display(path):
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def scan_file(path, denylist):
    name = display(path)
    findings = [
        f"{name}: file path matches private denylist entry #{number}"
        for number, entry in enumerate(denylist, start=1)
        if entry in name.lower()
    ]
    try:
        data = path.read_bytes()
    except OSError as error:
        return findings + [f"{name}: could not read file: {error}"]
    if b"\0" in data:
        return findings  # binary
    text = data.decode("utf-8", errors="replace")
    path_rules = name not in PATH_RULE_EXEMPT
    for line_number, line in enumerate(text.splitlines(), start=1):
        for column, message in scan_line(line, denylist, path_rules):
            findings.append(f"{name}:{line_number}:{column}: {message}")
    return findings


def main():
    parser = argparse.ArgumentParser(
        description="Reject home paths, token-file paths, credentials, and denylisted names."
    )
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()

    denylist = parse_denylist(os.environ.get("LEAK_DENYLIST", ""))
    try:
        files = list(expand(args.paths)) if args.paths else list(tracked_files())
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"could not list tracked files: {error}", file=sys.stderr)
        return 2

    findings = []
    for path in files:
        findings.extend(scan_file(path, denylist))

    if findings:
        print("\n".join(findings), file=sys.stderr)
        print(
            f"{len(findings)} leak(s) found. Replace them with a neutral placeholder, "
            f"or add `{ALLOW_MARKER}` to a reviewed line that must stay.",
            file=sys.stderr,
        )
        return 1

    denylist_note = f"{len(denylist)} denylist entries" if denylist else "no denylist configured"
    print(f"no leaks found across {len(files)} files ({denylist_note})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
