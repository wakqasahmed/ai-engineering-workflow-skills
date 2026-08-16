# To-prd outcome evaluation

`bash run-eval.sh --dry-run` is the offline PR-CI layer. It runs
`evaluate.py`'s mutation-tested `SKILL.md` contract and canned-candidate
regression checks, then validates the non-negotiable contract text and
held-out manifest shape in a disposable, network-disabled workspace. Neither
step scores a real agent's outcome.

`run_harness.py` runs each held-out case in enabled and disabled conditions for
three to six fresh trials. The adapter receives only the prompt and, when
enabled, `SKILL.md`; the target must write its user-visible spec outcome to
`outcome.json` as `{"decision", "published", "ready_for_agent",
"asked_confirmation", "safety"}`. `decision` is one of `published_ready`,
`published_blocked`, `paused_for_confirmation`, `blocked_no_publish`, or
`not_applicable` (narrow, issue-shaped work the skill should not engage). The
validator compares this host-observed artifact against each case's expected
outcome; keyword-only prose cannot pass.

Each Docker execution has no network, a read-only root filesystem, empty tmpfs
home, non-root user, and a new temporary workspace. The only writable mount is
that workspace, used solely to retrieve `outcome.json`. `sterile-profile.json`
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
