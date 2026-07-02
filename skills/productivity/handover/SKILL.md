---
name: handover
description: Use when the user says "handoff", "hand off", "session handoff", "wrap up session", "handover summary", or wants a structured end-of-session summary before clearing context, and whenever context must cross an agent, session, or blocked state. Produces a handover covering decisions, shipped changes, key files, running state, verification, deferrals, and open questions so a fresh agent can continue seamlessly.
---

# Handover

Produce a compact, structured summary so a fresh agent or session can continue without re-deriving what already happened. This is a **context-handoff artifact**, not a status report — the audience is the next agent, not a stakeholder.

## When to invoke

- Continuity is needed: context is about to cross an agent, session, or clear boundary, or work is blocked and non-obvious state must be preserved.
- User says: "handoff", "hand off", "session handoff", "wrap up session", "handover summary", "let's wrap up", or a near-equivalent.
- Also invoke proactively if the user signals they're about to clear context without having asked for a handover yet.

Skip it when work is already complete and legible from the issue, PR, and tests — don't create a handover for its own sake.

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
4. Output in chat by default. Only write it to a file or memory if the user explicitly asks for that — this skill's job is the summary, not persistence.

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

- Chat output only, unless explicitly asked to persist it. Never silently write it to a file or update memory.
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
