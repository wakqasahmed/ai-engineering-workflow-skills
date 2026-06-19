---
name: review-gate
description: Run an independent review gate before merging non-trivial work. Use after implementation and verification, especially for medium/high-risk changes.
---

# Review Gate

Use this after implementation and before merge.

## Workflow

1. Confirm linked issue and acceptance criteria.
2. Confirm verification commands and results.
3. Review spec compliance before code style.
4. Check regression, security, maintainability, and missing-test risks.
5. Post concrete findings or explicitly state no blocking issues.
6. Apply review findings before merge.

## Reviewer Contract

The reviewer should read the issue, acceptance criteria, and PR diff first. Pull more context only when needed.

## Merge Rule

Do not merge non-trivial work without a review record. If an automated or subagent reviewer stalls, post a manual expert review that states residual risk.
