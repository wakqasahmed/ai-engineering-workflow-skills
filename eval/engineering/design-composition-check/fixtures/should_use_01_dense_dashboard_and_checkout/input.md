# Scenario

A team just finished extracting a token/component set from a Figma reference
for a new internal ops tool. Three features are queued to build on it:

- A marketing-style "Welcome to Ops Console" landing screen (static copy, one CTA).
- A settings screen with three toggles.
- A multi-column analytics dashboard with per-column filters, sorting, and
  pagination over a live dataset.
- A multi-step checkout/approval flow (request → review → approve/reject →
  confirmation) that is the tool's core purpose.

No feature has shipped a screen against this system yet, and all four
features are expected to depend on it.
