---
"ai-engineering-workflow-skills": minor
---

Extend `external-pr-style` to maintainer replies, not just PR descriptions, with word ceilings for short and detailed replies.

It now ships an outcome-eval harness: a deterministic contract check over held-out fixtures (banned headers including bold-markdown and bare header lines, hedge phrases with straight or curly apostrophes, em and en dash ceilings, and per-tier word floors and ceilings) that runs in PR CI, plus a manually dispatched model outcome eval.
