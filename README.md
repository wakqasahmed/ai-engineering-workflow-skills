# AI Engineering Workflow Skills [![skills.sh](https://skills.sh/b/wakqasahmed/ai-engineering-workflow-skills)](https://skills.sh/wakqasahmed/ai-engineering-workflow-skills)

Practical engineering workflow skills for clarifying work, defining done, decomposing scope, gating reviews and releases, and preserving handoffs when context has to cross agents or sessions.

## Install

```bash
npx skills@latest add wakqasahmed/ai-engineering-workflow-skills
```

Local Claude CLI fallback:

```bash
scripts/list-skills.sh
scripts/link-skills.sh
```

## Skills

- `clarify-work`: resolve ambiguity before implementation starts.
- `define-done`: lock acceptance criteria, risk, and verification before editing.
- `decompose-to-issues`: split broad work into issue-sized vertical slices.
- `review-gate`: enforce an independent review pass before merge.
- `release-gate`: enforce deployment, rollback, and health checks before release.
- `workflow-handoff`: preserve compact state when work crosses agents or sessions.
- `hitl-blocker`: turn missing human-held access into explicit GitHub issues.
- `setup-matt-pocock-skills`: configure per-repo issue tracker, triage labels, and domain doc layout.

## Why This Exists

This pack turns the workflow from `AI_ENGINEERING_WORKFLOW.md` into installable skills instead of keeping it as guidance only. The docs remain useful for humans; the skill folders are the install surface for `skills.sh` and compatible tooling.

## Marketplace And Discovery

- Public install command: `npx skills@latest add wakqasahmed/ai-engineering-workflow-skills`
- skills.sh page: `https://skills.sh/wakqasahmed/ai-engineering-workflow-skills`
- GitHub repo: `https://github.com/wakqasahmed/ai-engineering-workflow-skills`
