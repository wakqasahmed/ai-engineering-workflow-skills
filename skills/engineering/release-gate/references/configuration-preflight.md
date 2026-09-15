# Configuration Preflight

Reference for the "Configuration completeness and secret-delivery verification" line in `../SKILL.md`'s Required For Medium/High Risk list. Run this only when the change introduces or changes a required config/secret name; otherwise this check does not apply.

## 1. Reconciliation

Diff the set of config/secret names the changed code now requires against what the target environment actually has configured.

1. Extract the required names from the diff: new `.env.example` keys, new `config('x.y')` / `os.environ` / `process.env` reads, new `secrets.*`/`vars.*` references in CI workflows, new provider SDK client constructors.
2. List what the target environment actually has, names only, never values: `gh secret list --env <env>`, `<provider> config vars`, `<provider> secrets list`, or the platform's env dashboard.
3. Diff the two sets. Any required name absent from the target environment is a gap.
4. **Block the release on any gap.** List each missing name with the provider-native step to set it — e.g. `gh secret set NAME --env production`, `fly secrets set NAME=...`, the exact dashboard path. Do not deploy hoping the value shows up later: a boot-time crash from a missing variable costs more than this check.

## 2. Non-secret canary

Before a secret-delivery path is used for the first time in an environment — new environment, new secret name, or a changed delivery mechanism such as moving from `.env` to a secret manager — prove the pipe works before any real secret flows through it.

1. Set a harmless placeholder value (e.g. `canary-<random>`) through the exact mechanism the real secret will use: same secret store, same variable name, same injection path (build arg, runtime env, mounted file).
2. Deploy or restart the service so it picks up the new value.
3. Confirm the running service actually read the placeholder: a log line, a `/health` field, or a debug endpoint that reports the variable's *presence* or *length* — never its content.
4. If the canary doesn't show up, the delivery path is broken; fix the wiring before setting the real secret. If it does, the pipe is proven — only then have the real secret set through the same mechanism.

**What a passing canary proves, and what it doesn't**: it proves the delivery mechanism resolves — the wire from secret store to running process works. It does not prove the real credential is valid, scoped correctly, or pointed at the right account. The existing smoke test and health check still have to pass against real values before release completes.

## Guardrails

- Never read, echo, or log an actual secret value in either step — reconciliation compares names only; the canary uses a placeholder, never the real value.
- Both steps are gated exactly like the rest of this gate: skip entirely for low-risk changes; mandatory for medium/high-risk changes that introduce or change required config.
