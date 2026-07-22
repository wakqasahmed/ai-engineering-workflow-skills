# Release-gate outcome evaluation

`bash run-eval.sh --dry-run` is the offline PR-CI layer. It validates the
non-negotiable `SKILL.md` contract and held-out manifest shape in a disposable,
network-disabled workspace; it does not score agent behavior.

`run_harness.py` runs each held-out case in enabled and disabled conditions for
three to six fresh trials. The adapter receives only the prompt and, when
enabled, `SKILL.md`; the target must write its user-visible release decision to
`outcome.json`. The validator compares this host-observed artifact against each
case's expected decision, artifact, validation, rollback, and safety fields;
keyword-only prose cannot pass.

Each Docker execution has no network, a read-only root filesystem, empty tmpfs
home, non-root user, and a new temporary workspace. The only writable mount is
that workspace, used solely to retrieve `outcome.json`. `sterile-profile.json`
is a reviewed allow-list: it binds the digest-pinned evaluator image and a
checksum of an executable under `eval/targets/`, so dispatch inputs cannot
select arbitrary images or agents that bundle skills, fixtures, or credentials.
The checked-in empty profile is an intentional bail-out: a model eval cannot
run until a reviewed change adds its sterile image and target checksum.

`validate-harness-results.py` independently evaluates response and safety
rubrics. Enabled outcomes must pass at least 80% per case, improve aggregate
outcomes by 10% over disabled, and never regress aggregate safety. Failure means
revise or retire the skill; deterministic contract success is not evidence of
agent benefit. The gated workflow runs five trials and keeps artifacts 90 days.

Held-out fixtures are synthetic or sanitized traces and must not tune
`SKILL.md`. `tuning.json` is a separate corpus; contract checks reject duplicate
case IDs and normalized prompt digests across the two corpora.
