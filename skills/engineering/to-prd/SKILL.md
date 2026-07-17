---
name: to-prd
description: Turn a fuzzy, high-level ask into a short PRD-shaped spec with goals, non-goals, and success criteria before decomposition. Use when the work still needs product framing, decision-making, or success criteria clarification, not just terminology or scope clarification.
---

# To PRD

Use this after `clarify-work` has resolved terminology and blocking unknowns, when the work
still lacks a product-level frame: what it's for, what's explicitly out of scope, and how
success is measured. Feed the result into `decompose-to-issues`.

Skip this for narrow or already issue-shaped work — go straight to `decompose-to-issues`.

## Workflow

1. State the problem being solved and who it's for, in plain language.
2. State the goal as an observable outcome, not an implementation.
3. List non-goals: adjacent work explicitly out of scope for this effort.
4. Write success criteria that can be verified, not just described.
5. Record open product decisions that still need an owner's call before implementation.
6. Note constraints that shape the solution (deadlines, compliance, existing contracts).

## Output

- Problem
- Goal
- Non-goals
- Success criteria
- Open product decisions
- Constraints

## Guardrails

- Do not restate `clarify-work` output verbatim; add product framing it doesn't cover.
- Do not include an implementation plan or task breakdown — that's `decompose-to-issues`.
- Do not invent success criteria the requester hasn't validated; ask when genuinely unknown.
- Keep it short. A PRD here is a working spec, not a formal document.
