---
"ai-engineering-workflow-skills": minor
---

Add the `docker-db-guardrails` skill: a Claude Code `PreToolUse` hook that blocks schema-wipe commands (`migrate:fresh`, `migrate:refresh`, `migrate:reset`, `db:wipe`, `db:drop`, `db:reset`, `DROP DATABASE/TABLE/SCHEMA`, `TRUNCATE`, `dropdb`, `FLUSHALL`) against a Docker container unless the database they would actually hit is visibly disposable.

It resolves the target itself instead of trusting the command: an explicit `-d`/`--dbname` first, then the `docker exec` target container's real environment read from Docker, then the shell's own environment. A missing or ambiguous name is treated as production. Commands are tokenized with `shlex`, so prose that only mentions these words in a commit message, issue body, or PR title is not blocked. `system-level/core.md` gains a Test Database Safety pointer to it.
