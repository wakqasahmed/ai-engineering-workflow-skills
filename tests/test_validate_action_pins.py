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


if __name__ == "__main__":
    unittest.main()
