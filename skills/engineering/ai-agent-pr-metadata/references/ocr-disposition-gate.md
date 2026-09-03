# OCR Finding Disposition Gate

This reference document defines the disposition recording specification for Alibaba Open Code Review (OCR) inline findings, shared by `ai-agent-pr-metadata` and `subagent-pipeline`.

## Disposition Format

Every OCR inline finding on the latest head commit must be addressed with a PR comment in this exact format:

```md
<!-- ocr-disposition:COMMENT_ID -->
Disposition: fixed|deferred|declined
Reason: One concise sentence that preserves the decision.
```

## Governance Rules

- **Authority**: Only repository owners, members, or collaborators can record dispositions on findings. Automated agents without collaborator privileges must draft proposed dispositions for human-owner recording (HITL fallback).
- **Blocking findings**: Any finding explicitly marked `Blocking:` (or involving correctness, security, data loss, or acceptance criteria) must be resolved with `Disposition: fixed`.
- **Non-blocking findings**: Suggestions regarding minor style, speculative defensive coding, or out-of-scope refactoring may be resolved with `Disposition: deferred` or `Disposition: declined`, with a concise rationale in `Reason:`.
- **Zero undispositioned findings**: The OCR disposition gate will fail if any latest-head finding remains without an authoritative disposition.
