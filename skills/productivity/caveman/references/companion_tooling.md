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

The linter exits `0` for `CLEAN` and `WARN`; only `FAIL` exits `1`.

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

The tools detect `**Warning:**`, `destructive`, `irreversible`, and `cannot be undone` markers. The compressor leaves marked input unchanged. The linter softens violations only inside the marked paragraph; violations elsewhere still produce `FAIL`. The remaining exception zones require agent judgment.

## Why Include the Fork's Tools

Matt's caveman skill is tight + complete. The immediate `alirezarezvani/claude-skills` adaptation adds:
1. **Deterministic compression** — apply rules consistently across responses (not just in spirit)
2. **Quantification** — show ROI of caveman mode in tokens/dollars
3. **Compliance checking** — verify a response actually follows rules (vs claiming to)

## Attribution

Immediate source: [alirezarezvani/claude-skills — caveman](https://github.com/alirezarezvani/claude-skills/tree/main/engineering/caveman/skills/caveman) (MIT).

Original: Matt Pocock's historical [`skills/productivity/caveman`](https://github.com/mattpocock/skills/blob/221ffca96736afefdc08ca7cf0b3965e9ea83f41/skills/productivity/caveman/SKILL.md) skill (MIT; no longer present in the live repository).
