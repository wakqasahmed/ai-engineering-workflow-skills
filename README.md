# May 2026 Skills

My public AI-assisted engineering workflow as of May 2026.

This repository is descriptive first for humans adopting the workflow. Its agent entrypoints are directive when loaded by an AI coding agent.

## Repository Structure

- `AGENTS.md`: neutral agent entrypoint
- `CLAUDE.md`: compatibility entrypoint
- `AI_ENGINEERING_WORKFLOW.md`: full workflow, role contracts, risk levels, and failure paths
- `system-level/core.md`: invariant operating principles for agents

## Start Here

1. Read `AGENTS.md` or `CLAUDE.md`.
2. Read `system-level/core.md` for stable rules.
3. Read `AI_ENGINEERING_WORKFLOW.md` for the full May 2026 workflow.

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

## Publishing Notes

- This repository should stay free of private project details.
- Technology-specific guidance belongs in separate skill packs.
- Workflow changes can be versioned over time; this repository captures the May 2026 version.
