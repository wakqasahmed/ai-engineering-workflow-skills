---
name: external-pr-style
description: Write PR descriptions for third-party upstream repos in natural human prose to avoid maintainer AI-rejection patterns. Use before opening any PR against a repo we don't own.
---

# External PR Style

Use this whenever opening a PR against a repository we don't own or control — any upstream, third-party, open-source contribution.

## The problem

Some maintainers reject otherwise-correct, well-tested PRs purely because the description reads as AI-generated: generic section headers ("Root Cause:", "Why This Fix Works:", "Alternatives Considered:"), templated phrasing, over-explained one-line fixes. This is usually not an automated detector — it's a human maintainer pattern-matching by eye and closing with a canned rejection reply, sometimes on a diff that is otherwise correct and tested.

Confirmed directly across several upstream contribution sessions: individual maintainers of some well-known PHP/JS ecosystem repos have closed multiple PRs this way, including one with an identical fix and real tests to a version that was later accepted once the description was rewritten. This pattern is maintainer-specific, not universal — always check a target repo's recent closed-PR history for this signature before assuming it applies.

## Rules

- Write the PR body as first-person prose describing the bug and the fix, the way you'd explain it to a coworker over chat — not as a templated report.
- No invented section headers unless the target repo's own template requires them (see exception below). Skip "Root Cause:", "Why This Works:", "Alternatives Considered:", "Summary:" unless the repo asks for exactly that.
- State what you verified — tests run, red→green proof, residual risk on security-sensitive changes — as plain sentences woven into the explanation, not as a labeled checklist.
- Don't over-explain a small fix. Match the length of the description to the size of the change.
- Don't hedge excessively or enumerate edge cases nobody asked about.

## Compression pass (do this last, before posting)

Technique adapted from [mattpocock/skills — caveman](https://github.com/mattpocock/skills/blob/main/skills/misc/caveman/SKILL.md) (filler/hedge/pleasantry stripping), applied to natural prose rather than caveman's fragment style — added 2026-08-26 after lunarphp/lunar#2606, where a maintainer flagged our PR descriptions as reading AI-generated.

Long, padded explanations are themselves an AI-tell, independent of headers — reread the drafted body and strip (see canonical [prose compression word list](references/compression-word-list.md)):

- Pleasantries/hedging: "I'd be happy to", "please note that", "it's worth mentioning", "certainly", "of course", "I believe".
- Filler intensifiers: "just", "really", "basically", "actually", "simply", "essentially".
- Restated context the maintainer already has (the issue title, the file name, "as described in the issue").
- Any sentence that explains something the diff already makes obvious.

This is a compression pass on your own draft, not a caveman-style rewrite — keep full sentences, articles, and natural grammar. The goal is a shorter draft that reads like a person who typed fast, not a person who dropped words to save tokens. If a sentence survives after removing every filler word from it, it earns its place; if it doesn't survive, it wasn't saying anything.

## Exception: repos with a bot-enforced template

Some repos mechanically require specific sections — a PR-checks bot that blocks merge until a template is filled in (e.g. a required Summary/Why/How/Testing/Examples/Checklist structure), or a PR-title-lint bot with a fixed scope list. There, fill in exactly what's required. That's a hard requirement, not the AI-tell pattern — skipping it isn't concision, it's an incomplete submission that gets mechanically blocked before a human ever reads it.

Check for this before writing the PR body: look for `.github/pull_request_template.md`, a PR-checks workflow that validates title/body format, or CONTRIBUTING.md language describing a required structure. If one exists, follow it precisely. If none exists, default to natural prose.

## Distinct from an explicit no-AI-contributions policy

Some repos state an outright policy against AI-assisted contributions (e.g. a maintainer-applied "rejected AI" label, or CONTRIBUTING.md language explicitly declining AI-generated PRs). That is a different, harder line than a style preference. Don't try to write around an explicit policy like that — skip the repo entirely. This skill is about writing genuinely well for repos that judge quality and effort, not about disguising AI involvement where a maintainer has drawn an explicit line against it.

## Commit messages

This governs PR *descriptions* only. Commit message attribution rules (no AI co-author lines, ever) are unaffected and covered separately in `system-level/core.md` — they apply regardless of which repo you're contributing to.
