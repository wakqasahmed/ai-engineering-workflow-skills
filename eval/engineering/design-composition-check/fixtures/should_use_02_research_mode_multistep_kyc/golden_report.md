## Trigger
This design system came from a competitor-research pass with no source file, non-technical stakeholders must sign off on it, and no screen has exercised it yet ahead of three queued features.

## Screens Selected
- KYC Flow — primary flow: this is the product's core multi-step task, with the most state variety (upload, liveness, review, approve/decline, retry)
- Audit Log — information density: faceted search over every verification attempt

## Verdict
Does not compose — rework before scaling

## Gaps
- No token or component represents a declined-with-retry state distinct from a hard decline — Genuine: escalate as design-system amendment (issue #205); retry-after-decline is part of this flow's most common real path, so the KYC flow cannot be built correctly today until this state is defined, and other features must not scale on this system yet.
