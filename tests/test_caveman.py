import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "productivity" / "caveman"
SCRIPTS = SKILL_ROOT / "scripts"


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
            "Certainly, the database actually causes a configuration problem."
        )

        self.assertEqual(compressed, "DB -> config problem.")

    def test_preserves_code_and_quoted_strings_exactly(self):
        text = (
            "The function uses `the actual value` and says \"the actual value\".\n"
            "```python\nvalue = 'the actual value'\n```"
        )

        compressed = self.compressor.compress(text)

        self.assertIn("`the actual value`", compressed)
        self.assertIn('"the actual value"', compressed)
        self.assertIn("```python\nvalue = 'the actual value'\n```", compressed)

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
        self.assertEqual(result["verdict"], "WARN")


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


if __name__ == "__main__":
    unittest.main()
