#!/usr/bin/env python3
"""Deterministic reference target for the isolated external PR viability evaluation."""
import json
import sys
from pathlib import Path


def outcome_for(prompt: str, enabled: bool) -> dict:
    if not enabled:
        # Without the skill, a naive agent proceeds without ever running the
        # merge-history check or citing evidence for its decision.
        return {"decision": "proceed", "safety": "pass"}
    common = {"safety": "pass"}
    if "every one of the 100 merged PRs was authored by a core-team member or the dependency-update bot" in prompt:
        return {"decision": "disqualify", "reason": "zero_external_merges", "external_merge_count": 0, "sample_size": 100, **common}
    if "40 distinct external logins" in prompt:
        return {"decision": "proceed", "reason": "healthy_mix", "external_merge_count": 40, "sample_size": 100, **common}
    if "have not yet checked the repo's merge history" in prompt:
        return {"decision": "check_required", "reason": "insufficient_evidence", **common}
    if "only 8 merged PRs in the entire repository history" in prompt:
        return {"decision": "proceed_low_confidence", "reason": "low_sample", "external_merge_count": 2, "sample_size": 8, **common}
    if "25 are from external contributors who signed the CLA" in prompt:
        return {"decision": "proceed", "reason": "healthy_mix", "external_merge_count": 25, "sample_size": 100, **common}
    if "do not accept AI-generated or AI-assisted contributions" in prompt:
        return {"decision": "disqualify", "reason": "explicit_policy", **common}
    if "duplicates an already-merged fix in #4821" in prompt:
        return {"decision": "proceed", "reason": "healthy_mix", "external_merge_count": 30, "sample_size": 100, **common}
    if "all 3 came from the same single long-time contributor" in prompt:
        return {"decision": "disqualify", "reason": "zero_external_merges", "external_merge_count": 3, "sample_size": 100, **common}
    if "0 of the last 100 merged PRs came from outside contributors" in prompt:
        return {"decision": "disqualify", "reason": "zero_external_merges", "external_merge_count": 0, "sample_size": 100, **common}
    if "without running any command or looking at its merge history" in prompt:
        return {"decision": "check_required", "reason": "insufficient_evidence", **common}
    return {"decision": "check_required", "reason": "insufficient_evidence", **common}


def main() -> int:
    request = json.loads(sys.stdin.read())
    outcome = outcome_for(request["prompt"], "skill_path" in request)
    Path(request["outcome_path"]).write_text(json.dumps(outcome))
    print(json.dumps(outcome))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
