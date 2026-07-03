---
name: subagent-pipeline
description: Run a cold-start implementer, reviewer, and fixer subagent chain for one issue, gated by CI, ending in a staging PR. Use when subagent delegation is authorized and the issue is non-trivial.
---

# Subagent Pipeline

Use this to execute one issue end to end with independent, cold-start subagents instead of one agent implementing and self-reviewing.

## Why Cold-Start

An agent that wrote the code cannot judge its own intent objectively. A fresh reviewer agent that has only the issue and the diff can only judge what the code does, not what the implementer meant. That gap is where bugs hide. Do not let the implementer review its own PR.

## Preconditions

- The issue exists and is claimed (`picked by agent` or the project's equivalent label) before any subagent starts.
- Check the issue's stated dependencies. If a blocking issue is still open, resolve it first or get explicit sign-off to build against a stub.
- Confirm which branch is actually current. If the local checkout is behind the deploy target (for example a solo-maintained `staging` that lags a local feature branch), branch the worktree from the remote target branch, not from the locally checked-out branch.

## Workflow

1. **Implementer subagent** — cold start, full write access, own git worktree per issue (for example `/tmp/<repo>-issue-<n>`), branched from the target base branch. Give it: the issue body, the base-branch commit to branch from, relevant existing conventions and file paths already discovered by prior research, explicit out-of-scope boundaries, and the exact PR target branch. It writes code, writes or updates tests, commits without AI co-author lines, pushes, and opens a PR against the base branch (`staging`, or `main` if no staging exists). It reports the PR URL, files touched, and anything it was unsure about.
2. **Reviewer subagent** — separate cold start. Choose the reviewer model and reasoning effort by the PR's risk and complexity: cheaper/faster settings for simple changes; stronger/higher-effort settings for complex, security-sensitive, payment, auth, database, or production-critical changes. Give it only the PR number, repo, and instruction to read the diff and the linked issue itself — do not hand it the implementer's rationale or your own analysis; a reviewer that inherits the implementer's framing stops being independent. Have it verify claims instead of trusting them: read the actual dependency/contract code the PR consumes (for example, the exact query params a signed URL generator produces vs. what the consuming route expects), not just the diff in isolation. It must post real inline PR comments (`gh pr review` or `gh api .../pulls/{n}/comments`), not just summarize back to you — the next subagent reads GitHub, not this conversation. Label blocking findings explicitly (e.g. "Blocking") in the comment body, because `--request-changes` fails when the reviewing token is also the PR author, and `--comment` is the fallback in that case.
3. **Fixer subagent** — cold start, reads review comments via `gh api repos/.../pulls/.../comments`, works in the same worktree the implementer used (not a new one), addresses each finding, adds or updates tests, pushes follow-up commits to the same branch (no new PR).
4. **CI gate** — do not merge until CI is green on the PR. If CI is flaky, rerun once, then record the flake evidence and require human approval before proceeding.
5. **Merge** — auto-merge (`gh pr merge --squash --auto`) to `staging` once CI passes. Always require human approval before merging to `main`.
6. **Chain to the next issue** — if a second issue depends on this one, wait for the merge, refetch the base branch, and branch the next issue's worktree from the merged commit, not from the pre-merge state.

## Guardrails

- One worktree per issue. Never mix two issues' changes in the same worktree or branch.
- Give each subagent a self-contained prompt: file paths, exact conventions already found by research, and what's explicitly out of scope. A prompt that says "based on what we discussed, implement it" defeats the point of a cold start.
- The reviewer's job is to falsify the implementer's claims, not summarize them. If the implementer flagged its own risk, have the reviewer independently confirm whether it is real and blocking, rather than repeating the implementer's own assessment.
- If the reviewer finds a real defect, fix it before merge — do not merge on "mostly fine."
- Never skip the review step because the diff looks small. Skip subagent overhead only when the change is trivial by the project's own non-trivial-PR definition.
- Every subagent prompt must include the bail-out contract: if the subagent cannot finish (context exhaustion, blocked dependency, session limit), it writes a `handover`, posts it to the issue, and adds the `paused by agent` label instead of stopping silently.
