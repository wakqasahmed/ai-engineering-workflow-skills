---
name: design-composition-check
description: Falsify a new or unfamiliar design system by rendering its hardest UI compositions before other features build on it. Use when a freshly researched, extracted, or ingested design system or token set is about to be used by more than one feature and no prior screen has exercised it yet.
---

# Design Composition Check

Use this before a second feature starts building against a new or unfamiliar design system — after the system exists (tokens, components, or an extracted style guide), before it becomes a shared dependency.

## Trigger

Run this when all of the following hold:

- The design system or token set is new or unfamiliar: freshly researched, extracted from a reference, or ingested from a non-technical source — not something already proven across features in this project.
- More than one feature is about to depend on it.
- No prior screen in this project has exercised it yet.

## Skip conditions

- An established, framework-driven UI (Material, Ant, shadcn/ui, or similar) already proven elsewhere in this project or organization.
- A routine styling change to an existing, already-validated system.

State the skip condition in one line and stop. Do not select screens or render a verdict.

## Workflow

1. From the features already in scope, list every screen the design system will need to support.
2. Pick 1-2 of the *hardest* compositions from that list — never the easiest. See [Selecting the hardest compositions](references/screen-selection-guide.md) for what "hardest" means and how to find it fast.
3. Render each selected screen against the proposed tokens/components: a mockup, a component-driven build, or the actual feature implementation if one is already planned. Let that first real implementation issue double as the evidence instead of requiring a separate throwaway pass.
4. For every place the screen's real content doesn't fit the system cleanly, classify the gap:
   - **Correctable** — an existing token or component covers it with a small adjustment. Make the fix and note it.
   - **Genuine gap** — no existing token or component covers it. Do not invent a one-off, screen-local fork. Escalate it as a design-system amendment on the tracking issue.
5. Render one verdict and post it as a comment on the GitHub issue that introduced the design system (or the tracking issue for the feature that will consume it first):
   - **Composes cleanly** — no gaps found; the system is ready for other features to build on.
   - **Composes with a filed gap** — one or more gaps found and disposed of per step 4; the system is still ready, with amendments tracked.
   - **Does not compose** — a genuine gap is severe enough that the hardest screen cannot be built without a redesign.
6. When the verdict is "does not compose," revise the system before any other feature scales on it. Treat the design system as a blocked dependency — pause other features depending on it until the revision ships; do not proceed in parallel hoping the amendment lands later.

## Report format

Post this on the tracking issue:

```
## Trigger
<why this system qualified: new/unfamiliar, more than one feature, no prior screen>

## Screens Selected
- <screen name> — <why it's hard: information density | state variety | primary flow>
- <screen name> — <why it's hard: ...>

## Verdict
<Composes cleanly | Composes with a filed gap | Does not compose — rework before scaling>

## Gaps
- <gap> — Correctable: <what was fixed>
- <gap> — Genuine: escalate as design-system amendment (issue #<n>)
```

Omit the Gaps section only when the verdict is "Composes cleanly."

## Guardrails

- Never pick the easiest screens to get a fast "composes cleanly" verdict — that defeats the falsification purpose. If every screen in scope is genuinely easy, the skip condition applies instead of running this check on artificially convenient screens.
- Never let a genuine gap quietly become a one-off, screen-local fork of the system. Escalate it as a design-system amendment on the tracking issue, the same place other features will look before they hit the same gap.
- Do not create a separate manifest, screen-ID registry, or design-pipeline ledger — findings live on the existing GitHub issue.
- This is optional and narrow: it never blocks routine styling work or an already-proven system, and it is not a substitute for `to-prd`'s prototype allowance or the manual acceptance walkthrough in `AI_ENGINEERING_WORKFLOW.md` — those verify a decision or one feature's behavior; this verifies whether the shared system holds up under its hardest real usages.
