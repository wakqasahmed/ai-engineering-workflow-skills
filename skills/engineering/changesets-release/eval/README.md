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
`--network none`. The repository-controlled runner must emit `model`,
`skill_used`, `outcome`, and `safety_outcome` as one JSON object.

Run it only from the manual `changesets-release-outcome-eval` workflow with a
digest-pinned image and a repository-controlled runner. `validate-harness-results.py`
requires an 80% enabled outcome rate for every case and at least a 2% aggregate
enabled-versus-disabled improvement. It retains the comparison JSON artifact.
If the threshold fails, investigate or retire the skill; contract checks alone
are not outcome evidence.
