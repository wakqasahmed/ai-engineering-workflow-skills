# Workflow Router Evaluation

Deterministic offline evaluation suite for the `workflow-router` skill (`skills/engineering/workflow-router/SKILL.md`).

## Purpose

This eval validates two aspects of `workflow-router`:
1. **Setup Safeguards**: Confirms `SKILL.md` documents all required repository discovery conventions (GitHub remotes, tracker files, target branch, labels, `docs/` layout, `AGENTS.md`, test commands, approval before writing, and no destructive overwrites).
2. **Routing Accuracy**: Tests scenario inputs against the 6 core workflow routes:
   - `idea-to-staging` (vague or multi-issue requests)
   - `small-feature` (concrete single behavior change)
   - `claimed-github-issue` (claimed non-trivial GitHub issue)
   - `bug` (bug or regression)
   - `release` (release or production deployment)
   - `human-held-blocker` (credentials, DNS, billing, permissions)

## Fixtures

- `fixtures/scenarios.json`: Contains curated input scenarios with expected route classifications, ensuring unambiguous mapping across diverse phrasing.

## Running the Evaluation

Run the evaluation script from the repo root or this directory:

```bash
eval/engineering/workflow-router/run-eval.sh
```

The script runs completely offline with zero external network dependencies.
