#!/usr/bin/env python3
"""Exercise artifact-based outcome validation."""
import json
import subprocess
import tempfile
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
CASES = json.loads((EVAL_DIR / "fixtures" / "held-out.json").read_text())["cases"]

def record(case: dict, condition: str, trial: int) -> dict:
    events = [{"argv": event} for event in case["expected_artifact"]["required_events"]] if condition == "enabled" else []
    return {"case_id": case["id"], "condition": condition, "trial": trial,
            "outcome": "claimed_success", "safety_outcome": "claimed_safe",
            "artifact": {"events": events}}

def main() -> int:
    records = []
    for case in CASES:
        for condition in ("enabled", "disabled"):
            for trial in range(1, 6):
                records.append(record(case, condition, trial))
    with tempfile.TemporaryDirectory() as directory:
        results, summary = Path(directory) / "results.json", Path(directory) / "summary.json"
        results.write_text(json.dumps(records))
        subprocess.run(["python3", str(EVAL_DIR / "validate-harness-results.py"), str(results), "--summary", str(summary)], check=True)
        if not json.loads(summary.read_text())["pass"]:
            raise SystemExit("expected known-good comparison to pass")
        for record_item in records[:5]:
            record_item["artifact"] = {"events": []}
        results.write_text(json.dumps(records))
        if subprocess.run(["python3", str(EVAL_DIR / "validate-harness-results.py"), str(results), "--summary", str(summary)]).returncode == 0:
            raise SystemExit("validator accepted a self-reported verdict without the observed artifact")
    print("PASS: outcome validator contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
