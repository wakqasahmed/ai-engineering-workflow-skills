# Changelog

All notable changes to this workflow repository should be documented here.

The goal is transparency over time: what changed, why it changed, and when the workflow evolved.

## 2026-06

### Added

- installable `skills/` layout with short independent workflow skills
- Claude plugin metadata plus skill listing and plugin-path validation scripts
- safe user-level installer for `AGENTS.md` and `.claude/CLAUDE.md`, with dry-run, backups, conflict reporting, and CI coverage
- execution-discipline rules for assumptions, success criteria, scoped diffs, newly unused code, and trivial-change judgment
- proactive `tdd`, `simplify`, `diagnose`, and `security-review` trigger guidance
- optional skill prerequisite and user-level instruction synchronization guidance
- CI check that keeps the root agent entrypoints aligned
- extremely concise reporting guidance
- standing authorization guidance for cold-start reviewer subagents
- scale-adaptive planning tracks, clean-baseline checks, two-stage review, and manual acceptance walkthrough guidance
- instruction hygiene, deterministic enforcement, and production dependency checkpoints
- issue claiming before agent execution to reduce duplicate work
- guidance to use the strongest practical model and reasoning effort for independent reviewer agents

## 2026-05

### Added

- initial public workflow playbook
- root agent entrypoints via `AGENTS.md` and `CLAUDE.md`
- `system-level/core.md` for invariant operating rules
- `AI_ENGINEERING_WORKFLOW.md` for the full workflow, issue shape, PR shape, risk levels, and failure paths

### Changed

- removed month-specific branding from core docs so the repository can evolve continuously
- moved version tracking from inline document text to this changelog
- narrowed the `Influences` section to reflect the repository's current contents instead of future technology-specific skill packs
