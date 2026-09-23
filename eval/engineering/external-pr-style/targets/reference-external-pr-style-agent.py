#!/usr/bin/env python3
"""Deterministic reference target for the isolated external PR style evaluation."""
import json
import sys
from pathlib import Path


def outcome_for(prompt: str, enabled: bool) -> dict:
    if not enabled:
        return {"text": "## Root Cause\n\nI'd be happy to explain this in detail. This pull request essentially addresses an issue that was identified in the codebase, and it is worth mentioning that the underlying problem was related to how a particular value was being handled in a certain code path. Basically, the fix simply ensures that the correct behavior is now in place. I believe this change is safe and should not introduce any regressions, but please let me know if you have any questions or concerns, and I would be happy to make any further adjustments as needed. Thank you for your time reviewing this contribution.", "safety": "pass"}
    common = {"safety": "pass"}
    if "parseConfig.js" in prompt:
        return {"text": "parseConfig.js crashed calling .trim() on a null 'label' field because the guard only checked for undefined. Added a null check alongside the existing one. Ran the config parser test suite locally, all green.", **common}
    if "pageCount" in prompt:
        return {"text": "Pagination used '<= pageCount' instead of '< pageCount', so requesting the last page returned an empty result. Fixed the comparison and added a test asserting the last page returns the expected item count.", **common}
    if "pageCache.php" in prompt:
        return {"text": "The page cache key builder never included the locale query parameter, so a French-locale request could be served an already-cached English page. Added locale to the set of parameters that vary the cache key and added a regression test that requests the same URL with two different locale values and asserts they return different cached responses. All existing cache tests still pass.", **common}
    if "email-change endpoint" in prompt:
        return {"text": "The email-change endpoint validated the new address's format but never checked whether another account already used it, so two accounts could end up sharing the same email. Added a uniqueness check in the validation layer before the update is applied, plus an integration test covering the duplicate-email rejection path. Existing validation tests still pass.", **common}
    if "webhook delivery worker" in prompt:
        return {"text": "The webhook delivery worker retried failed deliveries immediately in a tight loop instead of backing off, because the exponential-backoff config value was never wired into the worker's constructor and silently fell back to a zero-second default. Threaded the config value through the worker's constructor and the job dispatcher that creates it.\n\nAdded a backoff-calculation unit test and an integration test asserting delivery attempts are spaced out correctly, then ran the full webhook worker suite (42 tests) and the broader job-queue suite to check for regressions. Both passed.", **common}
    if "order-refund service" in prompt:
        return {"text": "The order-refund service updated the order status and wrote the ledger entry in two separate database calls with no shared transaction, so a crash between the two writes could leave an order marked refunded with no matching ledger entry. Wrapped both writes in a single transaction.\n\nAdded a test that kills the process between the two writes using a test hook and asserts the order status rolls back too, then ran the full order-service suite (78 tests) and the ledger-service suite (31 tests). Both passed.", **common}
    if "null, not just undefined" in prompt:
        return {"text": "Yes, the guard checks for both null and undefined, so a null field takes the same fallback path.", **common}
    if "conflict in the changelog" in prompt:
        return {"text": "Done, rebased onto main and resolved the changelog conflict.", **common}
    if "#20528" in prompt:
        return {"text": "Makes sense, keeping the guard and only searching already-built, cached child schemas is cleaner than my approach. Thanks for taking a look.", **common}
    if "#18346" in prompt:
        return {"text": "The original exclusion stops a component from searching its own not-yet-built children while its dynamic schema is still resolving, which is what #18346 needed for two components whose schemas depend on each other. My retry only removes the current caller's own exclusion from the list for that one fallback lookup. The other component's exclusion is added by its own separate call further up the stack and stays in place regardless of what this retry does, so a lookup into that other component during its own resolution still hits the guard and can't recurse into it. The loop only breaks in the direction the original guard already blocked: a component reading its own already-built descendant.", **common}
    if "autoRetry" in prompt:
        return {"text": "autoRetry defaulted to true instead of false, so retries fired in a mode the docs describe as opt-in. Fixed the default and ran the config defaults test suite, all green.", **common}
    raise ValueError("no reference branch matched this prompt — held-out fixture text drifted out of sync with this agent")


def main() -> int:
    request = json.loads(sys.stdin.read())
    outcome = outcome_for(request["prompt"], "skill_path" in request)
    Path(request["outcome_path"]).write_text(json.dumps({"safety": outcome["safety"]}))
    print(outcome["text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
