# AI Engineering Workflow Skills [![skills.sh](https://skills.sh/b/wakqasahmed/ai-engineering-workflow-skills)](https://skills.sh/wakqasahmed/ai-engineering-workflow-skills)

Reusable skills and operating notes for AI-assisted software engineering work.

Use this repo when you want an AI coding agent to clarify work, decompose issues, define done, handle HITL blockers, review releases, and preserve handovers across sessions. It is written for humans deciding whether to install the workflow and for agents that need concise execution rules.

This repository is descriptive first for humans adopting the workflow. Its agent entrypoints are directive when loaded by an AI coding agent.

## Who This Is For

- Founders and engineering leads who delegate implementation to AI coding agents.
- Developers who want repeatable issue decomposition, verification, review, and release gates.
- Agents that need short skills backed by a deeper workflow playbook.
- Teams that want human-in-the-loop blockers to become visible GitHub issues instead of hidden chat failures.

## Repository Structure

- `AGENTS.md`: neutral agent entrypoint
- `CLAUDE.md`: compatibility entrypoint
- `AI_ENGINEERING_WORKFLOW.md`: full workflow, role contracts, risk levels, and failure paths
- `system-level/core.md`: invariant operating principles for agents

## Start Here

1. Read `AGENTS.md` or `CLAUDE.md`.
2. Read `system-level/core.md` for stable rules.
3. Read `AI_ENGINEERING_WORKFLOW.md` for the full workflow.
4. Read `CHANGELOG.md` for periodic updates and revision history.

## Install Skills

Install the workflow skills with skills.sh-compatible tooling:

```bash
npx skills@latest add wakqasahmed/ai-engineering-workflow-skills
```

For local Claude CLI development, link the skills directly:

```bash
scripts/list-skills.sh
scripts/link-skills.sh
```

The installable skills are intentionally short and independent. Use `AI_ENGINEERING_WORKFLOW.md` as the deeper reference playbook when a skill needs more detail.

## Marketplace And Discovery

Public install command: `npx skills@latest add wakqasahmed/ai-engineering-workflow-skills`

Checklist:

- Keep `.claude-plugin/plugin.json` in sync with every published skill path.
- Keep skill descriptions activation-focused so agents load the right workflow.
- Install once with `npx skills@latest add wakqasahmed/ai-engineering-workflow-skills` to seed skills.sh visibility.
- Link this repo from public profiles and from domain-specific skill packs that depend on the workflow.

## Positioning

This is the general engineering workflow pack. Domain-specific skills, such as Agentic Commerce or ecommerce SEO/AEO/GEO work, belong in separate repositories that can depend on this workflow.

## Install User-Level Entrypoints

Inspired by the installer discipline in `alirezarezvani/claude-skills`, this repo includes a small installer for the two user-level entrypoints only. It does not install third-party skill catalogs.

Preview the install:

```bash
scripts/install-user.sh --dry-run
```

Install to the current user:

```bash
scripts/install-user.sh --force
```

Default targets:

- `AGENTS.md` -> `$HOME/AGENTS.md`
- `CLAUDE.md` -> `$HOME/.claude/CLAUDE.md`

If an existing target file differs, the installer reports a conflict and stops unless `--force` is passed. With `--force`, it backs up the existing file under `$HOME/.ai-engineering-workflow-backups/<timestamp>/` before replacing it.

For test or staging installs:

```bash
scripts/install-user.sh --target-home /tmp/workflow-install-test --dry-run
```

## What This Repository Tries To Solve

- context bloat in long-running agent sessions
- weak decomposition of high-level work
- fuzzy issue boundaries
- inconsistent verification
- weak review and assistance traceability
- poor cross-agent continuity

## Core Idea

Decomposition is not only a planning device. It is a context-quality control mechanism for AI agents. High-level work should be clarified, decomposed into issues, and executed by issue-scoped agents whenever practical.

## Workflow Summary

1. Pressure-test a new idea with `roast` before committing to build it.
2. Clarify high-level work with `clarify-work`.
3. Use `to-prd` when scope or success criteria are still fuzzy.
4. Use `decompose-to-issues` to create issue-sized execution units.
5. Prefer a fresh agent per issue by default.
6. Define acceptance criteria and verification before implementation.
7. Use risk levels to choose verification, review, staging, and rollback gates.
8. Use an independent review pass before merge.
9. Preserve automation/assistance traceability in PRs.
10. Use risk-based staging and HITL before production when warranted.
11. Use `handover` when context crosses an agent or session boundary, when only 5-10% of the session limit remains with work unfinished, or when context usage passes 40% on unfinished multi-step work.

Planning depth should match the work: quick for trivial changes, standard for non-trivial issues, and deep for ambiguous or architectural work.

## Optional Skill Prerequisites

Some workflow triggers rely on separately installed skills:

- `simplify`: `brianlovin/claude-config@simplify`
- `security-review`: `getsentry/skills@security-review`
- `security-best-practices`: OpenAI curated skill for supported Python, JavaScript/TypeScript, and Go projects

Project-level conventions override skill defaults. In particular, the recommended `simplify` skill includes JavaScript-specific defaults that do not apply universally. Treat `security-best-practices` as an optional supported-stack supplement, not a mandatory workflow dependency.

## User-Level Installation

For user-level installations with duplicate instruction files, choose one canonical file and symlink compatibility files to it when the operating environment supports symlinks. Compare existing contents and create a backup before normalization.

Keep repository copies as regular files for portability across operating systems and packaging tools.

## Publishing Notes

- This repository should stay free of private project details.
- Technology-specific guidance belongs in separate skill packs.
- Workflow changes should be versioned over time in `CHANGELOG.md`.
