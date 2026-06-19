---
name: setup-matt-pocock-skills
description: Sets up an `## Agent skills` block in AGENTS.md or CLAUDE.md and `docs/agents/` so the engineering skills know this repo's issue tracker, triage labels, and domain doc layout. Run before first use of issue decomposition, triage, diagnosis, TDD, architecture, or zoom-out skills when the repo lacks that context.
disable-model-invocation: true
---

# Setup Matt Pocock's Skills

Scaffold the per-repo configuration that the engineering skills assume.

## Explore

- `git remote -v` and `.git/config`
- `AGENTS.md` and `CLAUDE.md`
- `CONTEXT.md` and `CONTEXT-MAP.md`
- `docs/adr/` and any `src/*/docs/adr/`
- `docs/agents/`
- `.scratch/`

## Decide

Resolve these in order:

1. Issue tracker
2. Triage label vocabulary
3. Domain docs layout

## Write

- Update the existing `CLAUDE.md` if present, else `AGENTS.md`.
- Add or update one `## Agent skills` block.
- Write `docs/agents/issue-tracker.md`.
- Write `docs/agents/triage-labels.md`.
- Write `docs/agents/domain.md`.

## Guardrails

- Never create `AGENTS.md` when `CLAUDE.md` already exists.
- Update an existing `## Agent skills` block in place.
- Let users edit the draft before writing.
