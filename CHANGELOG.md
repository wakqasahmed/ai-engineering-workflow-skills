# Changelog

All notable changes to this workflow repository should be documented here.

The goal is transparency over time: what changed, why it changed, and when the workflow evolved.

## 2026-06

### Added

- execution-discipline rules for assumptions, success criteria, scoped diffs, newly unused code, and trivial-change judgment
- proactive `tdd`, `simplify`, `diagnose`, and `security-review` trigger guidance
- optional skill prerequisite and user-level instruction synchronization guidance
- CI check that keeps the root agent entrypoints aligned
- extremely concise reporting guidance
- standing authorization guidance for cold-start reviewer subagents

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
