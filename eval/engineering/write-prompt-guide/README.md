# Write prompt guide outcome evaluation

`bash run-eval.sh --dry-run` is the offline PR-CI layer. It validates the non-negotiable `SKILL.md` contract, checks that all four cited provider-documentation URLs are still present in the repo-level `SOURCES.md`, and runs `validate-guide.py` over the held-out corpus in a disposable, network-disabled workspace that mirrors the repo's own directory layout. `check-contract.py` resolves its inputs from the repo root, so it also runs standalone (`python3 eval/engineering/write-prompt-guide/check-contract.py`). It does not score agent behavior.

`validate-guide.py` is the structural validator the skill's own step 4 refers to. Given a generated `PROMPT_GUIDE.md` and the target pack's own documentation text, it reports: missing required sections (quick start, context, structuring, prompt pairs, limitations, where to go deeper), fewer than two less-effective/more-effective prompt pairs, an absent copy-pasteable fenced prompt, a limitations section that is dismissive, thinner than two substantive disclosed limitations (25 words), or missing an issue/PR reference on any one limitation, a fix claim (`fixed`, `resolved`, `shipped`, `landed`, `addressed`, `merged`, `no longer an issue`, …) not hedged with its merge state *within the same sentence*, backtick-quoted capability names absent from the target pack's documentation, and plain-prose capability assertions ("the pack can also …") that name no capability the pack ships. It is importable, and its CLI takes the pack's real doc files: `python3 validate-guide.py PROMPT_GUIDE.md ../pack/SKILL.md ../pack/README.md`.

The capability vocabulary is **derived from the pack's documentation**, not supplied by the caller. There is no `allowed_terms` input, so a run cannot legitimise its own invention by declaring it; the only code-side exemption is a fixed list of generic hyphenated English (`multi-phase`, `copy-pasteable`, …) that no caller can extend.

## What it does not check

- **Merge state offline.** `#N` references are only checked for presence and per-limitation attachment in the default offline mode. Pass `--verify-refs <owner>/<repo>` to resolve every reference through `gh` and fail any already-merged PR presented as an open limitation; that mode needs network and is deliberately not part of `run-eval.sh --dry-run`.
- **Semantic truth of prose.** A prose capability claim that names a real skill is accepted even if the specific behaviour it describes is wrong. Grounding is name-level, not claim-level.
- **Agent behavior.** This is a structural contract check, not an outcome score.

## Corpus

The fifteen held-out cases exercise: a complete passing guide, a happy-path-only guide with no limitations section, a guide with no quick start, a guide with only one prompt pair, a guide naming a skill the target pack does not ship, a guide presenting an unmerged PR's fix as shipped, a limitations section with only vague prose and no issue links, a guide whose prompts are prose rather than copy-pasteable blocks, a guide with no multi-phase structuring section, a guide that never points back at the pack's own docs, and the five guardrail bypasses found in review: a fix claimed with a synonym verb, a hedge laundered from a neighbouring bullet, a gutted limitations section, a capability fabricated in prose, and a capability fabricated in backticks that a caller previously allow-listed.

`check-contract.py` re-runs those five bypasses as `BYPASS_PROBES` independently of the fixture corpus, so weakening the validator fails CI even if someone rewrites the fixtures. It also requires the manifest to carry a fabricated-capability case and an unmerged-fix case.

Held-out fixtures are synthetic and must not be used to tune `SKILL.md`; `tuning.json` is separate, and a guide whose normalized text appears in both corpora is rejected.
