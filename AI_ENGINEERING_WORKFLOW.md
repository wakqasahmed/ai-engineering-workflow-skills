# AI Engineering Workflow

My current public AI-assisted engineering workflow.

This repository has two audiences:

- humans adopting the workflow in full or in part
- agents executing the workflow as operating instructions

The workflow is descriptive as a public playbook, but the files under `system-level/`, `AGENTS.md`, and `CLAUDE.md` are directive when loaded by an agent.

## Core Principles

- Decomposition is not just project management. It is a context-quality control mechanism for agents.
- Smaller, issue-scoped execution helps agents stay sharp, reduces context bloat, and improves reliability.
- For high-level work, clarify first, then decompose, then execute issue by issue.
- For a new idea, not yet a scoped piece of work, pressure-test it with `roast` before it enters this pipeline at all.
- Human owners remain responsible for what gets merged, released, and shipped.

## Default Workflow

### Planning Tracks

- Quick: trivial or narrow changes. Execute directly with focused verification.
- Standard: non-trivial issue with acceptance criteria, verification plan, and risk level.
- Deep: ambiguous, architectural, or cross-cutting work. Clarify decisions, use a PRD when helpful, then decompose before implementation.

### 1. Clarify

- Use `clarify-work` for high-level tasks.
- Resolve fuzzy terminology, unclear requirements, and hidden constraints before implementation starts.

### 2. Decompose

- Use `to-prd` when the work still needs product framing, decision-making, or success criteria clarification.
- Use `decompose-to-issues` before implementation on high-level work.
- Treat the issue as the preferred execution boundary for an implementation agent.

### 3. Execute

- Before an agent starts work on an issue, mark the issue as claimed or picked in the issue tracker so other agents do not duplicate the work. Use the team's standard label or status, for example `picked by agent`.
- Use a fresh agent per issue by default.
- Reuse the same agent only for a genuinely small, narrow execution loop where context is still clean.
- Keep each issue small enough to complete and verify in one focused pass when possible.
- Run the minimum relevant baseline checks before editing and record pre-existing failures.
- Before non-trivial implementation, state assumptions, ambiguities, and the simplest viable approach.
- Keep every changed line traceable to the issue acceptance criteria.
- Remove imports, variables, and functions made unused by the change. Mention unrelated dead code without deleting it.

Agent role contracts:

- Implementer: reads the issue and relevant project docs, writes code, writes or updates tests, runs the named verification, and opens the PR.
- Reviewer: model and reasoning effort chosen by the PR's risk and complexity. Reads only the issue, acceptance criteria, and PR diff unless more context is explicitly needed. Posts concrete findings that identify the failing behavior, risk, or missing proof.
- Fixer: reads review comments, addresses each actionable finding, adds or updates tests when needed, reruns verification, and pushes follow-up commits.
- Human owner: resolves product tradeoffs, approves merge and release decisions, and remains accountable for shipped behavior.

### 4. Verify

- Before implementation, define acceptance criteria and a verification plan in the issue itself.
- Name the expected test layers when knowable: unit, integration, e2e, manual validation.
- Prefer writing focused tests first when expected behavior is already clear.
- For user-visible medium-risk and high-risk changes, name and perform the relevant manual acceptance walkthrough.
- At minimum, no change is complete until the relevant automated or manual checks have been run.

Definition of done:

- Acceptance criteria are satisfied.
- Relevant tests are added or updated, or the issue states why automated tests are not appropriate.
- The minimum relevant checks have been run and named.
- Non-trivial work has passed independent review.
- Risk, rollout, and rollback notes are present when the change warrants them.

### 5. Review

- Open a pull request for non-trivial changes.
- Run `simplify` after feature implementation and before independent review.
- Run `security-review` before PRs touching auth, payments, secrets, or external APIs.
- Require an independent review pass that is not just the implementing agent re-reading its own diff.
- When agents support delegation and the human owner has granted standing authorization, spawn a cold-start reviewer subagent without waiting for per-task authorization.
- That review can come from another human, another fresh agent, or a review tool such as Greptile.
- For medium-risk and high-risk changes, review spec compliance against acceptance criteria before reviewing code quality, regressions, security, and maintainability.
- Apply review findings before merge.

### 6. Release

- Run CI/CD as appropriate for the repository.
- Use staging and HITL validation for risky changes, especially user-facing, auth, payment, data-sensitive, or workflow-critical work.
- Deploy to production only after the relevant review and validation gates are satisfied.
- Final changelog assembly can happen later, but each non-trivial PR should include a short release-note candidate.
- For medium-risk and high-risk changes, state the rollback path and the production health check before release.

### 7. Handover When Needed

- Use `handover` when context will cross an agent or session boundary, when work is blocked, when only 5-10% of the session limit remains with work unfinished, when context usage passes 40% on unfinished multi-step work, or when non-obvious state must be preserved.
- Publish the handover to the linked issue and add the `paused by agent` label so a fresh agent can find and resume half-done work.
- Do not create handovers for work that is already complete and legible from the issue, PR, and tests.

## Decision Rules

- Use the quick, standard, or deep planning track that honestly fits the work.
- Use `to-prd` conditionally, not universally.
- Use `decompose-to-issues` by default for high-level work.
- Claim or mark an issue as picked before execution starts.
- Prefer fresh agent per issue by default, with a small-issue exception.
- For each PR review, choose the model and reasoning effort based on the PR’s risk and complexity.
- Use cheaper/faster settings for simple changes.
- Use stronger/higher-effort settings for complex, security-sensitive, payment, auth, database, or production-critical changes.
- When appropriate, run independent review passes focused on correctness, security, performance, and regressions.
- Use the appropriate model and effort level per PR for independent review passes.
- Use risk-based staging and HITL, not universal staging for every change.
- Treat context-bloat concerns as a heuristic, not a numeric rule.

## Risk Levels

Use the lowest risk level that honestly fits the change.

- Low risk: copy changes, local styling fixes, test-only changes, or a narrow bug fix with no business-rule change. Require focused verification.
- Medium risk: user-visible behavior, business logic, data handling, integrations, CI, or meaningful multi-file changes. Require focused tests, independent review, and rollout notes.
- High risk: auth, payments, permissions, secrets, migrations, deployment, infrastructure, tenant data, or irreversible operations. Require independent review, CI, staging or HITL validation, rollback notes, and a named production health check.

## Issue Template

Every implementation issue should include:

- `Problem`
- `Acceptance Criteria`
- `Verification Plan`
- `Expected Test Layers`
- `Constraints / Non-goals`
- `Links`
- `Relevant Files / Docs`
- `Risk Level`

Guidance:

- Keep acceptance criteria short, testable, and sufficient to define done.
- The verification plan should state how the work will be proven correct.
- Expected test layers help align proof cost with change risk.
- Relevant files and docs give fresh agents enough context without carrying over stale conversation history.

## PR Template

Every non-trivial PR should include:

- `Summary`
- `Linked Issue`
- `Acceptance Criteria Checklist`
- `Verification Performed`
- `Automation / Assistance Used`
- `Risk / Rollout Notes`
- `Rollback Notes`
- `Release-Note Candidate`

## Non-Trivial PRs

Treat a PR as non-trivial if any of these are true:

- it changes user-visible behavior
- it changes business logic or data handling
- it touches auth, payments, permissions, integrations, CI/CD, or deployment
- it spans multiple files in a way that changes behavior, coupling, or ownership boundaries
- it needs reviewer explanation beyond a tiny local fix
- it would be useful to mention in a release note, incident review, or future audit

Do not treat generated formatting, mechanical renames, or test fixture updates as non-trivial only because they touch multiple files. Do treat a one-line change as non-trivial if it changes security, billing, permissions, data integrity, deployment, or user-visible behavior.

## Traceability And Accountability

Every merged PR should record the automation or assistance used during the change. This is for traceability, not authorship and not accountability transfer. The human owner remains responsible for validating correctness, interpreting review output, and deciding what ships.

Recommended places to record this:

- PR description
- release notes

Do not rely on commit messages for this traceability. Do not add AI co-author lines or AI attribution to commits.

## Failure Paths

- When the same preventable failure recurs, prefer deterministic enforcement with CI, hooks, or lint rules over adding more instructions.
- If tests fail for unrelated reasons, capture the failing command and evidence, then decide whether the issue is blocked or whether a smaller verification still proves the change.
- If scope expands during implementation, stop and split the new work into a follow-up issue unless the expansion is required to satisfy the original acceptance criteria.
- If reviewer and implementer disagree, resolve against the issue acceptance criteria first and the product owner second. Do not merge unresolved correctness disputes.
- If CI is flaky, rerun once, then record the flake evidence and either fix the flake or require human approval before proceeding.
- If the issue cannot be completed in one focused pass, write a handover with current state, failing checks, open decisions, and next action, publish it to the issue, and add the `paused by agent` label.

## Context Packet For Fresh Agents

Each issue should give a fresh agent enough context to start without inheriting prior conversation state:

- problem statement and acceptance criteria
- relevant files, docs, domain terms, and prior decisions
- explicit non-goals
- expected test layers and exact verification commands when known
- risk level and rollout constraints

## Instruction Hygiene

- Keep always-loaded instructions short. Move conditional workflows into skills or referenced playbooks.
- Periodically prune instructions that do not prevent real mistakes.
- After changing global or project instructions, start a fresh agent session and verify which instruction files loaded and their precedence order.

## Dependency Checkpoint

Before adding a production dependency:

- verify the package source and maintainer legitimacy
- check maintenance status and license
- confirm the dependency is necessary
- require human approval

## Adoption Modes

- Adopt the full workflow if you want structured planning, issue-scoped execution, and release discipline.
- Adopt only the planning layer if your main problem is fuzzy requirements.
- Adopt only the review and traceability layer if your team already has a strong implementation workflow.
- Adopt only the handover discipline if context continuity is your main bottleneck.

## Influences

- Matt Pocock's observations around keeping AI work scoped tightly enough to preserve sharpness
- tool-assisted planning and issue decomposition workflows
- independent review practices, including tools such as Greptile
- real-world use of issue-scoped execution, verification-first delivery, and traceable AI assistance
