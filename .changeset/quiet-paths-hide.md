---
"ai-engineering-workflow-skills": minor
---

Add a leak check that runs in CI on every pull request and on pushes to main. `scripts/check-leaks.py` scans every tracked file and fails on absolute home paths (the eval sandbox users `/home/agent` and `/home/evaluator` are allowed), paths to token and credential files, and GitHub or API-key-shaped secrets. It also accepts an optional private denylist through the `LEAK_DENYLIST` repository secret, so names that must never ship can be blocked without committing the list itself. Matches are reported by file and line, with secrets redacted and denylist hits shown only by entry number.

The `docker-db-guardrails` and `external-campaign-triage` examples now use neutral placeholders (`app_demo` and `<campaign-tracker-repo>`) in place of names that referred to private work.
