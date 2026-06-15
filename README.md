# AI Engineering Workflow Skills

My public AI-assisted engineering workflow and agent operating playbook.

This repository is descriptive first for humans adopting the workflow. Its agent entrypoints are directive when loaded by an AI coding agent.

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

Install through skills.sh-compatible tooling:

```bash
npx skills@latest add wakqasahmed/ai-engineering-workflow-skills
```

For local Claude CLI development, link the skills directly:

```bash
scripts/list-skills.sh
scripts/link-skills.sh
```

The installable skills are intentionally short and independent. Use `AI_ENGINEERING_WORKFLOW.md` as the deeper reference playbook when a skill needs more detail.

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

1. Clarify high-level work with `grill-with-docs`.
2. Use `to-prd` when scope or success criteria are still fuzzy.
3. Use `to-issues` to create issue-sized execution units.
4. Prefer a fresh agent per issue by default.
5. Define acceptance criteria and verification before implementation.
6. Use risk levels to choose verification, review, staging, and rollback gates.
7. Use an independent review pass before merge.
8. Preserve automation/assistance traceability in PRs.
9. Use risk-based staging and HITL before production when warranted.
10. Use `handoff` only when context crosses an agent or session boundary.

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
