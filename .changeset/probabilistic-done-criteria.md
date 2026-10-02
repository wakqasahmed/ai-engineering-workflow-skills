---
"ai-engineering-workflow-skills": minor
---

Add a Probabilistic Output Requirement to `define-done` and a matching post-release accuracy signal to `release-gate`.

It applies only when a change's user-visible output comes from a model, a heuristic ranking, or another component whose correctness varies by input, so deterministic work and ordinary bug fixes carry no new steps. For those features, acceptance criteria must state a numeric target error rate with its unit and window ("accurate", "high quality", and "zero errors" are rejected), name a measurement method whose grading source is not the model's own output, name an owner for the number after release who is not the adoption owner, and add a permanent regression case for every confirmed production failure.

`release-gate` now lists the post-release accuracy signal next to the health check for medium/high-risk probabilistic changes, and points back to `define-done` for the target, method, and owner. The offline contract checks for both skills assert the new text.
