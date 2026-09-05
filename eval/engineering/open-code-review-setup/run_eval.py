#!/usr/bin/env python3
"""Deterministic contract layer for the open-code-review-setup skill.

Runs with no network access and no credentials. It does NOT invoke an LLM —
skills are prompt files with no code path to execute directly. Instead it
loads the hand-authored "golden" fixtures under fixtures/*/ (each one a
plausible request plus the compliant artifacts — workflow YAML, rule.json, or
a decline — a correctly-behaving agent following SKILL.md would produce) and
asserts those golden outputs satisfy the skill's non-negotiable contract, via
contract.py.

This proves the fixtures and the contract checks are internally consistent
and regression-safe. It does NOT prove a live model given SKILL.md will
actually produce these exact artifacts for a given request.

Exit code 0 = pass, 1 = fail.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
TEMPLATES_DIR = (
    Path(__file__).resolve().parents[3]
    / "skills"
    / "engineering"
    / "open-code-review-setup"
    / "templates"
)


def load_fixture(fixture_dir: Path) -> dict:
    meta = json.loads((fixture_dir / "meta.json").read_text())
    meta["_dir"] = fixture_dir.name
    return meta


def run_should_use_fixture(fixture_dir: Path, meta: dict) -> list:
    ocr_yml_path = fixture_dir / "golden-open-code-review.yml"
    if ocr_yml_path.exists():
        result = contract.check_workflow_files_contract(
            ocr_yml_path.read_text(),
            (fixture_dir / "golden-ocr-manual-review.yml").read_text(),
            (fixture_dir / "golden-rule.json").read_text(),
            maintainer=meta["maintainer"],
        )
        return result.failures
    response_text = (fixture_dir / "golden_response.md").read_text()
    result = contract.check_decline_response(response_text, meta.get("decline_signal_patterns"))
    return result.failures


def run_should_not_use_fixture(fixture_dir: Path, meta: dict) -> list:
    response_text = (fixture_dir / "golden_response.md").read_text()
    result = contract.check_decline_response(response_text, meta.get("decline_signal_patterns"))
    return result.failures


def check_untrusted_comment_trigger_regression() -> list[str]:
    """Regression check: strip the maintainer gate from the manual-review workflow
    and assert the contract rejects it — an open /ocr-review comment trigger would
    let any commenter on any PR spend LLM budget."""
    ocr_yml = (TEMPLATES_DIR / "open-code-review.yml").read_text()
    manual_yml = (TEMPLATES_DIR / "ocr-manual-review.yml").read_text()
    rule_json = (TEMPLATES_DIR / "rule.json").read_text()

    ungated_manual_yml = manual_yml.replace(
        "github.event.comment.user.login == '${{ vars.MAINTAINER_USERNAME }}' &&\n      ",
        "",
    )
    if ungated_manual_yml == manual_yml:
        return ["fixture text to strip was not found — update this regression case"]

    result = contract.check_workflow_files_contract(
        ocr_yml, ungated_manual_yml, rule_json, maintainer="wakqasahmed"
    )
    if result.passed:
        return [
            "contract accepted an ocr-manual-review.yml with the maintainer gate "
            "stripped from its comment trigger"
        ]
    return []


def check_mutable_action_input_regression() -> list[str]:
    """Regression check: replace the pinned commit SHA with a floating tag and
    assert the contract rejects it — a moved tag changes executable CI code
    without a repository diff."""
    ocr_yml = (TEMPLATES_DIR / "open-code-review.yml").read_text()
    manual_yml = (TEMPLATES_DIR / "ocr-manual-review.yml").read_text()
    rule_json = (TEMPLATES_DIR / "rule.json").read_text()

    unpinned_ocr_yml = ocr_yml.replace(
        "alibaba/open-code-review@1c8f930fc923753b17b80f633aea54274fc83825", "alibaba/open-code-review@v1"
    )
    if unpinned_ocr_yml == ocr_yml:
        return ["fixture text to replace was not found — update this regression case"]

    result = contract.check_workflow_files_contract(
        unpinned_ocr_yml, manual_yml, rule_json, maintainer="wakqasahmed"
    )
    if result.passed:
        return [
            "contract accepted an open-code-review.yml pinned to a floating tag "
            "instead of a full commit SHA"
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

    for check_name, check_fn in (
        ("untrusted comment trigger", check_untrusted_comment_trigger_regression),
        ("mutable action input", check_mutable_action_input_regression),
    ):
        regression_failures = check_fn()
        status = "PASS" if not regression_failures else "FAIL"
        print(f"[{status}] contract rejects {check_name}")
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
