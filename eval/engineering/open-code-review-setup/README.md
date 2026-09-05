# open-code-review-setup eval

Deterministic outcome-based evaluation for the `open-code-review-setup` skill
(issue #177).

This skill's output artifacts are GitHub Actions workflow YAML and a JSON
rule file, not markdown prose, so `contract.py` does light static analysis of
those artifacts: SHA-pinning of `alibaba/open-code-review`, maintainer gates
on both the automatic and manual-review workflows, no unsafe checkout of
PR-supplied code, no hardcoded credential values, and non-empty `rule.json`
exclusions.

## Fixtures

- `should_use_01_fresh_install` — nothing present yet: real copies of the
  skill's own templates, correctly configured, are the golden artifacts.
- `should_use_02_safe_audit_only_update` — everything already present; the
  golden response is an audit, not a reinstall, and does not claim to
  overwrite existing customizations.
- `should_not_use_01_missing_credential` — no OpenRouter key available; the
  golden response stops and defers to `hitl-blocker` instead of inventing a
  placeholder credential.

Two mutation regressions in `run_eval.py` (not separate fixture dirs) prove
the contract actually rejects the two other scenarios the issue named:
stripping the manual-review workflow's maintainer gate (untrusted comment
trigger), and swapping the pinned SHA for a floating tag (mutable action
input) — both against the real templates, not synthetic text.

## Running the eval

```bash
bash eval/engineering/open-code-review-setup/run-eval.sh
```

No network access or credentials required — this layer never invokes an LLM.

## Extending it

Add a new `fixtures/<should_use|should_not_use>_NN_name/` with `input.md`,
`meta.json`, and either the three `golden-*` artifact files (should_use, a
real install) or `golden_response.md` (should_not_use, or should_use for an
audit-shaped response). Run `run-eval.sh` to confirm the new golden output
satisfies `contract.py` before committing.
