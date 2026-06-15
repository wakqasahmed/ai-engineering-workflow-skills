---
name: define-done
description: Define acceptance criteria, risk level, and verification before editing. Use at the start of non-trivial implementation or when an issue lacks clear proof of completion.
---

# Define Done

Use this before changing code or docs on non-trivial work.

## Workflow

1. Classify risk: low, medium, or high.
2. Write testable acceptance criteria.
3. Name the minimum verification commands or manual checks.
4. Record known constraints and non-goals.
5. State rollback or recovery notes for medium/high-risk changes.

## Risk Rules

- Low: narrow copy, style, test-only, or isolated bug fix.
- Medium: user-visible behavior, business logic, data handling, CI, integrations, or multi-file behavior.
- High: auth, payments, permissions, secrets, migrations, deployment, infrastructure, tenant data, or irreversible operations.

## Done Means

- Acceptance criteria satisfied.
- Relevant checks run and named.
- Tests added/updated, or a reason is recorded.
- Independent review completed for non-trivial work.
- Rollout/rollback notes present when risk warrants them.
