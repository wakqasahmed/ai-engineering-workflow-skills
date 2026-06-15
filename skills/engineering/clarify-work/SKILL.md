---
name: clarify-work
description: Clarify non-trivial engineering work before implementation by resolving ambiguity, terminology, constraints, and the smallest viable path. Use when a request is broad, fuzzy, architectural, cross-cutting, or has hidden product decisions.
---

# Clarify Work

Use this before implementation when the request is not already issue-sized.

## Workflow

1. Restate the outcome in one sentence.
2. Name assumptions and unknowns that can change the implementation.
3. Ask only blocking questions. Prefer 1-3 questions.
4. Identify the planning track: quick, standard, or deep.
5. State the smallest viable approach and non-goals.
6. Convert broad work into issue-shaped execution units when needed.

## Output

- Outcome
- Assumptions
- Open questions
- Suggested execution boundary
- Verification signal

## Guardrails

- Do not plan around hypothetical future requirements.
- Do not start implementation while key terms or ownership boundaries are unclear.
- Prefer `grill-with-docs` when project terminology or decisions need to be updated.
