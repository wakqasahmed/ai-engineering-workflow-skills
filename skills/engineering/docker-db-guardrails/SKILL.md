---
name: docker-db-guardrails
description: Set up a Claude Code hook to block Laravel/SQL schema-wipe commands (migrate:fresh, migrate:refresh, db:wipe, DROP DATABASE/TABLE/SCHEMA, TRUNCATE) against a Docker container unless the actually-resolved target database visibly indicates it is disposable (test/testing/demo). Use when copying files into a container to run tests, when running Laravel artisan commands inside a shared/staging container, or when setting up guardrails against destructive database mistakes in Claude Code.
---

# Docker DB Guardrails

Sets up a PreToolUse hook that blocks schema/data-wipe commands run against a
Docker container's real database, unless that database's actual resolved name
visibly indicates it is disposable.

## The incident this guards against

An agent needed to run a Laravel feature test against code on a branch that
hadn't been deployed yet. The target container (a real staging deployment)
had PHP and Composer installed, so the agent:

1. Copied the container's `/var/www/html` to a temp path (`/tmp/test-branch`).
2. Overlaid the branch's changed files on top of that copy.
3. Ran `php artisan migrate:fresh --env=testing --force` from that temp path,
   believing the copy gave it isolation.

It didn't. Laravel's database connection comes from environment variables
(`DB_CONNECTION`, `DB_DATABASE`) that are set on the **container's process**,
not scoped to any working directory inside it — `/tmp/test-branch` and
`/var/www/html` see the exact same `DB_DATABASE`. The `--env=testing` flag
only loads a `.env.testing` file if one exists; this container had none, so
the flag silently no-opped and the command ran against the container's one
real, live database. `migrate:fresh` drops every table and re-migrates from
scratch — every row in every table was gone before anyone noticed.

The rule that should have prevented this already existed in prose (a global
instruction: "never run tests against staging, production, customer, demo, or
shared operational databases"), but it depended on the agent correctly
recognizing the risk before acting — there was no mechanical check that
verified the *actual* resolved database name before the destructive command
ran. This skill turns that prose rule into an automated gate: before any
recognized schema/data-wipe command runs, resolve the real target from
Docker itself and require it to look disposable, or refuse.

## What Gets Blocked

- `artisan migrate:fresh`, `artisan migrate:refresh`, `artisan db:wipe`
- `DROP DATABASE` / `DROP TABLE` / `DROP SCHEMA`
- `TRUNCATE TABLE`

...but only when the command also actually invokes one of the tools these
run through (`artisan`, `psql`, `mysql`, `mariadb`, `sqlite3`, `mongosh`) —
prose that merely *mentions* one of these keywords (a GH issue/PR body
describing this very incident, for example) is not blocked.

For a matched command, the hook resolves the real target and only allows it
through if the target visibly contains `test`, `testing`, or `demo`
(case-insensitive), checked in this order:

1. An explicit `-d <name>` / `--dbname=<name>` / `--db=<name>` argument in
   the command itself (lets an intentional `psql -d signalops_demo ...`
   against a shared multi-database Postgres container pass, without
   trusting the command's target implicitly the way the original incident
   did — that command had no explicit `-d`/`--dbname` argument at all).
2. If the command runs via `docker exec`/`docker compose exec <container>`,
   that container's own real `DB_DATABASE`/`DB_NAME`/`POSTGRES_DB`
   environment variable, read directly from Docker (`docker exec <container>
   env`) — never from anything the command claims about itself.
3. Otherwise (a bare local command), this shell's own equivalent env vars,
   as a best effort.

**A missing or ambiguous resolved name is treated as "assume production,"
never as "assume safe."** Any of the three checks above finding no
test/testing/demo indication blocks the command.

## Steps

### 1. Ask scope

Ask the user: install for **this project only** (`.claude/settings.json`) or
**all projects** (`~/.claude/settings.json`)?

### 2. Copy the hook script

The bundled script is at:
[scripts/block-unverified-destructive-db.py](scripts/block-unverified-destructive-db.py)

Copy it to the target location based on scope:

- **Project**: `.claude/hooks/block-unverified-destructive-db.py`
- **Global**: `~/.claude/hooks/block-unverified-destructive-db.py`

Make it executable with `chmod +x`.

### 3. Add hook to settings

Add to the appropriate settings file, merging into any existing
`hooks.PreToolUse` array's `"Bash"` matcher entry — don't overwrite other
hooks already registered there (e.g. `git-guardrails-claude-code`'s hook):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/block-unverified-destructive-db.py"
          }
        ]
      }
    ]
  }
}
```

(Project scope: use
`"\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/block-unverified-destructive-db.py"`
instead.)

### 4. Ask about customization

Ask if the user wants to broaden or narrow the "safe name" pattern (default:
`test|testing|demo`) or the recognized destructive-command / invoking-tool
patterns. Edit the copied script's `SAFE_NAME_PATTERN`, `DESTRUCTIVE_PATTERN`,
and `INVOKING_TOOLS` constants near the top for these.

### 5. Verify

Test both directions before trusting the hook in a new environment:

```bash
SCRIPT=~/.claude/hooks/block-unverified-destructive-db.py

# Should exit 2 (BLOCKED):
echo '{"tool_input":{"command":"docker exec my-staging-app php artisan migrate:fresh --force"}}' | "$SCRIPT"
echo '{"tool_input":{"command":"php artisan migrate:fresh --force"}}' | "$SCRIPT"

# Should exit 0 (allowed) — routine command, and prose that merely mentions these words:
echo '{"tool_input":{"command":"docker exec my-staging-app php artisan migrate:status"}}' | "$SCRIPT"
echo '{"tool_input":{"command":"gh issue create --body \"discusses migrate:fresh risk\""}}' | "$SCRIPT"
```

Then prove it fires live in-session against a real container in this
environment: run an actual `docker exec <container> php artisan migrate:fresh
--force` (or your stack's equivalent) in the Bash tool and confirm the hook
intercepts it with a `PreToolUse:Bash hook error` before it executes — per
this repo's own `update-config`-style hook-construction discipline
(pipe-test → schema check → live fire proof).

## Known limitations

- The hook tokenizes with Python's `shlex` (not a naive substring scan)
  specifically so that prose passed as the *value* of a text-carrying flag
  (`-m`/`--message`, `--body`, `--title`, `--comment`) is never mistaken for
  a real command invocation — an early substring-scan version of this exact
  hook blocked its own `git commit -m "..."` commit message while it was
  being written, because the message discussed both a destructive keyword
  and an invoking-tool name in plain prose. Still, it does not resolve
  command substitution, shell variables, or multi-command chains. The
  threat model here is an honest agent's wrong mental model about
  environment isolation, not evasion of untrusted input — unlike
  `git-guardrails-claude-code`'s adversarially-hardened tokenizer, which
  must resist deliberately obfuscated dangerous commands.
- A shared, multi-database container without an explicit `-d`/`--dbname`
  argument in the command can only be checked against its own bootstrap env
  var (often just `postgres`), which will correctly fail closed even for a
  legitimate destructive command against a genuinely disposable database on
  that container — pass `-d <safe-name>` explicitly (see check 1 above) to
  get through cleanly, rather than treating a block here as a false alarm to
  silence.
