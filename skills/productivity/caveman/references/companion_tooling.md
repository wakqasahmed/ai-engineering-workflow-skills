# Companion Tooling

Compression tools layered on top of Matt Pocock's caveman skill.

## Validation Tools (stdlib Python)

| Tool | Purpose | Run when |
|---|---|---|
| [`scripts/caveman_compressor.py`](../scripts/caveman_compressor.py) | Apply Matt's rules deterministically (drop articles/filler/pleasantries/hedging, abbreviate technical terms, use causality arrows) | Want a starting compressed version of any text |
| [`scripts/token_savings_estimator.py`](../scripts/token_savings_estimator.py) | Estimate token + cost savings using 4 chars/token (prose) or 3.5 chars/token (technical) heuristic | Want to quantify the value of caveman mode |
| [`scripts/caveman_lint.py`](../scripts/caveman_lint.py) | Detect banned vocabulary in a response (pleasantries, filler, hedging, metatalk, verbose phrases). Whitelist: code blocks, inline code, quoted strings, exception zones | Verify a response complies with caveman rules |

All three tools:
- Stdlib-only (no external dependencies)
- Run with embedded sample if no input provided
- Output text or JSON (`--output json`)
- Code blocks + inline code preserved (compression skips them)

## Token-Savings Heuristic

The estimator uses character-per-token approximations:
- **4.0 chars/token** for English prose
- **3.5 chars/token** for technical text (detected by presence of `{`, `}`, `()`, `->`, `==`, `//`, etc.)

This is within 10-15% of cl100k_base / o200k_base tokenizers for English. For exact token counts use the model's actual tokenizer (e.g., `tiktoken`).

## When Caveman Backfires (See main SKILL.md "Auto-Clarity Exception")

The compressor + lint tool both recognize these exception zones — Matt's rule is explicit:
- Security warnings
- Irreversible action confirmations
- Multi-step sequences where fragment order risks misread
- User asks to clarify or repeats question

The tools detect `**Warning:**`, `destructive`, `irreversible`, and `cannot be undone` markers. The compressor leaves marked input unchanged; the linter softens its verdict accordingly. The remaining exception zones require agent judgment.

## Why Include the Fork's Tools

Matt's caveman skill is tight + complete. The immediate `alirezarezvani/claude-skills` adaptation adds:
1. **Deterministic compression** — apply rules consistently across responses (not just in spirit)
2. **Quantification** — show ROI of caveman mode in tokens/dollars
3. **Compliance checking** — verify a response actually follows rules (vs claiming to)

## Attribution

Immediate source: [alirezarezvani/claude-skills — caveman](https://github.com/alirezarezvani/claude-skills/tree/main/engineering/caveman/skills/caveman) (MIT).

Original: Matt Pocock's historical [`skills/productivity/caveman`](https://github.com/mattpocock/skills/tree/main/skills/productivity/caveman) skill (MIT; no longer present in the live repository).

---

**Source authorities (non-exhaustive):**

- **Matt Pocock — caveman** ([mattpocock/skills](https://github.com/mattpocock/skills), MIT) — the upstream source
- **Anthropic — Token usage best practices** (https://docs.claude.com/en/docs/build-with-claude/prompt-engineering) — token-conscious prompting
- **OpenAI tokenizer docs** — `tiktoken` library + cl100k_base / o200k_base heuristics
- **Strunk & White — "The Elements of Style"** (1918) — "omit needless words"; foundational text on prose compression
- **Plain Language Movement / Plain Writing Act of 2010** — federal mandate for concise government writing
- **Norman, D. — "Living with Complexity"** (2010) — when simplicity helps vs hurts cognition
- **Pareto principle in communication** — 20% of words carry 80% of information density
