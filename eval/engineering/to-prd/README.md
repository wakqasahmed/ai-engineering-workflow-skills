# To-prd outcome evaluation

`bash run-eval.sh --dry-run` is the offline PR-CI layer. It runs
`evaluate.py`'s mutation-tested `SKILL.md` contract and canned-candidate
regression checks, then validates the non-negotiable contract text and
held-out manifest shape in a disposable, network-disabled workspace. Neither
step scores a real agent's outcome.

`run_harness.py` runs each held-out case in enabled and disabled conditions for
three to six fresh trials. The adapter receives the prompt, a path to
`fake-tracker` (a harness-owned fake issue-tracker CLI standing in for the
real project tracker `SKILL.md` says to detect and publish to), and, when
enabled, `SKILL.md`. `published` and `ready_for_agent` are **never**
self-reported by the target — they are derived exclusively from
`tracker-log.jsonl`, an append-only log only `fake-tracker`'s own successful
executions can write to, so a target that merely prints or writes JSON
claiming `published: true` without invoking the tracker is not believed.
`decision`, `asked_confirmation`, and `safety` still come from the target's
visible JSON response, since the harness has no independent way to observe
those. `decision` is one of `published_ready`, `published_blocked`,
`paused_for_confirmation`, `blocked_no_publish`, or `not_applicable` (narrow,
issue-shaped work the skill should not engage). The validator compares this
merged artifact (visible-response fields plus tracker-derived fields) against
each case's expected outcome; keyword-only prose cannot pass, and neither can
a self-reported `published: true` with no matching tracker log entry.

Each Docker execution has no network, a read-only root filesystem, empty tmpfs
home, non-root user, and a new temporary workspace. The only writable mount is
that workspace, used solely to retrieve `tracker-log.jsonl` (never a path the
target could write an arbitrary "outcome" artifact to). `sterile-profile.json`
is a reviewed allow-list: it binds the digest-pinned evaluator image and a
checksum of an executable under `eval/targets/`, so dispatch inputs cannot
select arbitrary images or agents that bundle skills, fixtures, or credentials.
The checked-in empty profile is an intentional bail-out: a model eval cannot
run until a reviewed change adds its sterile image and target checksum.

`validate-harness-results.py` independently evaluates the JSON user-visible
outcome and the artifact against the fixture. Both are required for an enabled
outcome; a correct artifact cannot compensate for a mismatched or unsafe
response. Disabled mismatches are scored as failed outcomes rather than
validator failures, so they measure the ablation. Enabled outcomes must pass
at least 80% per case, improve aggregate outcomes by 10% over disabled, and
never regress aggregate safety (whether the reported readiness/publication
gating matched the expected safety state). Failure means revise or retire the
skill; deterministic contract success is not evidence of agent benefit. The
gated workflow runs five trials and keeps artifacts 90 days.

Held-out fixtures cover five should-use cases (well-specified spec, a
genuinely unresolved test seam that must pause for one confirmation, an
unresolved product blocker, missing tracker access, and a redundant-interview
guardrail) and five should-not-use cases (typo fix, unit test only, a small
CSS change, a dependency bump, and a pure decomposition request that belongs
to `decompose-to-issues`). They are synthetic and must not tune `SKILL.md`.
`tuning.json` is a separate corpus; contract checks reject duplicate case IDs
and normalized prompt digests across the two corpora.
