# Evaluation Architecture and Coverage

This directory contains deterministic contract evaluations and model-outcome harnesses for skills in this repository.

## Two-Tier Evaluation Model

1. **Deterministic Contract Checks (Free, PR CI)**:
   - Run via `bash eval/<category>/<skill>/run-eval.sh --dry-run`.
   - Executed offline in a disposable, network-blocked workspace with synthetic fixtures.
   - Asserts non-negotiable written rules in `SKILL.md` and validates fixture schema, category splits, and disjoint tuning sets.
   - Does not spend model tokens and gates every pull request in `.github/workflows/entrypoint-sync.yml`.

2. **Gated Model-Outcome Harness (Manual Dispatch / Scheduled)**:
   - Run via `run_harness.py` in an isolated container with no network, no ambient credentials, and an empty home.
   - Runs 3 to 6 trials per scenario across `enabled` and `disabled` conditions.
   - Evaluates user-visible outcome deltas and safety thresholds (`is_safe()`), preventing regressions.

## Skill Evaluation Coverage Status

| Skill | Deterministic Contract Check | Model Harness Tracking | Notes |
|---|---|---|---|
| `changesets-release` | `eval/engineering/changesets-release/` | Built-in | Verified in CI |
| `clarify-work` | `eval/engineering/clarify-work/` | Built-in | Verified in CI |
| `decompose-to-issues` | `eval/engineering/decompose-to-issues/` | Built-in | Verified in CI |
| `define-done` | `eval/engineering/define-done/` | Built-in | Verified in CI |
| `hitl-blocker` | `eval/engineering/hitl-blocker/` | Built-in | Verified in CI |
| `release-gate` | `eval/engineering/release-gate/` | Built-in | Verified in CI |
| `review-gate` | `eval/engineering/review-gate/` | Built-in | Verified in CI |
| `subagent-pipeline` | `eval/engineering/subagent-pipeline/` | Built-in | Verified in CI |
| `to-prd` | `eval/engineering/to-prd/` | Built-in | Verified in CI |
| `workflow-router` | `eval/engineering/workflow-router/` | Built-in | Verified in CI |
| `write-prompt-guide` | `eval/engineering/write-prompt-guide/` | Built-in | Verified in CI |
| `external-pr-viability` | `eval/engineering/external-pr-viability/` | Built-in | Verified in CI |
| `ai-agent-pr-metadata` | `eval/engineering/ai-agent-pr-metadata/` | Built-in | Verified in CI |
| `roast` | `eval/product/roast/` | Built-in | Verified in CI |
| `handover` | `eval/productivity/handover/` | Built-in | Verified in CI |
| `diagnose` | Intentional deferral | [#57](https://github.com/wakqasahmed/ai-engineering-workflow-skills/issues/57) | Upstream-adapted diagnostic loop |
| `external-pr-style` | Intentional deferral | [#59](https://github.com/wakqasahmed/ai-engineering-workflow-skills/issues/59) | Natural prose guidance |
| `git-guardrails-claude-code` | Intentional deferral | [#60](https://github.com/wakqasahmed/ai-engineering-workflow-skills/issues/60) | Hook installation procedure |
| `open-code-review-setup` | Intentional deferral | [#61](https://github.com/wakqasahmed/ai-engineering-workflow-skills/issues/61) | OCR setup workflow |
| `resolving-merge-conflicts` | Intentional deferral | [#62](https://github.com/wakqasahmed/ai-engineering-workflow-skills/issues/62) | Conflict resolution procedure |
| `tmux-orphaned-socket` | Intentional deferral | [#63](https://github.com/wakqasahmed/ai-engineering-workflow-skills/issues/63) | Low-level socket recovery |
| `wizard` | Intentional deferral | [#64](https://github.com/wakqasahmed/ai-engineering-workflow-skills/issues/64) | Procedural bash generator |
| `writing-for-agents` | Intentional deferral | [#65](https://github.com/wakqasahmed/ai-engineering-workflow-skills/issues/65) | Authoring reference |
