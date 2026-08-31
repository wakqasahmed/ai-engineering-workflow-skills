# AI Engineering Workflow Skills

Canonical source for engineering workflow, product, and productivity skills.

**In plain terms:** you tell your agent what stage of a software change you're in — scoping it, defining done, breaking it into issues, reviewing before merge, releasing, or handing off context — and it routes to the matching engineering-workflow skill instead of improvising its own process each time.

## Install

Pick whichever fits how you work. All three end up in the same place: the skill files sitting where your agent looks for them.

### 1. Everything, via npx (recommended)

```bash
npx skills@latest add wakqasahmed/ai-engineering-workflow-skills
```

This installs every skill in the pack for whichever agent you're using (Claude Code, Cursor, Codex, and 70+ others — see the [`skills` CLI](https://github.com/vercel-labs/skills)). Add `-g` to install once for every project instead of per-project, or `-a claude-code` to target one agent specifically.

### 2. Just one skill

Don't need the whole pack? Install a single skill by its name (skill names match their folder, e.g. `clarify-work`):

```bash
npx skills@latest add wakqasahmed/ai-engineering-workflow-skills --skill clarify-work
```

Or point straight at one skill's folder on GitHub:

```bash
npx skills add https://github.com/wakqasahmed/ai-engineering-workflow-skills/tree/main/skills/engineering/clarify-work
```

### 3. No Node/npx available — manual zip install

1. On this repo's GitHub page: **Code → Download ZIP**.
2. Unzip it.
3. Copy whichever `skills/<category>/<name>/` folder(s) you want into your agent's own skills directory (for Claude Code, that's `.claude/skills/` in your project, or `~/.claude/skills/` for a global install; other agents use their own equivalent path).

No installer, no dependency — just files your agent already knows how to read.

## Use it — step by step

**Start with `workflow-router`** if you're not sure which skill applies — it routes a work request to the smallest applicable delivery workflow.

| Skill | What it covers |
|---|---|
| [`ai-agent-pr-metadata`](skills/engineering/ai-agent-pr-metadata/SKILL.md) | Add GitHub-visible AI agent and AI code-review metadata and exact agent labels without adding AI attribution to commits, and scope Alibaba/Open Code Review's review surface to control LLM token spend. |
| [`changesets-release`](skills/engineering/changesets-release/SKILL.md) | Records release intent with Changesets and guides semver, changelog, CI, and artifact-version checks for independently distributed packages. |
| [`clarify-work`](skills/engineering/clarify-work/SKILL.md) | Clarify non-trivial engineering work before implementation by resolving ambiguity, terminology, constraints, and the smallest viable path. |
| [`decompose-to-issues`](skills/engineering/decompose-to-issues/SKILL.md) | Break high-level work into independently executable GitHub issues using vertical slices. |
| [`define-done`](skills/engineering/define-done/SKILL.md) | Define acceptance criteria, risk level, and verification before editing. |
| [`hitl-blocker`](skills/engineering/hitl-blocker/SKILL.md) | Convert human-only blockers into visible GitHub issues. |
| [`open-code-review-setup`](skills/engineering/open-code-review-setup/SKILL.md) | Set up Alibaba Open Code Review (OCR) on a repository that lacks it, or audit and update an existing setup. |
| [`release-gate`](skills/engineering/release-gate/SKILL.md) | Check deployment, staging, rollback, and health verification before release. |
| [`review-gate`](skills/engineering/review-gate/SKILL.md) | Run an independent semantic review gate before merging non-trivial work, on top of (not duplicating) Alibaba Code Review and CI. |
| [`subagent-pipeline`](skills/engineering/subagent-pipeline/SKILL.md) | Run a cold-start implementer, reviewer, and fixer subagent chain for one issue, gated by CI, ending in a staging PR. |
| [`to-prd`](skills/engineering/to-prd/SKILL.md) | Synthesize the current conversation and repository context into a concise product and engineering spec, publish it to the project issue tracker, and gate agent readiness before decomposition. |
| [`workflow-router`](skills/engineering/workflow-router/SKILL.md) | Routes a software-work request to the smallest applicable delivery workflow and records repository conventions once. |
| [`write-prompt-guide`](skills/engineering/write-prompt-guide/SKILL.md) | Produce a pack-specific `PROMPT_GUIDE.md` that teaches end users what to type to get a good run out of one Agent Skill pack, from that pack's own `SKILL.md`, README, and open issues. |
| [`roast`](skills/product/roast/SKILL.md) | Use when someone asks to roast an idea, pressure-test or stress-test an idea, validate a business idea, "convene the council", get a brutal second opinion before building something, or says "/roast". |
| [`handover`](skills/productivity/handover/SKILL.md) | Compact the current conversation into a handover document a fresh agent can pick up and continue seamlessly. |

## Contents

The installable skills live in [`skills/engineering/`](skills/engineering/), [`skills/filament/`](skills/filament/), [`skills/product/`](skills/product/), and [`skills/productivity/`](skills/productivity/).

## Sources

Skills whose methodology rests on first-party vendor documentation cite it in [`SOURCES.md`](SOURCES.md), a ledger of publisher, URL, and the specific claims each source supports.

## Aggregate catalogue

Changes merged to this repository are automatically synchronized to [wakqasahmed/skills](https://github.com/wakqasahmed/skills). Treat this repository as the source of truth for engineering workflow skills.

## Outcome-eval harness status

Several skills already have a deterministic eval layer (free, runs on every PR). The gated model-harness layer — real skill-enabled vs. disabled comparisons against a live model — is still open work for 8 skills: [#57](https://github.com/wakqasahmed/ai-engineering-workflow-skills/issues/57), [#59](https://github.com/wakqasahmed/ai-engineering-workflow-skills/issues/59)–[#65](https://github.com/wakqasahmed/ai-engineering-workflow-skills/issues/65).

### Fund the real harness runs

This skill's deterministic checks run free on every PR. Proving its outcome-eval harness with real, metered model calls costs money:

- **Bitcoin (BTC):** `bc1p5xqamscrz7nu0d8jdmj748rj75sk8khtyxypn3qvsdjms4t4uw2qsjn0he`
- **Ethereum (ETH) / any ERC-20 including stablecoins:** `0x59bc573e414D62d44461234dEf438247dfc3Cf6A`

Double-check every character against this page before sending. Full portfolio picture and rationale: [wakqasahmed/skills](https://github.com/wakqasahmed/skills#fund-the-real-harness-runs).
