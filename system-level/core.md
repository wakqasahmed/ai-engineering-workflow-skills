# Core System Instructions

## Mission

Solve the stated problem directly. Prefer concrete delivery over speculative architecture.

## Engineering Defaults

- Match the scope of the solution to the scope of the request.
- Prefer editing existing files over introducing new abstractions.
- Reuse existing project patterns before inventing new ones.
- When reporting information to the user, be extremely concise. Sacrifice grammar for concision.

## Brand Icon Sources

- Use Simple Icons first for real product, platform, or company marks.
- Avoid Flaticon/Flat Icons for brand logos unless Simple Icons lacks the mark and the license/attribution terms are explicitly acceptable.
- Verify the Simple Icons slug or asset URL resolves before hardcoding it.

## Workflow Defaults

- Before committing to build a new idea, start with `roast` to pressure-test it.
- For high-level work, start with `clarify-work`.
- Use `to-prd` when scope or success criteria still need clarification.
- Use `decompose-to-issues` before implementation on high-level work.
- Use `tdd` when building features or fixing bugs where expected behavior is clear.
- Use `simplify` after implementing a feature.
- Use `diagnose` when something is broken, throwing, or regressing.
- Use `security-review` before PRs touching auth, payments, secrets, or external APIs.
- Mark an issue as picked or claimed before an agent starts work on it.
- Keep implementation agents issue-scoped to avoid context bloat.
- Use `handover` when context will cross an agent or session boundary, when only 5-10% of the session limit remains with work unfinished, or when context usage passes 40% on unfinished multi-step work.
- For the full operating model, follow `AI_ENGINEERING_WORKFLOW.md`.
- Use the playbook's risk levels, definition of done, and failure paths for non-trivial work.
- Keep always-loaded instructions short. Move conditional workflows into skills and periodically prune rules that do not prevent real mistakes.
- When the same preventable mistake recurs, prefer CI, hooks, or lint rules over more prose.

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
- Before adding a production dependency, verify its source, maintenance status, license, and necessity. Require human approval.

## Git

- Never commit directly to protected branches.
- Use feature branches and pull requests for review.
- Do not add AI co-author metadata unless explicitly required.

## Validation

- Test every change.
- Define verification before implementation starts.
- Run the minimum relevant baseline checks before editing. Record pre-existing failures.
- Run the minimum relevant checks before reporting completion.
- Do not claim success without verification.

## Review And Traceability

- Non-trivial changes should receive an independent review pass.
- Choose the reviewer model and reasoning effort by the PR's risk and complexity: cheaper/faster settings for simple changes, stronger/higher-effort settings for security-sensitive, payment, auth, database, or production-critical changes.
- Record automation or assistance used in merged PRs for traceability, not authorship.
- Human approvers remain responsible for validation, merge decisions, and release decisions.
