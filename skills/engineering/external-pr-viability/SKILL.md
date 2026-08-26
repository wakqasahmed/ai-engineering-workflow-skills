---
name: external-pr-viability
description: Check whether an upstream repo actually merges outside contributors before investing implementation time in an unsolicited PR. Use right after scouting a candidate issue in a third-party repo, before writing any fix.
---

# External PR Viability

Use this before writing a single line of code for an unsolicited PR against a repository you do not already have merged standing in.

## The problem

A correct, fully-tested, contribution-guideline-compliant PR can be closed within seconds, with zero review and zero comment, even though CI passed. That is not a code-quality signal — a genuine quality rejection leaves a comment or a "changes requested" review, because the point of a comment is to get the author to fix something. A silent, near-instant close with passing checks means the PR was never evaluated on its merits: it was closed because of who opened it, not what was in it. No amount of correctness, test coverage, or contribution-guideline compliance changes that outcome, and reattempting on the same repo (a different issue, a rewritten description) wastes the same amount of effort again.

Confirmed directly: a PR fixing a real, independently-verified one-line bug — with a red/green-tested regression test, a linked issue, a filled-in contribution template, and the required changelog entry — was closed by a core-team member 34 seconds after the final push. Checking the last 100 merged PRs on that repository showed every single author was either a core-team member or the dependency-update bot: zero outside contributors merged, ever, in that window. Other recent external PRs from unrelated contributors had received the identical silent treatment.

## Rule

Before implementing a fix for an unsolicited external PR, run this check:

1. `gh pr list --repo <owner>/<repo> --state merged --limit 100 --json author` — collect the unique author logins.
2. For each unique login, confirm org membership: `gh api orgs/<org>/members/<login>` (204 = member, 404 = not a member) — or use employer/bio signals when the repo isn't org-owned.
3. Count how many of the last 100 merged PRs came from a genuinely external author (not an org member, not a bot).

Decision:

- **Fewer than ~20 merged PRs exist to sample** — inconclusive. State the small sample size and proceed with lower confidence rather than disqualifying; this check needs history to mean anything.
- **Zero or near-zero external authors** (a small handful out of 100, or zero) — disqualify the repo. Do not implement, do not open a PR. Record the finding with its evidence (author list, counts) so a later scouting pass doesn't repeat the mistake.
- **A healthy, recurring mix of external and internal authors** — proceed normally.

Also check `CONTRIBUTING.md` / the README for an explicit stated policy against external or AI-assisted contributions. An explicit policy disqualifies immediately regardless of merge-rate and doesn't need the count.

One instant, uncommented close on its own is not proof of a repo-wide policy — a single PR can be legitimately superseded by a competing PR, already fixed, or closed by an automated duplicate-detector (which typically *does* leave a comment naming what it duplicates). Only escalate to a full repo disqualification after confirming the pattern via the merge-count check, never from one incident alone.

## Distinguish from `external-pr-style`

This check answers "will this repo merge an outside PR at all," before any code is written. `external-pr-style` (write natural prose, avoid AI-tell headers) answers "how do I write the PR so a maintainer who *does* evaluate outside PRs on their merits doesn't reject it for style." Running the style skill correctly cannot fix a repo that has already failed this check — they solve different failure modes, checked in this order: viability first, then style.

## Record the finding

When a repo fails this check, write down what you found — the last-100-merged author list, the external-merge count, and the specific incident if one triggered the check — wherever your scouting or tracking system keeps a disqualified-repo list, so a later scouting pass doesn't rediscover the same repo the expensive way.

## Guardrails

- Never disqualify a repo from a single closed PR alone — confirm the pattern via the merge-count check first.
- Never fabricate the merge-count evidence — the decision must cite an actual command's real output, not an assumption or a guess made to move faster.
- Don't confuse a CLA/DCO requirement (a process gate, satisfiable by any contributor) with an external-merge policy (a categorical exclusion). CLA-gated repos can still be fully viable once the CLA is signed — check the actual merged-author mix, not just the presence of a CLA bot.
