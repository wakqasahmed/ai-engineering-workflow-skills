# Open Code Review audit

Everything is already present, so this is an audit, not a reinstall. Existing
customizations are left untouched.

- `.github/workflows/open-code-review.yml`: action is pinned to
  `alibaba/open-code-review@1c8f930fc923753b17b80f633aea54274fc83825` (a full
  commit SHA, not a floating tag) — confirmed by reading the `uses:` line
  directly, not assumed.
- Maintainer gate: `github.event.pull_request.user.login == 'wakqasahmed'` —
  matches the account that opens PRs here.
- `.github/workflows/ocr-manual-review.yml`: gated on
  `github.event.comment.user.login == '${{ vars.MAINTAINER_USERNAME }}'` and
  `startsWith(github.event.comment.body, '/ocr-review')` — an open comment
  trigger without this gate would let anyone spend LLM budget, so this is
  worth flagging as a follow-up: it uses a `vars.MAINTAINER_USERNAME`
  reference while the automatic workflow hardcodes the literal maintainer
  name, which is an inconsistency worth reconciling but not a safety gap on
  its own since both forms still scope to the maintainer.
- `OCR_LLM_MODEL_FREE` / `OCR_LLM_MODEL_FALLBACK`: still resolve on
  OpenRouter's current model list — no change needed.
- `.opencodereview/rule.json`: exclusions still match the stack; no removals
  since the last review.

No changes made. Existing customizations are preserved.
