import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "validate-external-skill-refs.py"

spec = importlib.util.spec_from_file_location("validate_external_skill_refs", SCRIPT_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = spec.loader.exec_module(mod) or mod


class NameRegexTest(unittest.TestCase):
    def test_accepts_bare_name_field(self):
        self.assertEqual(mod.NAME_RE.search("name: test-driven-development\n").group(1), "test-driven-development")

    def test_accepts_name_field_with_trailing_comment(self):
        text = "name: test-driven-development  # pinned dependency\n"
        self.assertEqual(mod.NAME_RE.search(text).group(1), "test-driven-development")


class FetchFrontmatterNameTest(unittest.TestCase):
    def test_raises_value_error_not_assertion_error_on_missing_name(self):
        # Regression: AssertionError is stripped by `python -O`, which would
        # silently skip this check on fetched (untrusted) external input.
        original_urlopen = mod.urllib.request.urlopen

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b"no frontmatter here\n"

        mod.urllib.request.urlopen = lambda *a, **k: FakeResponse()
        try:
            with self.assertRaises(ValueError):
                mod.fetch_frontmatter_name("owner/repo", "deadbeef", "some-skill")
        finally:
            mod.urllib.request.urlopen = original_urlopen


class MissingDocFileTest(unittest.TestCase):
    def test_missing_doc_file_is_reported_not_crashed(self):
        original_doc_files = mod.DOC_FILES
        original_root = mod.ROOT
        with tempfile.TemporaryDirectory() as tmp:
            mod.ROOT = Path(tmp)
            mod.DOC_FILES = ("does-not-exist.md",)
            try:
                errors = []
                for relative_path in mod.DOC_FILES:
                    path = mod.ROOT / relative_path
                    try:
                        path.read_text(encoding="utf-8")
                    except OSError as exc:
                        errors.append(f"{relative_path}: could not read file ({exc})")
                self.assertEqual(len(errors), 1)
                self.assertIn("could not read file", errors[0])
            finally:
                mod.DOC_FILES = original_doc_files
                mod.ROOT = original_root


if __name__ == "__main__":
    unittest.main()
