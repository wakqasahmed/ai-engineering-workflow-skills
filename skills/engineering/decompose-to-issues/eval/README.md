# Decompose-to-issues outcome evaluation

`bash run-eval.sh --dry-run` is the deterministic PR-CI layer. It runs offline
in a disposable workspace with only `SKILL.md`, the contract checker, and the
held-out manifest. It checks non-negotiable skill text and fixture integrity;
it does not score agent behavior.

`run_harness.py` is the explicitly gated outcome evaluation. Each held-out case
runs three to six fresh trials in both conditions. Enabled receives the prompt,
the repository-controlled target-agent adapter, and `SKILL.md`; disabled
receives no skill. Every case/trial gets a temporary workspace. The Docker
container has no network, no repository mount, an empty tmpfs home, a read-only
root filesystem, no Linux capabilities, and no ambient credentials. Rubrics
remain outside the container. The adapter forwards only the prompt and optional
skill path, and returns only the agent's user-visible response.

The validator compares those observable responses with case-specific outcome
and safety rubrics; it neither scores skill loading nor accepts agent verdict
fields. It requires an 80% enabled outcome rate for each case, a 10% aggregate
enabled-versus-disabled improvement, and no aggregate safety regression. If a
threshold fails, revise or retire the skill rather than citing contract checks
as outcome evidence.

Run the gated workflow with a digest-pinned image, a repository-controlled
agent executable, a matching sterile-image attestation, declared model, and
three to six trials. Results are retained for 90 days. The held-out fixtures
must not tune `SKILL.md`; add synthetic cases and sanitized real usage/failure
traces only after separating any tuning corpus from these held-out cases.
