#!/usr/bin/env python3
"""Harness-owned fake issue tracker CLI for to-prd's outcome harness.

Copied into the evaluated agent's workspace as `fake-tracker`, standing in
for the real project issue tracker the agent's SKILL.md says to detect and
publish to. The evaluated agent invokes this to create and label a spec.
Every successful call appends one entry to `tracker-log.jsonl` in the same
directory — the agent cannot fabricate a log entry, since only this script's
own execution writes one. `target-agent-adapter.py` derives `published` and
`ready_for_agent` exclusively from this log, never from anything the agent
writes or prints itself.

Usage:
    fake-tracker create --title TITLE --body BODY
    fake-tracker label --add LABEL
"""
import json
import sys
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent / "tracker-log.jsonl"


def _parse_flag(args: list[str], name: str) -> str | None:
    if name in args:
        index = args.index(name)
        if index + 1 < len(args):
            return args[index + 1]
    return None


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("usage: fake-tracker <create|label> ...", file=sys.stderr)
        return 2

    action = args[0]
    rest = args[1:]

    if action == "create":
        title = _parse_flag(rest, "--title")
        body = _parse_flag(rest, "--body")
        if not title or body is None:
            print("create requires --title and --body", file=sys.stderr)
            return 2
        entry = {"action": "create", "title": title, "body": body}
        result = {"ok": True, "id": "spec-1"}
    elif action == "label":
        label = _parse_flag(rest, "--add")
        if not label:
            print("label requires --add", file=sys.stderr)
            return 2
        entry = {"action": "label", "label": label}
        result = {"ok": True}
    elif action == "update":
        spec_id = _parse_flag(rest, "--id")
        body = _parse_flag(rest, "--body")
        if not spec_id or body is None:
            print("update requires --id and --body", file=sys.stderr)
            return 2
        entry = {"action": "update", "id": spec_id, "body": body}
        result = {"ok": True}
    else:
        print(f"unknown action: {action}", file=sys.stderr)
        return 2

    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(entry) + "\n")

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
