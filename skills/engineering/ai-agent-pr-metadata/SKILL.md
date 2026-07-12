---
name: ai-agent-pr-metadata
description: Add GitHub-visible AI agent and AI code-review metadata without adding AI attribution to commits. Use when configuring PR templates, PR creation commands, PR update comments, or Alibaba Code Review/open code review workflows to disclose the implementing agent, review tool, LLM model, and run URL.
---

# AI Agent PR Metadata

Use this when a repository needs traceable AI assistance metadata in GitHub while keeping commit history human-authored and attribution-free.

## Rules

- Keep commit messages free of AI co-author lines and AI attribution.
- Put agent details in PR bodies, PR comments, and PR review bodies only.
- Never guess the model name. Read it from workflow vars, orchestration config, or an explicit user-provided value.
- Include a run URL when the work was produced by GitHub Actions or another traceable runner.

## PR Template

Add or update `.github/pull_request_template.md`:

```md
## Agent Metadata

Implementation/update agent:
- Name: <!-- e.g. Claude Sonnet 5 Medium, Codex GPT-5 High, or N/A -->
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

## PR Updates

When an agent pushes updates after PR creation, post a PR comment:

```bash
gh pr comment "$PR_NUMBER" --repo "$GITHUB_REPOSITORY" \
  --body "AI Agent update: ${AI_AGENT_NAME} pushed ${GITHUB_SHA}. Run: ${RUN_URL}"
```

## Verification

- Confirm `git log --format=%B -n 5` has no `Co-Authored-By` or AI attribution lines.
- Confirm the PR body contains `Agent Metadata`.
- Confirm the Alibaba review body contains `Review metadata` with the actual LLM model.
