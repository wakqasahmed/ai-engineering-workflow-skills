# Changesets release outcome evaluation

`bash run-eval.sh --dry-run` is the deterministic PR-CI layer. It creates a
disposable offline workspace containing only `SKILL.md`, the contract checker,
and the held-out synthetic manifest. It checks non-negotiable written rules and
fixture integrity; it does not claim to score an agent outcome.

The ten cases in `fixtures/held-out.json` are held out and must not be used for
tuning. There are no sanitized real traces available for this skill yet; add
them separately from held-out cases after removing repository, customer, and
credential details.

`run_harness.py` is the explicitly gated live outcome harness. It runs five
fresh trials for every case in both conditions: enabled receives the prompt and
`SKILL.md`; disabled receives the prompt without the skill. Each trial has a
new temporary workspace, empty home, no repository mount, read-only root, and
`--network none`. The manual workflow takes a digest-pinned evaluator image and
an evaluator command. The command runs as `/bin/sh -ceu` inside that image and
must emit one JSON object containing `model`, `outcome`, and `safety_outcome`.
It can report `skill_used` for diagnostics, but the validator never uses that
metadata as an outcome score. It receives only the read-only `/workspace` mount
with `case.json` (and `SKILL.md` in the enabled condition), plus the declared
`HARNESS_*` environment values.

Run it only from the manual `changesets-release-outcome-eval` workflow with a
digest-pinned image and an evaluator command compatible with this contract.
`validate-harness-results.py`
requires an 80% enabled outcome rate for every case and at least a 2% aggregate
enabled-versus-disabled improvement. Results declare harness version `1`, the
workflow's declared model, and five trials per condition. It retains the
comparison JSON artifact.
If the threshold fails, investigate or retire the skill; contract checks alone
are not outcome evidence.
