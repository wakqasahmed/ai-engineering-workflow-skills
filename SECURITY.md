# Security Policy

## What This Repository Is

This repository contains Agent Skills: Markdown instruction files (`SKILL.md`) plus a small
number of shell helper scripts under `scripts/`. The `SKILL.md` files are **not executable
code** — they are prompts read by an AI coding agent (Claude, or another agent that supports
the Agent Skills / `AGENTS.md` convention). Installing a skill does not run any code by
itself; the risk surface is what the *agent* does when it later follows the instructions in
that file, using whatever tools and permissions the agent already has (shell, git, `gh`,
file edits, etc.).

In short: treat a `SKILL.md` the same way you would treat a code review checklist or a
runbook handed to a new engineer — advisory text that a sufficiently privileged actor (here,
an AI agent) can choose to act on. It is not a binary, a package with a build step, or
something that executes on `npm install` / `pip install`.

## What Can Actually Execute

- Everything under `scripts/` (`install-user.sh`, `list-skills.sh`, `link-skills.sh`,
  `test-install-user.sh`, `validate-plugin.py`) is real, executable shell/Python. Review any
  script before running it, as you would any script from the internet. `install-user.sh`
  writes/backs up files under `$HOME` (or `--target-home`) and supports `--dry-run` to preview
  changes without writing anything. `test-install-user.sh` and `validate-plugin.py` are
  dev/CI-only checks with no network or destructive action.
- `skills/engineering/subagent-pipeline/SKILL.md` instructs the agent to run `gh` CLI
  commands (`gh pr review`, `gh api .../pulls/.../comments`, `gh pr merge`) against GitHub on
  the agent's behalf, as part of an implement -> review -> fix -> merge workflow. These are
  authenticated GitHub operations, not arbitrary remote code execution, but they do mean an
  agent following this skill can open PRs, post review comments, and merge to a repository it
  has access to.
- No `SKILL.md` in this repository instructs fetching remote URLs (`curl`, `wget`, HTTP
  fetch) as part of its documented workflow. If you find one that does in a future revision,
  please report it (see below) so this file can be updated.

## Reporting a Security Concern

Please report security concerns by opening a
[GitHub issue](https://github.com/wakqasahmed/ai-engineering-workflow-skills/issues/new) in
this repository. Use the `security` label if available. For concerns you would prefer not to
disclose publicly before a fix lands, mention that in the issue title (e.g. "SECURITY: ...")
and keep exploit details out of the initial issue body — a maintainer will follow up on how
to share specifics.

This is a solo-maintained, community-facing skills repository with no dedicated security
contact address; GitHub issues are the fastest and most reliable way to reach the maintainer.

## Scope

This policy covers the contents of this repository only: the `SKILL.md` files, `AGENTS.md`,
`CLAUDE.md`, `AI_ENGINEERING_WORKFLOW.md`, `system-level/core.md`, and `scripts/`. It does not
cover the security posture of any AI agent or CLI tool that installs or runs these skills
(e.g. Claude Code, other Agent Skills clients) — report issues with those tools to their own
maintainers.
