# design-composition-check eval

Deterministic outcome-based evaluation for the `design-composition-check` skill (issue #203).

The skill's output artifact is a markdown report posted on a GitHub issue (or an
explicit skip line), not code, so `contract.py` parses that report's structure —
the `## Screens Selected`, `## Verdict`, and `## Gaps` sections defined in
SKILL.md's "Report format" — instead of pattern-matching free-form prose. It
checks that the selected anchor screens come from the hardest candidates in
scope (never the easy/skip list for that fixture), that exactly one of the
three valid verdicts is used, and that any gap under a non-clean verdict is
classified as Correctable or escalated as a Genuine design-system amendment.

## Fixtures

- `should_use_01_dense_dashboard_and_checkout` — a freshly extracted design
  system about to serve four features; the golden report anchors on the
  dense analytics dashboard and the primary approval flow, not the landing
  or settings screens, and files one correctable and one genuine gap.
- `should_use_02_research_mode_multistep_kyc` — a research-mode-derived
  system needing non-technical sign-off; the primary KYC flow's missing
  retry-vs-decline state is severe enough to produce a "does not compose"
  verdict instead of a filed-gap pass.
- `should_skip_01_established_framework` — shadcn/ui already proven across
  three existing features; the trigger does not fire and the skill must
  skip without forcing a screen selection or verdict.

## Running the eval

```bash
bash eval/engineering/design-composition-check/run-eval.sh
```

No network access or credentials required — this layer never invokes an LLM.

## Extending it

Add a new `fixtures/<should_use|should_skip>_NN_name/` with `input.md`,
`meta.json`, and either `golden_report.md` (should_use) or
`golden_response.md` (should_skip). Run `run-eval.sh` to confirm the new
golden output satisfies `contract.py` before committing.
