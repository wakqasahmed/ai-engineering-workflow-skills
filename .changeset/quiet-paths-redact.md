---
"ai-engineering-workflow-skills": patch
---

The `handover` skill now states a public-surface rule: anything posted to a GitHub issue or PR, or written to a public repo file, uses repo-relative paths only. Absolute host paths, home-directory layout, credential or token file locations, auth command patterns, and private repo names are replaced with `[local path redacted]` or generic wording, and the public draft gets a grep scan for host-path and credential patterns before posting. Local handover files still keep absolute paths. `system-level/core.md` points non-handover status comments at the same rule, and the handover contract check now asserts the rule is present.
