# Selecting the hardest compositions

The point of this pass is falsification: does the design system compose into real screens, not just the convenient ones? Picking easy screens first only postpones the discovery of a gap until more features already depend on the system.

## What makes a screen "hard"

Rank candidate screens by these three signals; a screen only needs to score high on one to qualify:

- **Highest information density** — many data points, columns, or controls visible at once: a dense table, a multi-filter dashboard, a comparison grid, a log/audit view. These stress the system's spacing, typography scale, and component composition under real content volume, not lorem ipsum.
- **Most state variety** — the screen has many distinct visual states to represent: loading, empty, error, partial, success, and permission-gated variants, or a component that changes shape based on data (a card that sometimes has an image, sometimes a badge, sometimes neither).
- **The primary or critical user flow** — checkout, signup/KYC, the core multi-step task the product exists to support. If this flow doesn't compose, nothing else about the system matters yet.

## What makes a screen "easy" (skip these as anchors)

- A static marketing or landing page with fixed, curated content.
- A settings screen with a handful of toggles or a single form field.
- An empty or near-empty detail view with little data variety.
- Any screen that was the source material the design system was extracted or derived from — it will trivially compose because the system was built to match it.

## Finding hard candidates fast

- Scan the feature backlog or PRD for words like "table," "dashboard," "filter," "sort," "bulk," "audit," "checkout," "onboarding," "wizard," or "multi-step" — these usually mark hard candidates.
- Ask which screen has the most distinct components or conditional branches in its spec; that is a state-variety signal even when the screen looks visually simple.
- Ask which single screen, if broken, blocks the product's core value; that is the primary-flow signal regardless of visual complexity.

## Picking 1-2, not more

Two screens are usually enough to falsify: one dense/data-heavy screen and one primary-flow screen, when both exist in scope. Pick only one when a single screen already carries both signals (e.g., a checkout flow with a dense order-summary table), or when only one signal is present in the current scope. Do not pad the pass with additional screens once the system has been genuinely stressed — that turns a falsification check into unrequested process.
