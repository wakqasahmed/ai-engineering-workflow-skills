#!/usr/bin/env python3
"""token_savings_estimator.py — Estimate token-cost savings from caveman compression.

Stdlib-only. Uses a chars-per-token heuristic (4 chars/token average for English
prose; 3.5 for technical text) to estimate output tokens before vs after caveman
compression.

Why heuristic and not real tokenizer:
- No external dependencies (stdlib only)
- Tokenizer accuracy varies by model (cl100k_base vs o200k_base vs others)
- Heuristic is within 10-15% of real tokenizer output for English prose
- Reports both heuristic + character count so user can apply their own multiplier

Usage:
    python token_savings_estimator.py                         # uses embedded sample
    python token_savings_estimator.py "your text"
    python token_savings_estimator.py --file path/to/input.txt
    python token_savings_estimator.py "text" --output json
    python token_savings_estimator.py "text" --price-per-mtok 3.00
"""

import argparse
import json
import os
import sys
from typing import Any, Dict


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from caveman_compressor import SAMPLE_INPUT, compress  # noqa: E402


CHARS_PER_TOKEN_PROSE = 4.0
CHARS_PER_TOKEN_TECHNICAL = 3.5
TECHNICAL_TOKEN_INDICATORS = ("```", "{", "}", "()", "->", "==", "//", "/*", "import ", "function ")


def _estimate_chars_per_token(text: str) -> float:
    """Heuristic: technical text has more tokens per char than prose."""
    hit_count = sum(1 for indicator in TECHNICAL_TOKEN_INDICATORS if indicator in text)
    if hit_count >= 3:
        return CHARS_PER_TOKEN_TECHNICAL
    return CHARS_PER_TOKEN_PROSE


def estimate_tokens(text: str) -> int:
    return int(round(len(text) / _estimate_chars_per_token(text)))


def analyze(original: str, price_per_mtok: float = 0.0) -> Dict[str, Any]:
    compressed = compress(original)
    original_tokens = estimate_tokens(original)
    compressed_tokens = estimate_tokens(compressed)
    saved = original_tokens - compressed_tokens
    percent_saved = round(100.0 * saved / max(original_tokens, 1), 1)

    result: Dict[str, Any] = {
        "original_chars": len(original),
        "compressed_chars": len(compressed),
        "chars_per_token_used": _estimate_chars_per_token(original),
        "estimated_original_tokens": original_tokens,
        "estimated_compressed_tokens": compressed_tokens,
        "tokens_saved": saved,
        "percent_token_savings": percent_saved,
        "compressed_preview": compressed[:200] + ("..." if len(compressed) > 200 else ""),
    }

    if price_per_mtok > 0:
        cost_per_token = price_per_mtok / 1_000_000.0
        result["price_per_million_tokens"] = price_per_mtok
        result["cost_saved_per_response_usd"] = round(saved * cost_per_token, 6)
        result["cost_saved_per_1k_responses_usd"] = round(saved * cost_per_token * 1000, 4)

    return result


def render_text(result: Dict[str, Any]) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append("TOKEN SAVINGS ESTIMATOR (caveman compression)")
    lines.append("=" * 72)
    lines.append("")
    lines.append(f"Chars/token heuristic: {result['chars_per_token_used']:.1f} (prose=4.0; technical=3.5)")
    lines.append("")
    lines.append(
        f"Original:   {result['original_chars']} chars  "
        f"~ {result['estimated_original_tokens']} tokens"
    )
    lines.append(
        f"Compressed: {result['compressed_chars']} chars  "
        f"~ {result['estimated_compressed_tokens']} tokens"
    )
    lines.append("")
    lines.append(f"Savings: {result['tokens_saved']} tokens ({result['percent_token_savings']}%)")
    if "price_per_million_tokens" in result:
        lines.append("")
        lines.append(f"At ${result['price_per_million_tokens']}/Mtok:")
        lines.append(f"  Cost saved per response:   ${result['cost_saved_per_response_usd']:.6f}")
        lines.append(f"  Cost saved per 1k responses: ${result['cost_saved_per_1k_responses_usd']:.4f}")
    lines.append("")
    lines.append("-" * 72)
    lines.append("Compressed preview:")
    lines.append(f"  {result['compressed_preview']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Estimate token + cost savings from caveman compression.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    price_help = "Per-million-token price (USD) to estimate cost savings"
    parser.add_argument("text", nargs="?", help="Input text (uses embedded sample if omitted)")
    parser.add_argument("--file", help="Read input from file")
    parser.add_argument("--output", choices=("text", "json"), default="text", help="Output format")
    parser.add_argument("--price-per-mtok", type=float, default=0.0, help=price_help)
    args = parser.parse_args()

    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as file:
                original = file.read()
        except (IOError, OSError) as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
    elif args.text:
        original = args.text
    else:
        original = SAMPLE_INPUT

    result = analyze(original, args.price_per_mtok)
    if args.output == "json":
        print(json.dumps(result, indent=2))
    else:
        print(render_text(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
