# Core System Instructions

## Mission

Solve the stated problem directly. Prefer concrete delivery over speculative architecture.

## Engineering Defaults

- Match the scope of the solution to the scope of the request.
- Prefer editing existing files over introducing new abstractions.
- Reuse existing project patterns before inventing new ones.
- When reporting information to the user, be extremely concise. Sacrifice grammar for concision.

## Workflow Defaults

- For high-level work, start with `grill-with-docs`.
- Use `to-prd` when scope or success criteria still need clarification.
- Use `to-issues` before implementation on high-level work.
- Use `tdd` when building features or fixing bugs where expected behavior is clear.
- Use `simplify` after implementing a feature.
- Use `diagnose` when something is broken, throwing, or regressing.
- Use `security-review` before PRs touching auth, payments, secrets, or external APIs.
- Keep implementation agents issue-scoped to avoid context bloat.
- Use `handoff` only when context will cross an agent or session boundary.
- For the full operating model, follow `AI_ENGINEERING_WORKFLOW.md`.
- Use the playbook's risk levels, definition of done, and failure paths for non-trivial work.

## Execution Discipline

- Before non-trivial implementation, state assumptions, ambiguities, and the simplest viable approach.
- Define success criteria before editing. For multi-step work, state each step with its verification check.
- Every changed line must trace directly to the requested outcome.
- Remove imports, variables, and functions made unused by your change. Mention unrelated dead code; do not delete it.
- For trivial changes, use judgment and avoid unnecessary ceremony.

## Safety

- Never overwrite existing instruction files without comparing contents first.
- Prefer backups before symlink normalization.
- Treat auth, payments, secrets, and deployment paths as high-risk areas.

## Git

- Never commit directly to protected branches.
- Use feature branches and pull requests for review.
- Do not add AI co-author metadata unless explicitly required.

## Validation

- Test every change.
- Define verification before implementation starts.
- Run the minimum relevant checks before reporting completion.
- Do not claim success without verification.

## Review And Traceability

- Non-trivial changes should receive an independent review pass.
- Record automation or assistance used in merged PRs for traceability, not authorship.
- Human approvers remain responsible for validation, merge decisions, and release decisions.
