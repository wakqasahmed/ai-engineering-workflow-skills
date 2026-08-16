# Filament conventions outcome evaluation

`bash run-eval.sh --dry-run` is the offline PR-CI layer. It validates the
non-negotiable skill contract and held-out/tuning corpus separation; it does not
score agent behavior.

`run_harness.py` is the explicitly gated model evaluation. It runs every
held-out case in enabled and disabled conditions for three to six trials. Each
fresh Docker workspace receives only the target agent, adapter, prompt, and the
skill for enabled trials. The container has no network, no ambient credentials,
an empty home, a read-only root filesystem, and no repository mount.

The target agent writes an implementation-decision artifact and returns the
same JSON as its user-visible response. The validator independently compares
both to fixture-owned expected outcomes: the detected Filament version and the
chosen public implementation approach. It does not use skill-loading metadata
as an outcome signal.

Enabled trials must pass at least 80% for every case, improve aggregate outcome
rate by at least 10 percentage points over disabled trials, and not regress
safety. Failed evaluation means retire or revise the skill. Results are kept
for 90 days by the manual workflow.

Held-out fixtures are synthetic. Keep any future sanitized real traces and
tuning cases outside `fixtures/held-out.json`.
