# AI Engineering Workflow Skills

This file mirrors `AGENTS.md` for compatibility.

## Start Here

- Follow `system-level/core.md` for invariant operating rules.
- For non-trivial work, follow `AI_ENGINEERING_WORKFLOW.md`, including risk level, definition of done, and failure-path guidance.

## Trigger Map

- Use `grill-with-docs` for high-level task clarification and decomposition.
- Use `to-prd` when scope, terminology, or success criteria are still fuzzy.
- Use `to-issues` before implementation on high-level work.
- Use `tdd` when building features or fixing bugs where expected behavior is clear.
- Use `simplify` after implementing a feature.
- Use `diagnose` when something is broken, throwing, or regressing.
- Use `security-review` before PRs touching auth, payments, secrets, or external APIs.
- Use `handoff` only when context crosses an agent or session boundary.

## Summary

- Keep implementation agents issue-scoped to avoid context bloat.
- Define acceptance criteria and verification before implementation.
- Prefer a fresh agent per issue by default.
- Require independent review and preserve automation/assistance traceability in merged PRs.
