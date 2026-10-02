import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "check-leaks.py"

spec = importlib.util.spec_from_file_location("check_leaks", SCRIPT_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Built at runtime so this file never contains a credential-shaped literal.
FAKE_GITHUB_TOKEN = "ghp_" + "A1b2C3d4E5" * 3 + "F6g7H8"
FAKE_FINE_GRAINED = "github_pat_" + "11ABCDEFG0" * 3
FAKE_SECRET_KEY = "sk-" + "proj-" + "a1B2c3D4e5" * 3


def flagged(line, denylist=()):
    return [message for _, message in mod.scan_line(line, list(denylist))]


def run_checker(*paths, denylist=None):
    env = {k: v for k, v in os.environ.items() if k != "LEAK_DENYLIST"}
    if denylist is not None:
        env["LEAK_DENYLIST"] = denylist
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *map(str, paths)],
        capture_output=True,
        text=True,
        env=env,
    )


class HomePathTest(unittest.TestCase):
    def test_flags_a_real_users_home_path(self):
        self.assertTrue(flagged("see /home/someuser/project/notes.md"))
        self.assertTrue(flagged("cd /Users/someone/code"))

    def test_allows_eval_sandbox_users(self):
        self.assertEqual(flagged("cp out.json /home/agent/work/"), [])
        self.assertEqual(flagged("HOME=/home/evaluator"), [])

    def test_sandbox_allowance_is_not_a_prefix_bypass(self):
        self.assertTrue(flagged("/home/agentsmith/x"))
        self.assertTrue(flagged("/home/evaluator2/x"))

    def test_allows_placeholders_and_url_paths(self):
        self.assertEqual(flagged("/home/<user>/project and /home/$USER/x"), [])
        self.assertEqual(flagged("https://example.com/home/docs"), [])


class TokenFilePathTest(unittest.TestCase):
    def test_flags_credential_stores_and_secret_named_home_files(self):
        for line in (
            "cat ~/.git-credentials",
            "read ~/.config/gh/hosts.yml",
            "token=$(cat $HOME/.secrets/github-token)",
            "export KEY=$(cat ~/.config/openai/api_key)",
            "cat ~/.github-pat",
        ):
            with self.subTest(line=line):
                self.assertTrue(flagged(line))

    def test_allows_ordinary_home_paths_and_secret_names(self):
        for line in (
            "~/.claude/settings.json",
            "$HOME/.config/git-identity-guard/config",
            "~/patches/fix.diff",
            "OCR_LLM_AUTH_TOKEN: ${{ secrets.OCR_LLM_AUTH_TOKEN }}",
        ):
            with self.subTest(line=line):
                self.assertEqual(flagged(line), [])


class CredentialPatternTest(unittest.TestCase):
    def test_flags_credential_shapes(self):
        for token in (FAKE_GITHUB_TOKEN, FAKE_FINE_GRAINED, FAKE_SECRET_KEY):
            with self.subTest(token=token[:6]):
                self.assertTrue(flagged(f"TOKEN={token}"))

    def test_ignores_words_and_identifiers_containing_sk_dash(self):
        for line in (
            "task-0123456789abcdefghij",
            "disk-usage-report-2026-10-02-final",
            "risk-level-assessment-for-release-1",
            "pip install sk-learn",
            "sk-some-long-kebab-case-identifier-name",
            "ghp_short",
        ):
            with self.subTest(line=line):
                self.assertEqual(flagged(line), [])

    def test_credential_is_redacted_in_the_report(self):
        (message,) = flagged(FAKE_GITHUB_TOKEN)
        self.assertNotIn(FAKE_GITHUB_TOKEN, message)


class DenylistTest(unittest.TestCase):
    def test_parses_newline_and_comma_separated_entries(self):
        self.assertEqual(mod.parse_denylist(" Alpha ,beta\n\n gamma,\n"), ["alpha", "beta", "gamma"])
        self.assertEqual(mod.parse_denylist(""), [])

    def test_matches_case_insensitively_without_echoing_the_entry(self):
        (message,) = flagged("uses the AcmeInternal database", ["acmeinternal"])
        self.assertEqual(message, "private denylist entry #1")


class AllowMarkerTest(unittest.TestCase):
    def test_marker_skips_a_reviewed_line(self):
        self.assertEqual(flagged("never read ~/.git-credentials  <!-- leak-check: allow -->"), [])


class CommandLineTest(unittest.TestCase):
    def test_fails_on_leaks_and_never_prints_secrets_or_denylist_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            leaky = Path(directory) / "leaky.md"
            leaky.write_text(
                "path: /home/someuser/x\n"
                f"token: {FAKE_GITHUB_TOKEN}\n"
                "db: acmeinternal_db\n"
            )
            result = run_checker(directory, denylist="AcmeInternal")

        self.assertEqual(result.returncode, 1)
        self.assertIn("leaky.md:1:7: absolute home path /home/someuser", result.stderr)
        self.assertIn("leaky.md:2:8: GitHub token", result.stderr)
        self.assertIn("leaky.md:3:5: private denylist entry #1", result.stderr)
        output = result.stdout + result.stderr
        self.assertNotIn(FAKE_GITHUB_TOKEN, output)
        self.assertNotIn("acmeinternal", output.lower())

    def test_flags_a_denylisted_file_name(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "acmeinternal-notes.md").write_text("clean\n")
            result = run_checker(directory, denylist="acmeinternal")

        self.assertEqual(result.returncode, 1)
        self.assertIn("file path matches private denylist entry #1", result.stderr)

    def test_passes_clean_files_and_skips_binaries(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "clean.md").write_text("cp out.json /home/agent/work/\n")
            (Path(directory) / "blob.bin").write_bytes(b"\0/home/someuser/x")
            result = run_checker(directory)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no denylist configured", result.stdout)


if __name__ == "__main__":
    unittest.main()
