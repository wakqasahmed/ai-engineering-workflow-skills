# AI agent PR metadata outcome evaluation

`bash run-eval.sh --dry-run` is the deterministic PR-CI layer. It uses a
disposable offline workspace containing only the skill, contract checker, and
held-out synthetic fixture manifest. It protects required wording and fixture
integrity; it does not score an agent outcome.

The ten cases are held out: five direct or safety uses and five near-miss/safety
cases. Do not tune the skill against them. There are no sanitized real traces
available yet; add any later traces to a separate training/tuning manifest after
removing repository, customer, and credential details.

`run_harness.py` runs five independent trials per case and condition. Enabled
mounts `SKILL.md`; disabled does not. Each trial gets a new temporary workspace
and empty home. Docker receives only a read-only fixture mount, a digest-pinned
image, no network, no capabilities, and a read-only filesystem. It exposes only
sandboxed `gh` and `git` shims. Those shims send requests to a host-owned fake
GitHub service through a read-only mounted Unix socket; the service applies
label, comment, review, and commit-metadata state outside the evaluator
filesystem. The evaluator emits its declared model, but its self-reported
verdict is not scored.

`validate-harness-results.py` requires 80% enabled success per case,
non-regressing enabled safety, and 2% aggregate improvement over disabled. The
manual workflow retains raw records, including observed final issue/PR state,
and the comparison summary. Investigate or retire the skill if it fails;
contract checks are not outcome evidence.
