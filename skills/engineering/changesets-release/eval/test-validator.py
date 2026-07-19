#!/usr/bin/env python3
"""Exercise the outcome validator with deterministic synthetic trial records."""
import json
import importlib.util
import subprocess
import tempfile
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
CASES = json.loads((EVAL_DIR / "fixtures" / "held-out.json").read_text())["cases"]

HARNESS_SPEC = importlib.util.spec_from_file_location("changesets_harness", EVAL_DIR / "run_harness.py")
HARNESS = importlib.util.module_from_spec(HARNESS_SPEC)
HARNESS_SPEC.loader.exec_module(HARNESS)


def record(case: dict, condition: str, trial: int) -> dict:
    return {
        "case_id": case["id"],
        "condition": condition,
        "trial": trial,
        "model": "test-model",
        "skill_used": case["expected_skill_usage"],
        "outcome": case["expected_outcome"],
        "safety_outcome": case["expected_safety_outcome"],
    }


harness_command = HARNESS.isolated_command(Path("/tmp/eval"), "evaluator@sha256:test", "echo '{}'", "enabled", 1, "test-model")
if "HOME=/home/evaluator" not in harness_command or not any(
    argument == "type=bind,source=/tmp/eval/home,target=/home/evaluator" for argument in harness_command
):
    raise SystemExit("harness does not mount and select an empty evaluator home")


with tempfile.TemporaryDirectory() as directory:
    directory = Path(directory)
    results = []
    for case in CASES:
        for condition in ("enabled", "disabled"):
            for trial in range(1, 6):
                item = record(case, condition, trial)
                if condition == "disabled":
                    item["outcome"] = "incorrect_without_skill"
                results.append(item)
    results_path = directory / "results.json"
    summary_path = directory / "summary.json"
    results_path.write_text(json.dumps(results))
    subprocess.run(
        ["python3", str(EVAL_DIR / "validate-harness-results.py"), str(results_path), "--summary", str(summary_path)],
        check=True,
    )
    summary = json.loads(summary_path.read_text())
    if not summary["pass"] or summary["outcome_delta"] < 0.02:
        raise SystemExit("validator did not report the expected enabled outcome improvement")

    for item in results:
        if item["condition"] == "enabled":
            item["skill_used"] = "unreported"
    results_path.write_text(json.dumps(results))
    subprocess.run(
        ["python3", str(EVAL_DIR / "validate-harness-results.py"), str(results_path), "--summary", str(summary_path)],
        check=True,
    )
    if not json.loads(summary_path.read_text())["pass"]:
        raise SystemExit("validator scored skill usage metadata as an outcome")

    results[0]["safety_outcome"] = "unsafe_enabled_result"
    results_path.write_text(json.dumps(results))
    failed = subprocess.run(
        ["python3", str(EVAL_DIR / "validate-harness-results.py"), str(results_path), "--summary", str(summary_path)],
        capture_output=True,
        text=True,
    )
    if failed.returncode == 0 or "safety outcome rate regresses" not in failed.stdout:
        raise SystemExit("validator did not reject an enabled safety regression")

print("PASS: Changesets outcome validator")
