#!/usr/bin/env python3
"""Verify every external skill this repo references by name actually matches the
frontmatter `name:` of a real skill in the declared upstream pack, at a pinned
commit — not just an alias someone assumed was the installed name.

Agent Skills discovery is keyed by the frontmatter `name:` field
(https://agentskills.io/specification), not by any name a downstream repo
happens to call it. Fetches each pinned skill's SKILL.md over HTTPS (no GitHub
API token needed) and asserts the frontmatter name matches what this repo
documents installing and invoking.
"""
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Aliases this repo used before #166 — never the real frontmatter name of any
# dependency above. Catch a regression back to the wrong alias as a skill
# invocation (backtick-wrapped), without flagging the words in plain English
# prose (e.g. "simplify the changed code").
STALE_ALIAS_RE = re.compile(r"`(tdd|simplify|security-review)`")
DOC_FILES = (
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "AI_ENGINEERING_WORKFLOW.md",
    "system-level/core.md",
    "skills/engineering/workflow-router/SKILL.md",
)

EXTERNAL_SKILLS = (
    {
        "repo": "addyosmani/agent-skills",
        "pinned_sha": "84ee50673804b95c287d1e4eb4f1c1dad7c5188a",
        "skill_path": "test-driven-development",
        "expected_name": "test-driven-development",
    },
    {
        "repo": "addyosmani/agent-skills",
        "pinned_sha": "84ee50673804b95c287d1e4eb4f1c1dad7c5188a",
        "skill_path": "code-simplification",
        "expected_name": "code-simplification",
    },
    {
        "repo": "addyosmani/agent-skills",
        "pinned_sha": "84ee50673804b95c287d1e4eb4f1c1dad7c5188a",
        "skill_path": "security-and-hardening",
        "expected_name": "security-and-hardening",
    },
)

NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)


def fetch_frontmatter_name(repo: str, sha: str, skill_path: str) -> str:
    url = f"https://raw.githubusercontent.com/{repo}/{sha}/skills/{skill_path}/SKILL.md"
    with urllib.request.urlopen(url, timeout=15) as response:
        text = response.read().decode("utf-8")
    match = NAME_RE.search(text)
    if not match:
        raise AssertionError(f"{url}: no frontmatter 'name:' field found")
    return match.group(1)


def main() -> int:
    errors = []
    for dependency in EXTERNAL_SKILLS:
        url = (
            f"https://raw.githubusercontent.com/{dependency['repo']}/"
            f"{dependency['pinned_sha']}/skills/{dependency['skill_path']}/SKILL.md"
        )
        try:
            actual_name = fetch_frontmatter_name(
                dependency["repo"], dependency["pinned_sha"], dependency["skill_path"]
            )
        except Exception as exc:  # noqa: BLE001 - report any fetch/parse failure as a violation
            errors.append(f"{url}: could not verify frontmatter name ({exc})")
            continue
        if actual_name != dependency["expected_name"]:
            errors.append(
                f"{url}: frontmatter name is '{actual_name}', but this repo documents "
                f"and invokes it as '{dependency['expected_name']}'"
            )

    for relative_path in DOC_FILES:
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        for match in STALE_ALIAS_RE.finditer(text):
            line_number = text.count("\n", 0, match.start()) + 1
            errors.append(
                f"{relative_path}:{line_number}: invokes stale alias "
                f"`{match.group(1)}` — use its real installed frontmatter name instead"
            )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"validated {len(EXTERNAL_SKILLS)} external skill name(s) against their pinned revision")
    return 0


if __name__ == "__main__":
    sys.exit(main())
