#!/usr/bin/env python3
"""Deterministic contract layer for the design-composition-check skill.

Runs with no network access and no credentials. It does NOT invoke an LLM —
skills are prompt files with no code path to execute directly. Instead it
loads the hand-authored "golden" fixtures under fixtures/*/ (each one a
plausible scenario plus the compliant output — a composition-check report, or
a skip response — a correctly-behaving agent following SKILL.md would
produce) and asserts those golden outputs satisfy the skill's non-negotiable
contract, via contract.py.

This proves the fixtures and the contract checks are internally consistent
and regression-safe. It does NOT prove a live model given SKILL.md will
actually pick the same anchor screens for a given scenario.

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
    report_text = (fixture_dir / "golden_report.md").read_text()
    result = contract.check_composition_report(
        report_text,
        hard_screens=meta.get("hard_screens", []),
        easy_screens=meta.get("easy_screens", []),
        expected_verdict=meta.get("expected_verdict"),
        min_gap_count=meta.get("min_gap_count", 0),
        expected_gap_classes=meta.get("expected_gap_classes", {}),
        allow_single_screen=meta.get("allow_single_screen", False),
    )
    return result.failures


def run_should_skip_fixture(fixture_dir: Path, meta: dict) -> list:
    response_text = (fixture_dir / "golden_response.md").read_text()
    result = contract.check_skip_response(response_text, meta.get("skip_signal_patterns"))
    return result.failures


def check_easy_screen_regression() -> list[str]:
    """Regression check: swap the golden dashboard/checkout selection for the
    easy landing/settings screens and assert the contract rejects it. Proves
    the easy-screen check actually fires, not just that a golden report which
    happens to already pick hard screens trivially passes."""
    fixture_dir = FIXTURES_DIR / "should_use_01_dense_dashboard_and_checkout"
    meta = load_fixture(fixture_dir)
    report_text = (fixture_dir / "golden_report.md").read_text()
    tampered = report_text.replace(
        "- Analytics Dashboard — information density: per-column filters, sorting, and pagination over a live dataset\n"
        "- Approval Flow — primary flow: this is the tool's core multi-step task",
        "- Welcome Landing Screen — easy to render first\n"
        "- Settings Screen — easy to render first",
    )
    if tampered == report_text:
        return ["fixture text did not match the expected screen-selection lines — update this regression case"]
    result = contract.check_composition_report(
        tampered,
        hard_screens=meta["hard_screens"],
        easy_screens=meta["easy_screens"],
        expected_verdict=meta.get("expected_verdict"),
    )
    if not any("is one of the easy/skip screens" in f for f in result.failures):
        return [
            "contract did not reject the easy-screen anchors via the dedicated easy_screens guard "
            f"(failures were: {result.failures})"
        ]
    return []


def main() -> int:
    fixture_dirs = sorted(p for p in FIXTURES_DIR.iterdir() if p.is_dir())
    if len(fixture_dirs) < 3:
        print(f"FAIL: expected at least 3 fixtures, found {len(fixture_dirs)}")
        return 1

    should_use_count = 0
    should_skip_count = 0
    total_failures = 0

    skill_failures = contract.check_skill_md_contract().failures
    status = "PASS" if not skill_failures else "FAIL"
    print(f"[{status}] SKILL.md matches the deterministic contract")
    for failure in skill_failures:
        print(f"    - {failure}")
        total_failures += 1

    regression_failures = check_easy_screen_regression()
    status = "PASS" if not regression_failures else "FAIL"
    print(f"[{status}] contract rejects an anchor selection that picks the easy screens")
    for failure in regression_failures:
        print(f"    - {failure}")
        total_failures += 1

    for fixture_dir in fixture_dirs:
        meta = load_fixture(fixture_dir)
        category = meta["category"]

        if category == "should_use":
            should_use_count += 1
            failures = run_should_use_fixture(fixture_dir, meta)
        elif category == "should_skip":
            should_skip_count += 1
            failures = run_should_skip_fixture(fixture_dir, meta)
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
    if should_skip_count < 1:
        print(f"FAIL: expected at least 1 should_skip fixture, found {should_skip_count}")
        total_failures += 1

    if total_failures:
        print(f"\nFAIL: {total_failures} contract violation(s) across {len(fixture_dirs)} fixtures")
        return 1

    print(
        f"\nPASS: {len(fixture_dirs)} fixtures ({should_use_count} should_use, "
        f"{should_skip_count} should_skip) all satisfy the deterministic contract"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
