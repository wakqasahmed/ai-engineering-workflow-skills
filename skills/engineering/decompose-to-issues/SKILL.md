---
name: decompose-to-issues
description: Break high-level work into independently executable GitHub issues using vertical slices. Use when a plan, PRD, roadmap item, or vague feature needs issue-sized execution units.
---

# Decompose To Issues

Use decomposition as context control, not project-management ceremony.

## Workflow

1. Identify the user-visible or operational outcome.
2. Split by vertical slices that can be implemented, reviewed, and verified independently.
3. Put shared setup before dependent slices only when it unlocks multiple issues.
4. Mark dependencies explicitly.
5. Keep each issue small enough for a fresh agent to complete in one focused pass when possible.

## Issue Shape

Each issue should include:

- Problem
- Acceptance criteria
- Verification plan
- Expected test layers
- Constraints / non-goals
- Links and relevant files
- Risk level

## Guardrails

- Avoid horizontal slices like "build backend" and "build frontend" unless the architecture truly requires it.
- Do not create issues that require inherited conversation context to understand.
- Create follow-up issues for scope discovered during implementation.
