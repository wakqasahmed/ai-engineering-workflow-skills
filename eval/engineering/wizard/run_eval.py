#!/usr/bin/env python3
"""Deterministic contract layer for the wizard skill.

Runs with no network access and no credentials. It does NOT invoke an LLM —
skills are prompt files with no code path to execute directly. Instead it
loads the hand-authored "golden" fixtures under fixtures/*/ (each one a
plausible request plus the compliant output — a generated wizard script, or a
decline — a correctly-behaving agent following SKILL.md would produce) and
asserts those golden outputs satisfy the skill's non-negotiable contract, via
contract.py.

This proves the fixtures and the contract checks are internally consistent
and regression-safe. It does NOT prove a live model given SKILL.md will
actually produce this exact script for a given request.

Exit code 0 = pass, 1 = fail.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(fixture_dir: Path) -> dict:
    meta = json.loads((fixture_dir / "meta.json").read_text())
    meta["_dir"] = fixture_dir.name
    return meta


def run_should_use_fixture(fixture_dir: Path, meta: dict) -> list:
    script_text = (fixture_dir / "golden_wizard.sh").read_text()
    result = contract.check_wizard_script_contract(
        script_text,
        expected_stage_count=meta.get("expected_stage_count"),
        expected_env_names=meta.get("expected_env_names"),
        expected_secret_names=meta.get("expected_secret_names"),
        requires_confirm_before_irreversible=meta.get(
            "requires_confirm_before_irreversible", False
        ),
    )
    return result.failures


def run_should_not_use_fixture(fixture_dir: Path, meta: dict) -> list:
    response_text = (fixture_dir / "golden_response.md").read_text()
    result = contract.check_decline_response(
        response_text, meta.get("decline_signal_patterns")
    )
    return result.failures


def check_missing_confirm_regression() -> list[str]:
    """Regression check: strip the confirm calls from the irreversible-migration
    golden script and assert the contract rejects it. Proves the
    requires_confirm_before_irreversible check actually fires, not just that a
    script which happens to already have confirm calls trivially passes."""
    fixture_dir = FIXTURES_DIR / "should_use_02_irreversible_migration"
    meta = load_fixture(fixture_dir)
    script_text = (fixture_dir / "golden_wizard.sh").read_text()
    stripped_script = "\n".join(
        line for line in script_text.splitlines() if not line.strip().startswith('confirm "')
    )
    if stripped_script == script_text:
        return ["fixture has no confirm lines to strip — update this regression case"]
    result = contract.check_wizard_script_contract(
        stripped_script,
        expected_stage_count=meta.get("expected_stage_count"),
        requires_confirm_before_irreversible=True,
    )
    if result.passed:
        return [
            "contract accepted an irreversible-migration script with every confirm "
            "call removed"
        ]
    return []


def main() -> int:
    fixture_dirs = sorted(p for p in FIXTURES_DIR.iterdir() if p.is_dir())
    if len(fixture_dirs) < 3:
        print(f"FAIL: expected at least 3 fixtures, found {len(fixture_dirs)}")
        return 1

    should_use_count = 0
    should_not_use_count = 0
    total_failures = 0

    regression_failures = check_missing_confirm_regression()
    status = "PASS" if not regression_failures else "FAIL"
    print(f"[{status}] contract rejects an irreversible action with no confirm gate")
    for failure in regression_failures:
        print(f"    - {failure}")
        total_failures += 1

    for fixture_dir in fixture_dirs:
        meta = load_fixture(fixture_dir)
        category = meta["category"]

        if category == "should_use":
            should_use_count += 1
            failures = run_should_use_fixture(fixture_dir, meta)
        elif category == "should_not_use":
            should_not_use_count += 1
            failures = run_should_not_use_fixture(fixture_dir, meta)
        else:
            failures = [f"unknown category '{category}'"]

        status = "PASS" if not failures else "FAIL"
        print(f"[{status}] {fixture_dir.name} ({category})")
        for failure in failures:
            print(f"    - {failure}")
            total_failures += 1

    print()
    if should_use_count < 2:
        print(f"FAIL: expected at least 2 should_use fixtures, found {should_use_count}")
        total_failures += 1
    if should_not_use_count < 1:
        print(f"FAIL: expected at least 1 should_not_use fixture, found {should_not_use_count}")
        total_failures += 1

    if total_failures:
        print(f"\nFAIL: {total_failures} contract violation(s) across {len(fixture_dirs)} fixtures")
        return 1

    print(
        f"\nPASS: {len(fixture_dirs)} fixtures ({should_use_count} should_use, "
        f"{should_not_use_count} should_not_use) all satisfy the deterministic contract"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
