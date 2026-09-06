# Prose Compression Word List

This reference document defines words, phrases, and padding to strip during prose compression passes, shared by `external-pr-style` and `ai-agent-pr-metadata`.

## Words & Phrases to Strip

- **Pleasantries & Hedging**:
  - "I'd be happy to..."
  - "Please note that..."
  - "It's worth mentioning that..."
  - "Certainly..."
  - "Of course..."
  - "I believe..."
  - "Feel free to..."

- **Filler Intensifiers**:
  - "just"
  - "really"
  - "basically"
  - "actually"
  - "simply"
  - "essentially"

- **Redundant Context**:
  - Restating the issue title or PR title word-for-word.
  - "As described in the issue..."
  - Narrating obvious file edits that the diff already demonstrates.

## Punctuation Tells

- **Em dash (`U+2014`)**: Used as a default connector or aside marker, it is a tell. Rewrite with a period, comma, colon, or parentheses. See external-pr-style's [Em dashes are a tell](../SKILL.md#em-dashes-are-a-tell) for the full evidence and one-per-body ceiling.

## Compression Discipline

- Keep full sentences, articles, and natural grammatical flow (do not use fragmented "caveman" style).
- Ensure every sentence that remains carries distinct, load-bearing information.
- Write concisely, the way an experienced engineer writes in technical discussions.
