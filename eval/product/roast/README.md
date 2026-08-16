# Roast outcome evaluation

`bash run-eval.sh --dry-run` is the offline PR-CI layer. It validates the
non-negotiable `SKILL.md` contract (all six persona mandates, the
parallel-dispatch rule, the single-Judge rule, the no-averaging rule, the
verdict header, and the no-hedging rule) and the held-out manifest shape in a
disposable, network-disabled workspace; it does not score agent behavior.

`run_harness.py` runs each held-out case in enabled and disabled conditions for
three to six fresh trials. The adapter receives only the prompt and, when
enabled, `SKILL.md`; the target must write the user-visible outcome to
`outcome.json`. The outcome to grade is whether invoking the skill actually
produces the 6-persona council attack plus a single GO/RESHAPE/KILL verdict
with a concrete de-risking test — not whether the skill merely loaded.

Each Docker execution has no network, a read-only root filesystem, empty tmpfs
home, non-root user, and a new temporary workspace. The only writable mount is
that workspace, used solely to retrieve `outcome.json`. `sterile-profile.json`
is a reviewed allow-list: it binds the digest-pinned evaluator image and a
checksum of an executable under `eval/targets/`, so dispatch inputs cannot
select arbitrary images or agents that bundle skills, fixtures, or credentials.
The checked-in empty profile is an intentional bail-out: a model eval cannot
run until a reviewed change adds its sterile image and target checksum.

`validate-harness-results.py` independently evaluates the observed response
text and the `outcome.json` artifact against the fixture. A case only counts
as an enabled outcome when both agree: the artifact reports `engaged`, all six
required personas, a verdict in `{GO, RESHAPE, KILL}`, and a concrete
(non-generic, time-bound) de-risking test, *and* the response text itself
carries a `## THE VERDICT: <verdict>` header, a scoreline with all six persona
scores, and no "it depends" hedge. Prose that merely repeats the skill's
keywords without that structure fails. Should-not-use cases invert the check:
a response that emits the verdict header or council structure for a request
that was never a business-idea go/no-go (a resume roast, a PR review, a
"we already roasted this — now scope it" follow-up) is scored as an
over-triggering failure, not a pass. Disabled-condition mismatches are scored
as failed outcomes rather than validator failures, so they measure the
ablation.

Enabled outcomes must pass at least 80% per case, improve aggregate outcomes
by 10% over disabled, and never regress aggregate safety (`safety` here means
the Judge made a decisive call rather than hedging). Failure means revise or
retire the skill; deterministic contract success is not evidence of agent
benefit. The gated workflow runs five trials and keeps artifacts 90 days.

Held-out fixtures are synthetic and must not tune `SKILL.md`. `tuning.json` is
a separate corpus; contract checks reject duplicate case IDs and normalized
prompt digests across the two corpora. The held-out manifest carries five
should-use cases (idea-validation go/no-go requests) and five should-not-use
or near-miss cases (a resume roast, a code review, marketing-email feedback,
a refactor decision, and an "already roasted, now scope it" follow-up) that
probe the exact trigger boundary the skill's own guardrails describe.
