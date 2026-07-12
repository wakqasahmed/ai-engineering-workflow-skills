#!/usr/bin/env bash
set -euo pipefail

EVAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURES_DIR="${EVAL_DIR}/fixtures"
SKILL_MD="${EVAL_DIR}/../SKILL.md"

MODE="dry-run"
LIVE_REPO=""
LIVE_PR=""

usage() {
  cat <<'USAGE'
Usage:
  run-eval.sh [--dry-run]
  run-eval.sh --live --repo <owner/name> --pr <number>

Behavioral eval fixture for the subagent-pipeline skill. Exercises the
review-comment and merge-gate behaviors described in SKILL.md against
frozen fixtures.

  --dry-run          (default) Assert against the fixtures in eval/fixtures/.
                      No network calls, nothing touches GitHub.
  --live             Re-run the same structural assertions against a real
                      PR's review comments and CI status via `gh`. Requires
                      --repo and --pr, and an authenticated `gh` (GH_TOKEN).
                      This performs real read-only GitHub API calls; it does
                      not open PRs, post comments, or merge anything.
  --repo OWNER/NAME  Repository to inspect in --live mode.
  --pr NUMBER        PR number to inspect in --live mode.
  --help             Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) MODE="dry-run"; shift ;;
    --live) MODE="live"; shift ;;
    --repo) LIVE_REPO="$2"; shift 2 ;;
    --pr) LIVE_PR="$2"; shift 2 ;;
    --help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

PASS=0
FAIL=0

check() {
  local description="$1"
  local result="$2"
  if [[ "$result" == "true" ]]; then
    echo "PASS: ${description}"
    PASS=$((PASS + 1))
  else
    echo "FAIL: ${description}"
    FAIL=$((FAIL + 1))
  fi
}

# (a) Pipeline description requires inline gh pr review comments, not
#     in-conversation-only summaries.
assert_inline_comments_required() {
  local doc_states_it="false"
  if grep -q "must post real inline PR comments" "$SKILL_MD"; then
    doc_states_it="true"
  fi
  check "SKILL.md requires real inline PR comments (not summaries)" "$doc_states_it"

  local good_is_structured
  good_is_structured=$(jq -e '.comments | length > 0 and all(.path != null and .line != null)' \
    "${FIXTURES_DIR}/pr-review-comments-good.json" > /dev/null 2>&1 && echo true || echo false)
  check "good fixture: every comment has a path+line (real inline comment)" "$good_is_structured"

  local bad_is_unstructured
  bad_is_unstructured=$(jq -e '.comments | length > 0 and all(.path == null and .line == null)' \
    "${FIXTURES_DIR}/pr-review-comments-bad.json" > /dev/null 2>&1 && echo true || echo false)
  check "bad fixture: comment lacks path+line (in-conversation-only summary, would be rejected)" "$bad_is_unstructured"

  local bad_source_flagged="false"
  if jq -e '.source | test("in-conversation")' "${FIXTURES_DIR}/pr-review-comments-bad.json" > /dev/null 2>&1; then
    bad_source_flagged="true"
  fi
  check "bad fixture is explicitly sourced from conversation, not the GitHub API" "$bad_source_flagged"
}

# (b) Fixer reads structured comments via the gh api path, not free text.
assert_fixer_reads_structured_comments() {
  local doc_states_it="false"
  if grep -q 'gh api repos/.../pulls/.../comments' "$SKILL_MD"; then
    doc_states_it="true"
  fi
  check "SKILL.md tells the fixer to read via gh api .../pulls/.../comments" "$doc_states_it"

  local good_source_is_api="false"
  if jq -e '.source | test("^gh api repos/.*/pulls/[0-9]+/comments$")' \
    "${FIXTURES_DIR}/pr-review-comments-good.json" > /dev/null 2>&1; then
    good_source_is_api="true"
  fi
  check "good fixture's comment source matches the documented gh api path" "$good_source_is_api"
}

# Merge-decision logic, deliberately implemented twice in two different
# languages so the eval isn't just "a copy of the rule agreeing with
# itself": a bash version and an independent jq version. Both must agree
# with each other, and both must agree with the fixture's expect_merge,
# before a fixture is considered passing. This mirrors two literal
# sentences from SKILL.md's "Merge" step:
#   "auto-merge (`gh pr merge --squash --auto`) to `staging` once CI passes."
#   "Always require human approval before merging to `main`."
merge_should_proceed_bash() {
  local ci_state="$1" base_branch="$2" human_approval="$3"
  if [[ "$ci_state" != "success" ]]; then
    echo "false"
    return
  fi
  if [[ "$base_branch" == "main" && "$human_approval" != "true" ]]; then
    echo "false"
    return
  fi
  echo "true"
}

merge_should_proceed_jq() {
  local ci_state="$1" base_branch="$2" human_approval="$3"
  jq -n --arg ci "$ci_state" --arg base "$base_branch" --argjson approved "$human_approval" \
    '($ci == "success") and (($base != "main") or $approved)'
}

# Evaluate a merge-gate fixture with both independent implementations and
# require: (1) they agree with each other, (2) they agree with the
# fixture's recorded expect_merge. A regression in either implementation,
# or a fixture whose expect_merge no longer matches the documented rule,
# fails this — it is not merely self-consistency.
assert_merge_fixture() {
  local fixture="$1" label="$2"
  local ci_state base_branch human_approval expected bash_result jq_result
  ci_state=$(jq -r '.ci_state' "$fixture")
  base_branch=$(jq -r '.base_branch' "$fixture")
  human_approval=$(jq -r '.human_approval' "$fixture")
  expected=$(jq -r '.expect_merge' "$fixture")
  bash_result=$(merge_should_proceed_bash "$ci_state" "$base_branch" "$human_approval")
  jq_result=$(merge_should_proceed_jq "$ci_state" "$base_branch" "$human_approval")
  local agree="false"
  [[ "$bash_result" == "$jq_result" && "$bash_result" == "$expected" ]] && agree="true"
  check "$label" "$agree"
}

# (c) Merge only proceeds when the CI-green condition is true in the fixture.
assert_merge_requires_ci_green() {
  local fixture="${FIXTURES_DIR}/merge-target-staging.json"
  assert_merge_fixture "$fixture" "staging + CI green -> merge proceeds (bash and jq implementations agree)"

  fixture="${FIXTURES_DIR}/merge-target-staging-ci-red.json"
  assert_merge_fixture "$fixture" "staging + CI red -> merge blocked (bash and jq implementations agree)"
}

# (d) A main-branch fixture where merge must NOT proceed without a
#     human-approval flag, contrasted with one where it does.
assert_main_requires_human_approval() {
  local fixture="${FIXTURES_DIR}/merge-target-main-no-approval.json"
  assert_merge_fixture "$fixture" "main + CI green + no human approval -> merge blocked (bash and jq implementations agree)"

  fixture="${FIXTURES_DIR}/merge-target-main-approved.json"
  assert_merge_fixture "$fixture" "main + CI green + human approval -> merge proceeds (bash and jq implementations agree)"

  local doc_states_it="false"
  if grep -q "Always require human approval before merging to \`main\`" "$SKILL_MD"; then
    doc_states_it="true"
  fi
  check "SKILL.md states human approval is always required for main" "$doc_states_it"
}

# (e) The implementer-stage fixtures (issue.json, repo-diff.json) and the
#     standalone CI-status fixtures are not dead weight: assert the diff
#     actually addresses the issue's stated acceptance criteria, and that
#     the CI-status fixtures are internally consistent with the same PR.
assert_implementer_and_ci_status_fixtures_are_used() {
  local issue_fixture="${FIXTURES_DIR}/issue.json"
  local diff_fixture="${FIXTURES_DIR}/repo-diff.json"

  local issue_wants_retry="false"
  if jq -e '.body | test("retry"; "i")' "$issue_fixture" > /dev/null 2>&1; then
    issue_wants_retry="true"
  fi
  check "issue fixture's acceptance criteria mention retry behavior" "$issue_wants_retry"

  local diff_implements_retry="false"
  if jq -e '[.files[].patch] | join("\n") | test("attempts") and test("usleep")' \
    "$diff_fixture" > /dev/null 2>&1; then
    diff_implements_retry="true"
  fi
  check "repo-diff fixture's patch implements retry/backoff (addresses the issue)" "$diff_implements_retry"

  local pr_numbers_consistent="false"
  local diff_pr green_pr red_pr
  diff_pr=$(jq -r '.pr_number' "$diff_fixture")
  green_pr=$(jq -r '.pr_number' "${FIXTURES_DIR}/ci-status-green.json")
  red_pr=$(jq -r '.pr_number' "${FIXTURES_DIR}/ci-status-red.json")
  if [[ "$diff_pr" == "$green_pr" && "$diff_pr" == "$red_pr" ]]; then
    pr_numbers_consistent="true"
  fi
  check "ci-status fixtures reference the same PR as the implementer diff fixture" "$pr_numbers_consistent"

  local states_map_to_merge_gate="false"
  local green_state red_state
  green_state=$(jq -r '.state' "${FIXTURES_DIR}/ci-status-green.json")
  red_state=$(jq -r '.state' "${FIXTURES_DIR}/ci-status-red.json")
  local staging_ci merge_red_ci
  staging_ci=$(jq -r '.ci_state' "${FIXTURES_DIR}/merge-target-staging.json")
  merge_red_ci=$(jq -r '.ci_state' "${FIXTURES_DIR}/merge-target-staging-ci-red.json")
  if [[ "$green_state" == "$staging_ci" && "$red_state" == "$merge_red_ci" ]]; then
    states_map_to_merge_gate="true"
  fi
  check "ci-status fixture states match the ci_state values used by the merge-gate fixtures" "$states_map_to_merge_gate"
}

run_dry_run() {
  echo "== subagent-pipeline eval (dry-run, fixtures only, no network) =="
  assert_inline_comments_required
  assert_fixer_reads_structured_comments
  assert_merge_requires_ci_green
  assert_main_requires_human_approval
  assert_implementer_and_ci_status_fixtures_are_used
}

run_live() {
  echo "== subagent-pipeline eval (live, real GitHub reads via gh) =="
  if [[ -z "$LIVE_REPO" || -z "$LIVE_PR" ]]; then
    echo "FAIL: --live requires --repo <owner/name> and --pr <number>" >&2
    exit 1
  fi
  if ! command -v gh > /dev/null 2>&1; then
    echo "FAIL: gh CLI not found, cannot run --live mode" >&2
    exit 1
  fi

  echo "Fetching review comments for ${LIVE_REPO}#${LIVE_PR} (read-only)..."
  local comments
  comments=$(gh api "repos/${LIVE_REPO}/pulls/${LIVE_PR}/comments")
  local has_inline
  has_inline=$(jq -e 'length > 0 and all(.[]; .path != null and .line != null)' <<<"$comments" > /dev/null 2>&1 && echo true || echo false)
  check "live PR has structured inline comments (path+line) via gh api .../pulls/.../comments" "$has_inline"

  echo "Fetching CI status for ${LIVE_REPO}#${LIVE_PR} (read-only)..."
  local checks_json state
  checks_json=$(gh pr view "$LIVE_PR" --repo "$LIVE_REPO" --json statusCheckRollup)
  state=$(jq -r '[.statusCheckRollup[].conclusion // .statusCheckRollup[].state] | if length == 0 then "none" elif all(. == "SUCCESS" or . == "success") then "success" else "not-success" end' <<<"$checks_json")
  check "live CI status resolved (informational: state=${state})" "true"

  echo "NOTE: --live mode only performs read-only GitHub API calls. It does" \
       "not open PRs, post review comments, or merge — those remain fixture-only assertions."
}

if [[ "$MODE" == "dry-run" ]]; then
  run_dry_run
else
  run_live
fi

echo
echo "Results: ${PASS} passed, ${FAIL} failed"
if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
