# AI Engineering Workflow Skills

This repository contains my AI-assisted engineering workflow and agent operating playbook.

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
- Use `ai-agent-pr-metadata` when configuring PR templates, PR update comments, or AI review comments to disclose agent/model/run metadata outside commit messages.
- Use `open-code-review-setup` when creating a new repository or onboarding an existing repo to automated AI code review (OCR), or when OCR reviews are not running on PRs.
- Use `external-pr-style` before opening any PR against a repo we don't own.
- Use `resolving-merge-conflicts` when you need to resolve an in-progress git merge/rebase conflict.
- Use `wizard` when a manual procedure needs a human to click through a dashboard or enter credentials — generates a guided script instead of leaving `hitl-blocker`'s bare issue description to figure out alone.
- Use `git-guardrails-claude-code` to set up or audit the PreToolUse hook that blocks force-push, direct push to main/master/staging, `reset --hard`, `clean -f/-fd`, `branch -D`, and bare `checkout .`/`restore .`.
- Use `write-prompt-guide` when a skill pack needs a user-facing `PROMPT_GUIDE.md` telling people what to type to get a good run out of it.
- Use `handover` when context crosses an agent or session boundary, when only 5-10% of the session limit remains with work unfinished, or when context usage passes 40% on unfinished multi-step work.

## Summary

- Keep implementation agents issue-scoped to avoid context bloat.
- Mark an issue as picked or claimed before an agent starts work on it.
- Define acceptance criteria and verification before implementation.
- Run tests only against disposable storage or a dedicated test database; never staging, production, customer, demo, or shared operational databases.
- Prefer a fresh agent per issue by default.
- Require independent review with reviewer model/effort chosen by the PR's risk and complexity, and preserve automation/assistance traceability in merged PRs.
