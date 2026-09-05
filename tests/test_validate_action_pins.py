import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate-action-pins.py"
FIXTURE = ROOT / "tests" / "fixtures" / "pinned-action.yml"


class ValidateActionPinsTest(unittest.TestCase):
    def test_accepts_full_commit_sha(self):
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), str(FIXTURE)],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_mutable_ref_with_file_and_line(self):
        mutable_workflow = FIXTURE.read_text().replace(
            "d23441a48e516b6c34aea4fa41551a30e30af803", "v6"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as temporary_directory:
            workflow = Path(temporary_directory) / "workflow.yml"
            workflow.write_text(mutable_workflow)
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), str(workflow)],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"{workflow}:4", result.stderr)
        self.assertIn("actions/checkout@v6", result.stderr)

    def test_rejects_mutable_ref_behind_a_quoted_uses_key(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as temporary_directory:
            workflow = Path(temporary_directory) / "workflow.yml"
            workflow.write_text(
                "name: Bad\n"
                "on: push\n"
                "jobs:\n"
                "  build:\n"
                "    steps:\n"
                "      - 'uses': attacker/action@main\n"
            )
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), str(workflow)],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("attacker/action@main", result.stderr)

    def test_accepts_pinned_ref_behind_a_quoted_uses_key(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as temporary_directory:
            workflow = Path(temporary_directory) / "workflow.yml"
            workflow.write_text(
                "name: OK\n"
                "on: push\n"
                "jobs:\n"
                "  build:\n"
                "    steps:\n"
                "      - 'uses': "
                "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803\n"
            )
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), str(workflow)],
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_mutable_ref_inside_a_quoted_value_containing_a_hash(self):
        # A quoted `uses` value can legally contain a literal '#' or space;
        # an unquoted-boundary-aware regex must not stop at that '#' and
        # validate a truncated (and coincidentally SHA-shaped) prefix instead
        # of the real, unpinned reference.
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as temporary_directory:
            workflow = Path(temporary_directory) / "workflow.yml"
            workflow.write_text(
                "name: Bad\n"
                "on: push\n"
                "jobs:\n"
                "  build:\n"
                "    steps:\n"
                '      - uses: "attacker/action@main # not a sha"\n'
            )
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), str(workflow)],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("attacker/action@main", result.stderr)

    def test_skips_local_actions_referenced_by_absolute_or_parent_path(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as temporary_directory:
            workflow = Path(temporary_directory) / "workflow.yml"
            workflow.write_text(
                "name: OK\n"
                "on: push\n"
                "jobs:\n"
                "  build:\n"
                "    steps:\n"
                "      - uses: ../shared-actions/build\n"
                "      - uses: /opt/actions/deploy\n"
            )
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), str(workflow)],
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_reports_undecodable_file_instead_of_crashing(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as temporary_directory:
            workflow = Path(temporary_directory) / "workflow.yml"
            workflow.write_bytes(b"uses: actions/checkout@\xff\xfe binary garbage")
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), str(workflow)],
                capture_output=True,
                text=True,
            )

        # A file that can't be decoded fails loud (not silently skipped) —
        # skipping it would let an unpinned action hide behind bad encoding.
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("could not read file", result.stderr)

    def test_reports_missing_path_instead_of_crashing(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as temporary_directory:
            missing = Path(temporary_directory) / "does-not-exist.yml"
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), str(missing)],
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("does not exist", result.stderr)


if __name__ == "__main__":
    unittest.main()
