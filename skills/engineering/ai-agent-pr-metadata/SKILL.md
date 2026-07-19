---
name: ai-agent-pr-metadata
description: Add GitHub-visible AI agent and AI code-review metadata and exact agent labels without adding AI attribution to commits, and scope Alibaba/Open Code Review's review surface to control LLM token spend. Use when configuring PR templates, issue/PR labels, PR creation commands, PR update comments, or Alibaba Code Review/open code review workflows to disclose the implementing agent, review tool, LLM model, run URL, or to add/tune a `.opencodereview/rule.json`.
---

# AI Agent PR Metadata

Use this when a repository needs traceable AI assistance metadata in GitHub while keeping commit history human-authored and attribution-free.

## Rules

- Commit attribution follows `system-level/core.md` (Git: no AI co-author metadata unless explicitly required). This skill governs where the traceable detail goes instead: PR bodies, PR comments, and PR review bodies only.
- Never guess the model name. Read the authoritative resolved model+version from the runtime or orchestrator; a product alias is not evidence of a model ID.
- Include a run URL when the work was produced by GitHub Actions or another traceable runner.
- Public issues, PRs, comments, and review records must never include credential values or local credential-file paths. Use `Credential details: [redacted]` instead.

## Agent Labels

- Apply an additive `agent:<model+version>-<effort>-<role>` label to the claimed issue and its PR only after the runtime or orchestrator has supplied the resolved model+version.
- Use that resolved identifier and declared effort exactly. Do not construct a label from an alias such as `gpt5`.
- Never replace the resolved model version or declared effort with an alias or a stronger/weaker value.
- Create the label before applying it if it does not already exist, and never remove other agents' `agent:*` labels.
- Example: `gpt5.6-terra` at `medium` effort as the implementer requires `agent:gpt5.6-terra-medium-implementer`.

If the resolved model ID is unavailable, do not create an agent-role label. Record `Resolved model ID: unavailable` and the runtime/orchestrator limitation in the PR body or a PR comment. This blocks automatic label creation; it does not authorize a substitute label.

Historical `agent:*` labels are audit data. Never relabel or delete them. Audit recent PRs by comparing their existing role labels with their recorded runtime metadata; for each confirmed invalid legacy label, open a focused follow-up issue that identifies the PR, evidence, and whether it indicates a correctness, security, or operational concern. Do not reopen PRs or mass-fix non-actionable review suggestions.

Before creating a new role label, validate the proposed exact label with the resolved runtime value. Do not pass an inferred alias as `--resolved-model-id`:

```bash
gh api "repos/$GITHUB_REPOSITORY/pulls/$PR_NUMBER/comments?per_page=100" > /tmp/ocr-review-comments.json
gh api "repos/$GITHUB_REPOSITORY/issues/$PR_NUMBER/comments?per_page=100" > /tmp/ocr-issue-comments.json
gh api "repos/$GITHUB_REPOSITORY/pulls/$PR_NUMBER/commits?per_page=100" > /tmp/pr-commits.json
python3 support/ai-engineering-workflow/scripts/verify-pr-governance.py \
  --head-sha "$GITHUB_SHA" \
  --review-comments /tmp/ocr-review-comments.json \
  --issue-comments /tmp/ocr-issue-comments.json \
  --pr-commits /tmp/pr-commits.json \
  --resolved-model-id "$AI_AGENT_RESOLVED_MODEL_ID" \
  --new-agent-label "agent:${AI_AGENT_RESOLVED_MODEL_ID}-${AI_AGENT_EFFORT}-${AI_AGENT_ROLE}"
```

## PR Template

Add or update `.github/pull_request_template.md`:

```md
## Agent Metadata

Implementation/update agent:
- Name: <!-- e.g. Claude Sonnet 5 Medium, Codex GPT-5.6 Terra Medium, or N/A -->
- Resolved model ID: <!-- Runtime/orchestrator value, or unavailable with limitation below -->
- Metadata limitation: <!-- Why the ID is unavailable, or N/A -->
- Verified agent labels: <!-- New labels created for this PR; comma-separated, or N/A -->
- Legacy agent labels: <!-- Pre-existing retained audit labels; comma-separated, or N/A -->
- Run: <!-- GitHub Actions run URL, local session reference, or N/A -->

Code review agent:
- Tool: alibaba-code-review
- LLM: <!-- e.g. qwen-coder-plus, or N/A if not run -->
- Run: <!-- GitHub Actions run URL, local session reference, or N/A -->
```

## Alibaba Code Review

End every Alibaba Code Review PR review with:

```md
---
Review metadata:
- Reviewer: alibaba-code-review
- LLM: ${ALIBABA_CODE_REVIEW_MODEL}
- Run: ${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}
```

If the review tool cannot customize its prompt or footer, wrap the generated review body before posting it with `gh pr review`.

### Cost scoping with `.opencodereview/rule.json`

`alibaba/open-code-review` runs an agentic tool-use loop per changed file (`code_search`, `file_read`, `file_read_diff`, then `code_comment`) — request/tool-call count scales with codebase exploration, not just diff size. A small diff across several files can still burn hundreds of thousands of input tokens if the agent goes hunting for context on every file. The action does not expose a tool-call or token budget flag, but it auto-discovers `<repoDir>/.opencodereview/rule.json` at review time (no workflow change needed — priority chain: `--rule` flag > project config > global config > built-in defaults).

Commit a project-level rule file to cut spend without losing coverage on files that matter:

```json
{
  "rules": [
    {
      "path": "tests/**/*.php",
      "rule": "Review test correctness, coverage of edge cases, and whether assertions match the intended behavior. Only inspect the implementation file directly under test when necessary — avoid broad codebase exploration for test files.",
      "merge_system_rule": true
    }
  ],
  "exclude": [
    "vendor/**",
    "node_modules/**",
    "**/dist/**",
    "**/build/**",
    "storage/**",
    "*.lock"
  ]
}
```

- `exclude` removes generated/vendored/build-artifact paths from review scope entirely — fewer files reviewed means fewer exploratory tool-call rounds.
- A scoped `rule` entry (merged with the built-in system rule via `merge_system_rule: true`) steers the agent toward the specific file instead of open-ended `code_search`, without dropping the file from review.
- Built-in default excludes already cover common test-file naming for Go/Java/JS/TS/Rust/Ruby (`**/*_test.go`, `**/*.spec.ts`, `**/__tests__/**`, etc.) — they do **not** cover PHPUnit/Pest's `*Test.php` convention, so PHP repos need an explicit rule/exclude decision for `tests/**`.
- Verify a rule matches before relying on it: `ocr rules check --rule .opencodereview/rule.json <path>` (no LLM call, free).
- After changing the rule file, compare the next run's `tool_calls`/`input_tokens` in the OCR result JSON (printed in the workflow log under `=== OCR result ===`) against a prior baseline run to confirm spend actually dropped.

## PR Updates

When an agent pushes updates after PR creation, post a PR comment:

```bash
gh pr comment "$PR_NUMBER" --repo "$GITHUB_REPOSITORY" \
  --body "AI Agent update: ${AI_AGENT_NAME} pushed ${GITHUB_SHA}. Run: ${RUN_URL}"
```

## Final OCR Disposition Gate

After the final push, wait for OCR and CI to settle. Fetch the latest-head OCR comments and PR conversation, then run the deterministic gate before merging:

```bash
gh pr checks "$PR_NUMBER" --repo "$GITHUB_REPOSITORY" --watch
gh api "repos/$GITHUB_REPOSITORY/pulls/$PR_NUMBER/comments" --paginate > /tmp/ocr-review-comments.json
gh api "repos/$GITHUB_REPOSITORY/issues/$PR_NUMBER/comments" --paginate > /tmp/ocr-issue-comments.json
gh api "repos/$GITHUB_REPOSITORY/pulls/$PR_NUMBER/commits?per_page=100" > /tmp/pr-commits.json
python3 support/ai-engineering-workflow/scripts/verify-pr-governance.py \
  --head-sha "$GITHUB_SHA" \
  --review-comments /tmp/ocr-review-comments.json \
  --issue-comments /tmp/ocr-issue-comments.json \
  --pr-commits /tmp/pr-commits.json
```

Every OCR inline comment on the latest head uses one PR comment with this exact record:

```md
<!-- ocr-disposition:COMMENT_ID -->
Disposition: fixed|deferred|declined
Reason: One concise sentence that preserves the decision.
```

Use no repeated fields or other nonblank text in that comment.

Open Code Review emits latest-head inline findings as `github-actions[bot]` comments with an `<!-- ocr-... -->` marker. The gate fails on an undispositioned latest-head OCR finding. Only repository owners, members, or collaborators can record a disposition. Every disposition requires a one-sentence reason; a comment explicitly marked `Blocking:` must be `fixed`. Use that marker only for correctness, security, data integrity, or acceptance-criteria findings. Style, wording, speculative defensive suggestions, and refactor preferences may be deferred or declined with a record, rather than generating bulk churn.

The `OCR disposition gate` workflow rechecks after Open Code Review completes and whenever a PR comment is created or edited. An active repository ruleset must require its exact `OCR disposition gate` status context on the default branch; do not rely on an agent manually running the command above. The gate accepts retained labels only when they are present in the base-ref `support/ai-engineering-workflow/legacy-agent-labels.json` audit baseline and recorded as legacy data. It validates every other label against the resolved model ID and rejects any unrecorded agent label. Never add a legacy label in the PR body to bypass this check.

## Verification

- Confirm `git log --format=%B -n 5` has no `Co-Authored-By` or AI attribution lines.
- Confirm the claimed issue and PR both contain the exact `agent:<model+version>-<effort>-<role>` label.
- Confirm the PR records the runtime/orchestrator-resolved model ID; if unavailable, confirm no new agent-role label was created and the limitation is recorded.
- Confirm the PR body contains `Agent Metadata`.
- Confirm the Alibaba review body contains `Review metadata` with the actual LLM model.
- Run the final OCR disposition gate after the last push and before merge.
