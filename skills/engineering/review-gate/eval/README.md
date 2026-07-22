# Review-gate outcome evaluation

`bash run-eval.sh --dry-run` is the deterministic PR-CI layer. It runs offline
in a disposable workspace and checks the non-negotiable `SKILL.md` contract and
held-out manifest shape. It does not score agent behavior.

`run_harness.py` is the explicitly gated model evaluation. Each held-out case
runs three to six fresh trials in both conditions. Enabled receives only the
prompt, repository-controlled target-agent adapter, and `SKILL.md`; disabled receives no
skill. The Docker container has no network, no repository mount, no ambient
credentials, a read-only root filesystem, an empty home, and a new temporary
workspace for every case/trial. Evaluation rubrics remain outside the
container. The adapter passes the target agent a prompt plus the optional
`SKILL.md` path and records only its text response. It does not accept outcome
or safety verdicts. The validator independently evaluates that response against
case-specific observable-review and safety rubrics; it does not score whether
the skill was loaded.

Supply a repository-controlled target-agent executable and a reviewed sterile-image
attestation through the gated workflow inputs. The attestation binds the exact
image digest and agent SHA-256 and asserts no ambient credentials, fixtures, or
preinstalled skills. The harness copies only the agent, adapter, prompt, and,
when enabled, `SKILL.md` into the read-only workspace. It runs as UID 65532 with
an empty tmpfs home and a minimal environment. The agent reads one JSON request
from standard input and writes only the review text to standard output.

The validator requires at least 80% enabled outcome rate per case, at least a
10% aggregate enabled-versus-disabled outcome improvement, and no aggregate
safety regression. A failed threshold means retire or revise the skill; do not
claim benefit from deterministic checks. The gated workflow retains the JSON
comparison artifact for 90 days.

`fixtures/held-out.json` must not be used to tune `SKILL.md`. Add synthetic
cases and sanitized real usage/failure traces only after placing any tuning
cases in a separate private or explicitly named non-held-out corpus.
