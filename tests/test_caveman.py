import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "productivity" / "caveman"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class CavemanCompressorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compressor = load_module("caveman_compressor", "caveman_compressor.py")

    def test_compresses_filler_articles_terms_and_causality(self):
        compressed = self.compressor.compress(
            "Certainly, the database actually leads to a configuration problem."
        )

        self.assertEqual(compressed, "DB -> config problem.")

    def test_preserves_code_and_quoted_strings_exactly(self):
        text = (
            "The function uses `the actual value` and says \"the actual value\".\n"
            "Use 'the actual value' exactly.\n"
            "```python\nvalue = 'the actual value'\n```"
        )

        compressed = self.compressor.compress(text)

        self.assertIn("`the actual value`", compressed)
        self.assertIn('"the actual value"', compressed)
        self.assertIn("'the actual value'", compressed)
        self.assertIn("```python\nvalue = 'the actual value'\n```", compressed)

    def test_does_not_convert_causality_nouns_to_arrows(self):
        cases = {
            "Root cause analysis shows the DB is slow.": "Root cause analysis shows DB is slow.",
            "The cause is unclear.": "cause is unclear.",
            "Lead time for the request is 200ms.": "Lead time for req is 200ms.",
            "Two leads are cold.": "Two leads are cold.",
        }

        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(self.compressor.compress(text), expected)

    def test_preserves_newlines_around_code_fences(self):
        text = "Fix the bug:\n\n```python\nx = 1\n```\n\nThen run the app."

        compressed = self.compressor.compress(text)

        self.assertIn("\n```python\n", compressed)
        self.assertIn("\n```\n", compressed)

    def test_does_not_protect_prose_between_decade_and_contraction_apostrophes(self):
        text = "Ship it in the '90s. The database is really the actual thing, don't ask."

        self.assertEqual(
            self.compressor.compress(text),
            "Ship it in '90s. DB is thing, don't ask.",
        )

    def test_preserves_single_letter_operand_before_operator(self):
        self.assertEqual(
            self.compressor.compress("Check a == b before the request."),
            "Check a == b before req.",
        )

    def test_uses_only_documented_conservative_abbreviations(self):
        text = (
            "Databases authorization configurations requests responses functions "
            "implementations applications."
        )

        self.assertEqual(self.compressor.compress(text), text)

    def test_preserves_sentence_initial_capitalization_when_abbreviating(self):
        self.assertEqual(
            self.compressor.compress("The Response was fine."),
            "Res was fine.",
        )

    def test_leaves_warning_context_uncompressed(self):
        warning = "**Warning:** This irreversible action cannot be undone."

        self.assertEqual(self.compressor.compress(warning), warning)

    def test_does_not_remove_phrase_fragments_inside_words(self):
        self.assertEqual(self.compressor.compress("Ensure the database works."), "Ensure DB works.")


class CavemanLintTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lint = load_module("caveman_lint", "caveman_lint.py")

    def test_flags_banned_phrases_outside_literals(self):
        result = self.lint.analyze("Certainly, this is actually simple. Maybe retry.")

        self.assertEqual(result["verdict"], "FAIL")
        self.assertGreater(result["total_violations"], 2)

    def test_ignores_banned_phrases_in_code_and_quoted_strings(self):
        result = self.lint.analyze(
            "Use `maybe actually` and preserve \"certainly, just\".\n"
            "```text\nperhaps basically\n```"
        )

        self.assertEqual(result["verdict"], "CLEAN")
        self.assertEqual(result["total_violations"], 0)

    def test_softens_violations_in_auto_clarity_context(self):
        result = self.lint.analyze(
            "**Warning:** This destructive action cannot be undone. "
            "It is actually important and perhaps irreversible."
        )

        self.assertTrue(result["has_exception_context"])
        self.assertEqual(result["verdict"], "WARN")

    def test_detects_pleasantries_ending_in_punctuation(self):
        result = self.lint.analyze("Sure! No problem!")

        self.assertEqual(result["total_violations"], 2)
        self.assertEqual(result["verdict"], "FAIL")

    def test_exception_context_only_softens_its_own_paragraph(self):
        result = self.lint.analyze(
            "**Warning:** This destructive action cannot be undone. It is actually serious.\n\n"
            "Sure. Certainly. Of course. No problem. Maybe just really basically actually "
            "simply probably retry."
        )

        self.assertTrue(result["has_exception_context"])
        self.assertEqual(result["verdict"], "FAIL")

    def test_detects_bare_pleasantry_shared_with_compressor(self):
        result = self.lint.analyze("Sure. Fix auth.")

        self.assertEqual(result["total_violations"], 1)
        self.assertEqual(result["verdict"], "FAIL")

    def test_warn_exit_code_is_success(self):
        warning = (
            "**Warning:** This destructive action cannot be undone. "
            "It is actually important."
        )

        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "caveman_lint.py"), warning],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)


class TokenSavingsEstimatorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.estimator = load_module(
            "token_savings_estimator", "token_savings_estimator.py"
        )

    def test_estimates_positive_savings_and_cost(self):
        result = self.estimator.analyze(
            "Certainly, the database is actually a really useful database.",
            price_per_mtok=3.0,
        )

        self.assertGreater(result["tokens_saved"], 0)
        self.assertGreater(result["percent_token_savings"], 0)
        self.assertIn("cost_saved_per_response_usd", result)

    def test_uses_technical_heuristic_after_three_indicators(self):
        text = "function demo() { return left == right; } // check"

        self.assertEqual(self.estimator._estimate_chars_per_token(text), 3.5)

    def test_shorter_compression_never_reports_negative_savings(self):
        result = self.estimator.analyze(
            "Object {} leads to serious runtime drift under sustained heavy production load.",
            price_per_mtok=3.0,
        )

        self.assertLessEqual(result["compressed_chars"], result["original_chars"])
        self.assertGreaterEqual(result["tokens_saved"], 0)
        self.assertGreaterEqual(result["cost_saved_per_response_usd"], 0)

    def test_uses_original_text_divisor_for_both_token_estimates(self):
        original = "Object {} leads to serious runtime drift under sustained heavy production load."
        compressed = self.estimator.compress(original)
        result = self.estimator.analyze(original)
        divisor = result["chars_per_token_used"]

        self.assertNotEqual(
            self.estimator._estimate_chars_per_token(original),
            self.estimator._estimate_chars_per_token(compressed),
        )
        self.assertEqual(
            result["estimated_original_tokens"],
            int(round(result["original_chars"] / divisor)),
        )
        self.assertEqual(
            result["estimated_compressed_tokens"],
            int(round(result["compressed_chars"] / divisor)),
        )


class CavemanCliTest(unittest.TestCase):
    def assert_invalid_utf8_file_is_reported_cleanly(self, script):
        with tempfile.NamedTemporaryFile(dir=ROOT, suffix=".bin") as invalid_file:
            invalid_file.write(b"\xff\xfe\x80")
            invalid_file.flush()
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / script), "--file", invalid_file.name],
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_compressor_file_decode_error_is_clean(self):
        self.assert_invalid_utf8_file_is_reported_cleanly("caveman_compressor.py")

    def test_linter_file_decode_error_is_clean(self):
        self.assert_invalid_utf8_file_is_reported_cleanly("caveman_lint.py")

    def test_estimator_file_decode_error_is_clean(self):
        self.assert_invalid_utf8_file_is_reported_cleanly("token_savings_estimator.py")


class CavemanSkillContractTest(unittest.TestCase):
    def test_preserves_persistence_and_auto_clarity_contract(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text()
        required_terms = (
            "ACTIVE EVERY RESPONSE once triggered",
            'Off only when user says "stop caveman" or "normal mode"',
            "security warnings",
            "irreversible action confirmations",
            "multi-step sequences where fragment order risks misread",
            "user asks to clarify or repeats question",
            "Resume caveman after clear part done",
        )

        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, skill)

        self.assertRegex(skill, r"(?m)^## Persistence$")
        self.assertRegex(skill, r"(?m)^## Auto-Clarity Exception$")

    def test_skill_is_explicitly_invoked_with_accurate_description(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text()

        self.assertIn("disable-model-invocation: true", skill)
        self.assertRegex(
            skill,
            r"(?m)^description: User-invoked persistent ultra-compressed communication mode",
        )
        self.assertNotIn("description: >", skill)
        self.assertNotIn("~75%", skill.split("---", 2)[1])

    def test_trigger_and_exit_wording_matches_all_entrypoints(self):
        routing = (
            "Use `caveman` only when the user explicitly asks for caveman mode or "
            "ultra-compressed replies; keep it active until the user says \"stop caveman\" "
            "or \"normal mode\", except for Auto-Clarity safety cases."
        )

        for path in (ROOT / "AGENTS.md", ROOT / "CLAUDE.md", ROOT / "README.md"):
            with self.subTest(path=path.name):
                self.assertIn(routing, path.read_text())

        readme = (ROOT / "README.md").read_text()
        self.assertRegex(
            readme,
            r"\| \[`caveman`\].*\| User-invoked persistent ultra-compressed",
        )

    def test_attribution_links_notice_and_eval_entry_are_pinned(self):
        pinned_source = (
            "https://github.com/mattpocock/skills/blob/"
            "221ffca96736afefdc08ca7cf0b3965e9ea83f41/"
            "skills/productivity/caveman/SKILL.md"
        )
        source_files = (
            SKILL_ROOT / "SKILL.md",
            SKILL_ROOT / "references" / "companion_tooling.md",
            ROOT / "skills" / "engineering" / "external-pr-style" / "SKILL.md",
        )

        self.assertEqual(
            sum(path.read_text().count(pinned_source) for path in source_files),
            4,
        )
        notice = (ROOT / "NOTICE").read_text()
        self.assertIn("Copyright (c) 2026 Matt Pocock", notice)
        self.assertIn("Copyright (c) 2025 Alireza Rezvani", notice)

        eval_readme = (ROOT / "eval" / "README.md").read_text()
        self.assertIn(
            "| `caveman` | `eval/productivity/caveman/` | Not yet tracked |",
            eval_readme,
        )
        self.assertTrue((ROOT / "eval" / "productivity" / "caveman" / "run-eval.sh").is_file())


if __name__ == "__main__":
    unittest.main()
