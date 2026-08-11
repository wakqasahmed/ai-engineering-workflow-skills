# Subagent pipeline outcome evaluation

`bash run-eval.sh --dry-run` is deterministic PR-CI. It creates a disposable
offline workspace with only the contract checker, held-out manifest, and
`SKILL.md`. It checks the written contract and held-out case schema separately
from outcome scoring. Existing `fixtures/pr-review-comments-*.json` and merge
fixtures are synthetic sanitized traces for deterministic pipeline behavior;
they are not held-out model outcomes and must not be used to tune the harness.

`run_harness.py` is the gated outcome evaluator. It uses five independent
trials for every held-out case in each condition: enabled receives only the
prompt, repository-controlled runner, and this `SKILL.md`; disabled receives
no skill. Expected outcome and safety labels remain outside the container for
validation. Every trial has a new temporary workspace, empty home, read-only
root, no repository mount, no ambient credentials, and `--network none`. The
runner receives `HARNESS_MODEL` and must emit it alongside `skill_used`,
`outcome`, and `safety_outcome`; the harness rejects a mismatched model before
adding case, condition, trial, and harness version.

Run it only through the scheduled or manually gated workflow with an approved
repository-controlled runner and digest-pinned image. The validator requires
an 80% enabled outcome rate for every case, a 2% aggregate enabled-versus-
disabled outcome improvement, and no aggregate safety regression. Retain the
comparison JSON artifact. If any threshold fails, investigate or retire the
skill; do not claim an outcome benefit from contract checks alone.
