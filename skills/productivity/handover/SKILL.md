---
name: handover
description: Compact the current conversation into a handover document a fresh agent can pick up and continue seamlessly. Invoke when only 5-10% of the session limit remains, when context usage passes 40% (less than 60% of the context window remaining), when context is about to cross an agent or session boundary, when work is blocked, or on explicit user request — never haphazardly mid-task. Covers decisions, shipped changes, key files, running state, verification, deferrals, and open questions.
argument-hint: "[what the next session will focus on]"
---

# Handover

Produce a compact, structured summary so a fresh agent or session can continue without re-deriving what already happened. This is a **context-handover artifact**, not a status report — the audience is the next agent, not a stakeholder. Save to the temporary directory of the user's OS - not the current workspace.

## When to invoke

- Only 5-10% of the session limit remains and the work is unfinished: pause the task at the next safe point and write the handover — do not run to the last token and stop silently.
- Context usage passes 40% of the window (less than 60% remaining) on unfinished multi-step work: hand over to a fresh session before context bloat degrades quality.
- Continuity is needed: context is about to cross an agent, session, or clear boundary, or work is blocked and non-obvious state must be preserved.
- User says: "handoff", "hand off", "handover", "hand over" "session handoff", "wrap up session", "handover summary", "let's wrap up", or a near-equivalent.
- Also invoke proactively if the user signals they're about to clear context without having asked for a handover yet.

Do not invoke haphazardly while ample context remains and the work is progressing. Skip it when work is already complete and legible from the issue, PR, and tests — don't create a handover for its own sake.

## How to produce it

1. Review the full conversation, not just the last few turns — handovers miss things when they only look at recent context.
2. Pull state from these sources, in order:
   - Any plan file referenced this session.
   - Task/todo list state — anything in progress or pending.
   - Background processes started this session — their IDs are load-bearing; the next agent can't rediscover them.
   - Files created or modified this session — you already know what you touched, don't re-grep to rediscover it.
   - Memory files written or updated this session.
   - Current branch/worktree/PR/issue.
   - Unresolved questions — things asked that never got a clear answer, or user asks that got deflected.
3. Do not audit the filesystem or git history to reconstruct this. It's a synthesis of this session, not a fresh investigation — no broad `git log`, no repo-wide greps "just to be sure."
4. Include a "suggested skills" section in the document, which suggests skills that the agent should invoke.
5. Do not duplicate content already captured in other artifacts (PRDs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.
6. Redact any sensitive information, such as API keys, passwords, or personally identifiable information.
7. If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.

## Publish to the issue

If the work traces to a GitHub issue or PR:

1. Comment on the issue with the absolute path of the handover file and the full handover content in the comment body — temp directories do not survive; the comment is the durable copy.
2. Add the label `paused by agent` (create it if missing). It marks half-done work waiting for pickup and pairs with `picked by agent`.
3. The agent that resumes the work removes `paused by agent`, applies `picked by agent`, and continues from the "Pick up here" line.

If no issue exists, report the handover file path in chat instead.

## Output template — use this structure every time

```
# Handover — <one-line title of what this session was about>

## Where it started
<2-3 sentences: what was asked, key framing or constraints that emerged>

## Decisions locked + what shipped
- <decision or change> — <why, and where it lives (absolute path if a file)>

## Key files for next session
- `<absolute path>` — <why the next agent should read this first>
- Plan file: `<path>` (if a plan drove the session)
- Memory files touched: `<paths>` — or "none"

## Running state
- Background processes: <IDs + what they are + how to stop them> — or "none"
- Dev servers / ports: <url + port> — or "none"
- Open worktrees / branches / PRs / issues: <paths, numbers> — or "none"

## Verification — how to confirm things still work
- `<command>` — <expected outcome>

## Deferred + open questions
- Deferred: <item> — <why pushed to later>
- Open: <question needing the user's input> — <context>

## Pick up here
<1-2 sentences: the single most likely next action for a fresh agent>
```

## Hard rules

- Never invent state. If a section has nothing to report, write "none" — don't omit the section; structure stability is the point.
- Absolute paths always — the next agent may have a different working directory.
- If a plan file drove the session, name it first under "Key files."
- Background process IDs are critical — if anything was started in the background, its ID and stop command must appear under "Running state."
- No emojis, no hype, no "great job" retrospective. Terse and concrete: paths, commands, IDs, decisions.

## Guardrails

- Keep it short enough for a fresh agent to use immediately — prefer links to issues, PRs, files, and commands over prose.
- Don't summarize the last 3 turns and call it a handover — review the whole session.
- Don't list files by relative path.
- Don't add a "what went well / what went poorly" retrospective — this isn't a retro.
- Don't recommend next steps beyond the single "Pick up here" line — the next agent decides.
