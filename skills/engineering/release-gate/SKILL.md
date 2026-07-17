---
name: release-gate
description: Check deployment, staging, rollback, and health verification before release. Use for user-facing, infrastructure, CI/CD, integration, or high-risk changes.
---

# Release Gate

Use this before staging or production release.

## Workflow

1. Confirm the reviewed commit or artifact being released.
2. Confirm environment and deployment mechanism.
3. Run the smallest deployment validation available.
4. Smoke-test the critical route or workflow.
5. Record rollback path.
6. Create a HITL issue if deployment needs missing human-held access.

## Required For Medium/High Risk

- CI status
- Review status
- Target environment
- Smoke test command
- Rollback command or previous artifact
- Health check signal

## Guardrails

- Prefer deploying reviewed artifacts over rebuilding unreviewed source.
- Do not deploy production from unreviewed PRs.
- Do not silently work around missing secrets, DNS, or account permissions.
- Test database safety (disposable/dedicated storage, staging backup timing) follows `system-level/core.md` (Test Database Safety) — this gate does not relax it.
