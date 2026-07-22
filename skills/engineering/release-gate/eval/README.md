# Release-gate outcome evaluation

`bash run-eval.sh --dry-run` is the offline PR-CI layer. It validates the
non-negotiable `SKILL.md` contract and held-out manifest shape in a disposable,
network-disabled workspace; it does not score agent behavior.

`run_harness.py` runs each held-out case in enabled and disabled conditions for
three to six fresh trials. The adapter receives only the prompt and, when
enabled, `SKILL.md`, then records only the user-visible text response. Each
Docker execution has no network, a read-only root filesystem, empty tmpfs home,
non-root user, no repository mount, and a new temporary workspace. A reviewed
attestation binds the digest-pinned image and target-agent checksum to the
sterile-environment claims.

`validate-harness-results.py` independently evaluates response and safety
rubrics. Enabled outcomes must pass at least 80% per case, improve aggregate
outcomes by 10% over disabled, and never regress aggregate safety. Failure means
revise or retire the skill; deterministic contract success is not evidence of
agent benefit. The gated workflow runs five trials and keeps artifacts 90 days.

Held-out fixtures are synthetic or sanitized traces and must not tune
`SKILL.md`. Keep tuning cases in a separate, explicitly non-held-out corpus.
