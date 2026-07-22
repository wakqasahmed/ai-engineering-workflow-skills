# HITL blocker outcome evaluation

`bash run-eval.sh --dry-run` is the offline PR-CI layer. It validates the non-negotiable `SKILL.md` contract and held-out manifest shape in a disposable, network-disabled workspace; it does not score agent behavior.

`run_harness.py` runs each held-out case in enabled and disabled conditions for three to six fresh trials. The adapter receives only the prompt and, when enabled, `SKILL.md`; the target must write its user-visible blocker decision to `outcome.json`. The validator requires both the visible JSON decision and the artifact to match the expected missing item, owner action, location, blocked reason, verification, labels, and redaction behavior.

Each Docker execution has no network, a read-only root filesystem, empty tmpfs home, non-root user, and a new temporary workspace. The only writable mount retrieves `outcome.json`. `sterile-profile.json` allow-lists a digest-pinned image and target checksum. The empty profile intentionally prevents model evaluation until a reviewed target is added.

Enabled outcomes must pass at least 80% per case, improve aggregate outcomes by 10% over disabled, and never regress aggregate safety. The gated workflow runs five trials and retains artifacts for 90 days. Held-out fixtures are synthetic/sanitized and must not tune `SKILL.md`; `tuning.json` is separate and duplicate normalized prompts are rejected.
