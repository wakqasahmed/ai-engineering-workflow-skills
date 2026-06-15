---
name: workflow-handoff
description: Create a compact handoff when context must cross an agent, session, or blocked state. Use when work is incomplete and non-obvious state must be preserved.
---

# Workflow Handoff

Use handoff only when continuity is needed.

## Include

- Current objective
- Current branch/worktree/PR/issue
- Completed changes
- Verification already run
- Failing or blocked commands
- Open decisions
- Next concrete action

## Exclude

- Long chat history
- Repeating code that is already in the repo
- Completed work that is obvious from merged PRs

## Guardrails

- Keep the handoff short enough for a fresh agent to use immediately.
- Prefer links to issues, PRs, files, and commands over prose.
