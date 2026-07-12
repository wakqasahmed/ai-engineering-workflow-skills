---
name: review-gate
description: Run an independent semantic review gate before merging non-trivial work, on top of (not duplicating) Alibaba Code Review and CI. Use after implementation and verification, especially for medium/high-risk changes.
---

# Review Gate

Use this after implementation and before merge.

## Division of Labor

- **Mechanical checks — owned by Alibaba Code Review and CI**: linting, formatting, conventional style, and straightforward static-analysis findings. Alibaba Code Review's output is recorded via `ai-agent-pr-metadata`.
- **Semantic review — owned by this gate**: requirements compliance, correctness, regressions, security/authorization, contract/integration risk, and acceptance-test adequacy — everything mechanical tooling can't judge.

## Workflow

1. Confirm linked issue and acceptance criteria.
2. Confirm verification commands and results.
3. Read Alibaba Code Review's findings and the GitHub CI/check results on the PR before starting the independent review — don't re-derive what's already there.
4. Review spec compliance before code style.
5. Check business logic and edge cases, regressions and compatibility, security and authorization, API/database/queue/integration contracts, and test adequacy including missing acceptance tests.
6. Revisit an Alibaba Code Review or CI finding only when it indicates an unresolved correctness, security, data-loss, configuration, or acceptance-criteria issue — not to relitigate style or formatting.
7. Post concrete findings or explicitly state no blocking issues. Do not repeat resolved lint, formatting, conventional-style, or straightforward static-analysis findings Alibaba Code Review or CI already covered.
8. Apply review findings before merge.

## Reviewer Contract

The reviewer should read the issue, acceptance criteria, Alibaba Code Review's output, CI results, and the PR diff first. Pull more context only when needed.

## Merge Rule

CI remains a hard merge gate; this review does not replace it and is not the place to rerun or restate lint/static-analysis automation. Do not merge non-trivial work without a review record. If an automated or subagent reviewer stalls, post a manual expert review that states residual risk.
