# Changelog

All notable changes to this workflow repository should be documented here.

The goal is transparency over time: what changed, why it changed, and when the workflow evolved.

## 2026-07

### Added

- `ai-agent-pr-metadata` skill for keeping AI agent, review tool, LLM model, and run metadata visible in PR bodies/comments/reviews without adding AI attribution to commit messages (#28)
- `subagent-pipeline` skill codifying the cold-start implementer/reviewer/fixer chain, CI gate, and staging auto-merge rule used for issue execution
- `roast` skill: a 6-persona adversarial council plus Judge verdict for pressure-testing a new idea before it enters the delivery pipeline, under a new `skills/product/` category
- `to-prd` skill so the dangling `to-prd` references in `AGENTS.md`, `CLAUDE.md`, `system-level/core.md`, `README.md`, and `AI_ENGINEERING_WORKFLOW.md` resolve to an in-repo skill; it produces a short PRD-shaped spec (problem, goal, non-goals, success criteria) that feeds `decompose-to-issues`, distinct from `clarify-work`'s terminology/scope clarification (#38)

### Changed

- `to-prd` now synthesizes conversation and repository context into a concise product-and-engineering spec, reuses the highest existing test seam, publishes to the detected issue tracker, gates `ready-for-agent` on resolved blockers, and hands off cleanly to `decompose-to-issues` (#45)
- `review-gate` and `subagent-pipeline` now draw an explicit line between mechanical checks (lint, formatting, conventional style, straightforward static analysis — owned by Alibaba Code Review and CI, recorded via `ai-agent-pr-metadata`) and semantic review (requirements compliance, correctness, regressions, security/authorization, contract/integration risk, acceptance-test adequacy — owned by the independent reviewer). The reviewer must read Alibaba Code Review's and CI's output before its own pass and must not repeat resolved mechanical findings; it may revisit one only if it signals an unresolved correctness/security/data-loss/configuration/acceptance-criteria issue. CI remains a hard merge gate and this review does not replace or duplicate it (#31)

- renamed `handoff`/`workflow-handoff` to `handover` and merged in a stricter end-of-session template (chat-only output, running-state and background-process tracking, plan/task/memory sourcing order, anti-patterns); updated all root entrypoint references
- routed dangling `grill-with-docs`/`to-issues` references to the in-repo `clarify-work`/`decompose-to-issues` skills so a cold install has no missing skill dependencies
- reviewer model and reasoning effort are now chosen per PR by risk and complexity (was: always strongest practical); aligned `subagent-pipeline`, role contracts, and entrypoints with `AI_ENGINEERING_WORKFLOW.md`
- `handover` now triggers when 5-10% of the session limit remains or context usage passes 40% on unfinished work, publishes the handover to the linked issue, and adds a `paused by agent` label so half-done work is discoverable; fixed invalid tab in `argument-hint` and removed `disable-model-invocation` so agents can self-invoke at the thresholds
- `subagent-pipeline` guardrails now require every subagent prompt to carry the bail-out contract (handover + issue comment + `paused by agent` label instead of stopping silently)
- replaced remaining `handoff` wording with `handover` outside user-utterance trigger synonyms
- optional skill prerequisites (`tdd`, `diagnose`, `simplify`, `security-review`) now map to the maintained `addyosmani/agent-skills` pack instead of scattered third-party repos

## 2026-06

### Added

- installable `skills/` layout with short independent workflow skills
- Claude plugin metadata plus skill listing and plugin-path validation scripts
- safe user-level installer for `AGENTS.md` and `.claude/CLAUDE.md`, with dry-run, backups, conflict reporting, and CI coverage
- execution-discipline rules for assumptions, success criteria, scoped diffs, newly unused code, and trivial-change judgment
- proactive `tdd`, `simplify`, `diagnose`, and `security-review` trigger guidance
- optional skill prerequisite and user-level instruction synchronization guidance
- CI check that keeps the root agent entrypoints aligned
- extremely concise reporting guidance
- standing authorization guidance for cold-start reviewer subagents
- scale-adaptive planning tracks, clean-baseline checks, two-stage review, and manual acceptance walkthrough guidance
- instruction hygiene, deterministic enforcement, and production dependency checkpoints
- issue claiming before agent execution to reduce duplicate work
- guidance to use the strongest practical model and reasoning effort for independent reviewer agents

## 2026-05

### Added

- initial public workflow playbook
- root agent entrypoints via `AGENTS.md` and `CLAUDE.md`
- `system-level/core.md` for invariant operating rules
- `AI_ENGINEERING_WORKFLOW.md` for the full workflow, issue shape, PR shape, risk levels, and failure paths

### Changed

- removed month-specific branding from core docs so the repository can evolve continuously
- moved version tracking from inline document text to this changelog
- narrowed the `Influences` section to reflect the repository's current contents instead of future technology-specific skill packs
