#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path


DEFAULT_PATHS = (
    Path(".github/workflows"),
    Path("skills/engineering/open-code-review-setup/templates"),
)
# The `uses` mapping key accepts an optional matching pair of quotes in YAML
# (`'uses': x` and `uses: x` are the same key) — match both via a backreference,
# so a quoted key cannot silently bypass this check the way an unquoted-only
# pattern would. The value itself is matched as either a quoted string (up to
# its matching closing quote, so a space or '#' inside the quotes doesn't
# truncate it) or an unquoted token (up to whitespace, '#', or a quote).
USES_PATTERN = re.compile(
    r"^\s*-?\s*(['\"]?)uses\1:\s*"
    r"(?:\"([^\"]*)\"|'([^']*)'|([^\"'\s#]+))"
)
FULL_SHA_PATTERN = re.compile(r"[0-9a-fA-F]{40}")
LOCAL_ACTION_PATTERN = re.compile(r"^\.{0,2}/")


def workflow_files(paths):
    for path in paths:
        if not path.exists():
            print(f"warning: path does not exist, skipping: {path}", file=sys.stderr)
            continue
        if path.is_file():
            yield path
            continue
        yield from sorted(path.rglob("*.yml"))
        yield from sorted(path.rglob("*.yaml"))


def main():
    parser = argparse.ArgumentParser(
        description="Reject GitHub Actions references that are not pinned to full commit SHAs."
    )
    parser.add_argument("paths", nargs="*", type=Path, default=DEFAULT_PATHS)
    args = parser.parse_args()

    files = list(workflow_files(args.paths))
    action_count = 0
    processed_files = 0
    failures = []
    for path in files:
        try:
            lines = path.read_text().splitlines()
        except OSError as error:
            failures.append(f"{path}: could not read file: {error}")
            continue
        processed_files += 1
        for line_number, line in enumerate(lines, start=1):
            match = USES_PATTERN.match(line)
            if not match:
                continue
            reference = match.group(2)
            if reference is None:
                reference = match.group(3)
            if reference is None:
                reference = match.group(4)
            # Local actions (./path, ../path, /absolute/path) are checked out
            # from this same repository, not fetched by ref, so there is no
            # commit SHA to pin.
            if LOCAL_ACTION_PATTERN.match(reference):
                continue
            action_count += 1
            _, separator, revision = reference.rpartition("@")
            if not separator or not FULL_SHA_PATTERN.fullmatch(revision):
                failures.append(
                    f"{path}:{line_number}: action reference must use a full "
                    f"40-character commit SHA: {reference}"
                )

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1

    print(f"validated {action_count} action references across {processed_files} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
