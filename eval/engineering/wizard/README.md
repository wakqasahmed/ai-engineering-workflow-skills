# wizard eval

Deterministic outcome-based evaluation for the `wizard` skill (issue #176).

A wizard's output artifact is an executable bash script, not markdown, so
`contract.py` does light static analysis of the generated script instead of
pattern-matching prose: which values are captured with `ask_secret` (hidden
entry) vs. plain `ask`, which are `write_env`'d and `set_secret`'d, whether
`TOTAL_STAGES` matches the real `stage()` count, and — for scenarios flagged
irreversible — whether a `confirm` gate exists at all before proceeding.

## Fixtures

- `should_use_01_credential_setup` — normal, non-destructive credential setup: one
  secret (`ask_secret`, `set_secret`) and one plain value (`ask`, `write_env`).
- `should_use_02_irreversible_migration` — dropping a legacy table is irreversible;
  the golden script gates it behind `confirm`.
- `should_not_use_01_agent_performable_task` — a package rename the agent can do
  itself, with no third-party dashboard or human-only step; the skill must decline.

## Running the eval

```bash
bash eval/engineering/wizard/run-eval.sh
```

No network access or credentials required — this layer never invokes an LLM.

## Extending it

Add a new `fixtures/<should_use|should_not_use>_NN_name/` with `input.md`,
`meta.json`, and either `golden_wizard.sh` (should_use) or `golden_response.md`
(should_not_use). Run `run-eval.sh` to confirm the new golden output satisfies
`contract.py` before committing.
