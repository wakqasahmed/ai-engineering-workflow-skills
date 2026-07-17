---
name: ai-agent-pr-metadata
description: Add GitHub-visible AI agent and AI code-review metadata and exact agent labels without adding AI attribution to commits, and scope Alibaba/Open Code Review's review surface to control LLM token spend. Use when configuring PR templates, issue/PR labels, PR creation commands, PR update comments, or Alibaba Code Review/open code review workflows to disclose the implementing agent, review tool, LLM model, run URL, or to add/tune a `.opencodereview/rule.json`.
---

# AI Agent PR Metadata

Use this when a repository needs traceable AI assistance metadata in GitHub while keeping commit history human-authored and attribution-free.

## Rules

- Commit attribution follows `system-level/core.md` (Git: no AI co-author metadata unless explicitly required). This skill governs where the traceable detail goes instead: PR bodies, PR comments, and PR review bodies only.
- Never guess the model name. Read it from workflow vars, orchestration config, or an explicit user-provided value.
- Include a run URL when the work was produced by GitHub Actions or another traceable runner.

## Agent Labels

- Apply an additive `agent:<model+version>-<effort>-<role>` label to the claimed issue and its PR.
- Use the resolved model identifier and declared effort exactly.
- Never replace the resolved model version or declared effort with an alias or a stronger/weaker value.
- Create the label before applying it if it does not already exist, and never remove other agents' `agent:*` labels.
- Example: `gpt5.6-terra` at `medium` effort as the implementer requires `agent:gpt5.6-terra-medium-implementer`.

## PR Template

Add or update `.github/pull_request_template.md`:

```md
## Agent Metadata

Implementation/update agent:
- Name: <!-- e.g. Claude Sonnet 5 Medium, Codex GPT-5.6 Terra Medium, or N/A -->
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

## Verification

- Confirm `git log --format=%B -n 5` has no `Co-Authored-By` or AI attribution lines.
- Confirm the claimed issue and PR both contain the exact `agent:<model+version>-<effort>-<role>` label.
- Confirm the PR body contains `Agent Metadata`.
- Confirm the Alibaba review body contains `Review metadata` with the actual LLM model.
