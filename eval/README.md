# Evaluation Architecture and Coverage

This directory contains deterministic contract evaluations and model-outcome harnesses for skills in this repository.

## Two-Tier Evaluation Model

1. **Deterministic Contract Checks (Free, PR CI)**:
   - Run via `bash eval/<category>/<skill>/run-eval.sh --dry-run`.
   - Executed offline in a disposable, network-blocked workspace with synthetic fixtures.
   - Asserts non-negotiable written rules in `SKILL.md` and validates fixture schema, category splits, and disjoint tuning sets.
   - Does not spend model tokens. Most checks gate pull requests through `.github/workflows/entrypoint-sync.yml`; `ai-agent-pr-metadata` and `write-prompt-guide` use dedicated path-filtered workflows, while `workflow-router` is not yet wired into PR CI.

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
| `workflow-router` | `eval/engineering/workflow-router/` | None | Deterministic check only; not yet wired into PR CI |
| `write-prompt-guide` | `eval/engineering/write-prompt-guide/` | None | Deterministic check only; verified in path-filtered CI |
| `external-pr-viability` | `eval/engineering/external-pr-viability/` | Built-in | Verified in CI |
| `ai-agent-pr-metadata` | `eval/engineering/ai-agent-pr-metadata/` | Built-in | Verified in CI |
| `external-campaign-triage` | `eval/engineering/external-campaign-triage/` | Built-in | Verified in CI |
| `roast` | `eval/product/roast/` | Built-in | Verified in CI |
| `handover` | `eval/productivity/handover/` | Built-in | Verified in CI |
| `diagnose` | Intentional deferral | Not yet tracked | Upstream-adapted diagnostic loop |
| `external-pr-style` | Intentional deferral | Not yet tracked | Natural prose guidance |
| `git-guardrails-claude-code` | Intentional deferral | Not yet tracked | Hook installation procedure |
| `open-code-review-setup` | Intentional deferral | Not yet tracked | OCR setup workflow |
| `resolving-merge-conflicts` | Intentional deferral | Not yet tracked | Conflict resolution procedure |
| `tmux-orphaned-socket` | Intentional deferral | Not yet tracked | Low-level socket recovery |
| `wizard` | Intentional deferral | Not yet tracked | Procedural bash generator |
| `writing-for-agents` | Intentional deferral | Not yet tracked | Authoring reference |
