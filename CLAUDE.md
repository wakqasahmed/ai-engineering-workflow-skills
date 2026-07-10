# AI Engineering Workflow Skills

This file mirrors `AGENTS.md` for compatibility.

## Start Here

- Follow `system-level/core.md` for invariant operating rules.
- For non-trivial work, follow `AI_ENGINEERING_WORKFLOW.md`, including risk level, definition of done, and failure-path guidance.

## Trigger Map

- Use `roast` before committing to build a new idea, to pressure-test it from multiple angles first.
- Use `clarify-work` for high-level task clarification.
- Use `to-prd` when scope, terminology, or success criteria are still fuzzy.
- Use `decompose-to-issues` before implementation on high-level work.
- Use `tdd` when building features or fixing bugs where expected behavior is clear.
- Use `simplify` after implementing a feature.
- Use `diagnose` when something is broken, throwing, or regressing.
- Use `security-review` before PRs touching auth, payments, secrets, or external APIs.
- Use `handover` when context crosses an agent or session boundary, when only 5-10% of the session limit remains with work unfinished, or when context usage passes 40% on unfinished multi-step work.

## Summary

- Keep implementation agents issue-scoped to avoid context bloat.
- Mark an issue as picked or claimed before an agent starts work on it.
- Define acceptance criteria and verification before implementation.
- Run tests only against disposable storage or a dedicated test database; never staging, production, customer, demo, or shared operational databases.
- Prefer a fresh agent per issue by default.
- Require independent review with reviewer model/effort chosen by the PR's risk and complexity, and preserve automation/assistance traceability in merged PRs.
