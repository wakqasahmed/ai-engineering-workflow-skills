This cannot proceed without a real OpenRouter API key. `OCR_LLM_AUTH_TOKEN`
does not have a valid value available in the local secrets store, and a
placeholder credential would either fail the preflight probe (401) or, worse,
silently configure a workflow that can never authenticate.

Per this skill's guardrails, no key available means stop here and use
`hitl-blocker` to file a visible blocker for a human to resolve — this must
not retry automation or invent a placeholder value.
