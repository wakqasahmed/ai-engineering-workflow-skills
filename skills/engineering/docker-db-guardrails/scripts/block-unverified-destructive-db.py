#!/usr/bin/env python3
"""
PreToolUse hook (Bash matcher): blocks schema/data-wipe commands (Laravel
artisan migrate:fresh / migrate:refresh / db:wipe, raw DROP DATABASE / DROP
TABLE / DROP SCHEMA, TRUNCATE TABLE) unless the actual resolved target
database visibly indicates it is disposable (name contains test/testing/demo).

Why this exists: a container's DB_CONNECTION/DB_DATABASE (or POSTGRES_DB) env
vars are process-wide, not scoped to any working directory inside that
container. Copying a codebase into a temp directory inside a container and
running `migrate:fresh` there still wipes the container's one real database -
copying files created no isolation. A `--env=testing`-style CLI flag silently
no-ops when no `.env.testing` file exists, so nothing signals the mistake
before the command runs. See SKILL.md for the incident this guards against.

Policy: fail closed. A missing or ambiguous resolved database name is
treated as "assume production," never as "assume safe."

Implementation note: uses shlex to tokenize the command instead of a raw
substring scan, specifically so that prose passed as the *value* of a
text-carrying flag (-m/--message, --body, --title, --comment - e.g. a git
commit message or GH issue body describing this very hook) is never
mistaken for a real destructive command invocation. A naive substring
scan cannot make this distinction and will self-trigger on exactly this
kind of documentation - this happened for real while writing this hook.
"""
import json
import re
import shlex
import subprocess
import sys

DESTRUCTIVE_PATTERN = re.compile(
    r"migrate:fresh|migrate:refresh|db:wipe"
    r"|drop\s+(database|table|schema)|truncate\s+table",
    re.IGNORECASE,
)
INVOKING_TOOLS = {"artisan", "psql", "mysql", "mariadb", "sqlite3", "mongosh"}
SAFE_NAME_PATTERN = re.compile(r"test|testing|demo", re.IGNORECASE)

# Single source of truth for every "which env var names the database"
# lookup - a container's env (container_db_values) and this shell's own env
# (the local fallback in main()) both use this, so they can never drift out
# of sync with each other again the way they briefly did during review.
DB_NAME_ENV_KEYS = ("DB_DATABASE", "DB_NAME", "POSTGRES_DB", "MYSQL_DATABASE", "MARIADB_DATABASE")

# Flags whose value is free-form prose, not a command/argument to inspect.
PROSE_FLAGS = {"-m", "--message", "--body", "--title", "--comment", "-F", "--file"}


def read_command() -> str:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return ""
    return payload.get("tool_input", {}).get("command", "") or ""


def tokenize(command: str) -> list[str] | None:
    """Returns None (not []) on failure - a caller that could not resolve
    the command must fail closed, not silently treat it as containing zero
    scannable words. An earlier version returned [] here, which made
    scannable_text empty, which made the destructive-pattern check fail to
    match, which let the whole command through unblocked - a fail-open bug
    on the exact class of malformed input (unbalanced quotes) this hook
    exists to be paranoid about."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=False)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return None


def scannable_tokens(tokens: list[str]) -> list[int]:
    """Indices of tokens that are real command words, excluding any token
    that is the *value* of a prose flag (its own commit message, PR body,
    issue title, etc.) - those must never be treated as a real invocation."""
    indices = []
    skip_next = False
    for i, tok in enumerate(tokens):
        if skip_next:
            skip_next = False
            continue
        if tok in PROSE_FLAGS:
            skip_next = True
            continue
        # Catches both the spaced-out "--flag=value" form and a short flag
        # glued directly onto its value with no space (-m"a message here"
        # shlex-tokenizes as one word, "-ma message here" - not equal to
        # "-m" and no "=" present, so the exact/"=" checks alone miss it).
        if any(tok.startswith(flag) and len(tok) > len(flag) for flag in PROSE_FLAGS):
            continue
        indices.append(i)
    return indices


def find_container(tokens: list[str]) -> str | None:
    try:
        exec_index = next(
            i for i, tok in enumerate(tokens)
            if tok == "exec" and i > 0 and tokens[i - 1] in ("docker", "compose", "docker-compose")
        )
    except StopIteration:
        return None

    i = exec_index + 1
    value_flags = {"-w", "-u", "-e", "--env", "--env-file", "--user", "--workdir"}
    while i < len(tokens):
        tok = tokens[i]
        if tok in value_flags:
            i += 2
            continue
        if tok.startswith("-"):
            i += 1
            continue
        return tok
    return None


def find_explicit_dbname(tokens: list[str]) -> str | None:
    for i, tok in enumerate(tokens):
        # -D/--database: mysql/mariadb client flags for selecting a database,
        # alongside -d/--dbname/--db (psql/sqlite-style tools).
        if tok in ("-d", "--dbname", "--db", "-D", "--database") and i + 1 < len(tokens):
            return tokens[i + 1]
        for prefix in ("--dbname=", "--db=", "--database="):
            if tok.startswith(prefix):
                return tok[len(prefix):]
    return None


def container_db_values(container: str) -> list[str]:
    try:
        result = subprocess.run(
            ["docker", "exec", container, "env"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    values = []
    for line in result.stdout.splitlines():
        key, _, value = line.partition("=")
        if key in DB_NAME_ENV_KEYS:
            values.append(value)
    return values


def main() -> int:
    command = read_command()
    if not command:
        return 0

    if not DESTRUCTIVE_PATTERN.search(command):
        return 0

    tokens = tokenize(command)
    if tokens is None:
        sys.stderr.write(
            f"BLOCKED: could not safely tokenize this command (unbalanced "
            f"quotes or similar) while checking it for schema/data-"
            f"destructive operations: {command}. Fixing the quoting and "
            f"re-running is the safe path - this hook cannot verify a "
            f"command it cannot parse.\n"
        )
        return 2
    # A list, not a set: order must be preserved so multi-word patterns like
    # "drop\s+table" can only match when those words are genuinely adjacent
    # in the command, not merely present anywhere. Python sets do not
    # guarantee iteration order, so joining a set here could silently
    # scramble word order and make the regex match (or fail to match)
    # based on hash placement rather than the command's actual content.
    scannable = [tokens[i] for i in scannable_tokens(tokens)]
    scannable_text = " ".join(scannable)

    # A destructive keyword alone isn't enough - it must appear as a real
    # command word (not inside prose), and the command must also actually
    # invoke one of the tools these operations run through.
    if not DESTRUCTIVE_PATTERN.search(scannable_text):
        return 0
    if not any(tool in scannable for tool in INVOKING_TOOLS):
        return 0

    # An explicit -d/--dbname/-D/--database argument states the user's actual
    # intent for THIS invocation and always wins outright - safe, allow;
    # unsafe, block immediately. Never fall through to a container's or this
    # shell's env vars afterward: those describe the container/shell in
    # general, not necessarily the specific database this command names, and
    # an explicit unsafe target must not be rescued by an unrelated
    # safe-looking env var elsewhere on the same container.
    explicit_db = find_explicit_dbname(tokens)
    if explicit_db is not None:
        if SAFE_NAME_PATTERN.search(explicit_db):
            return 0
        sys.stderr.write(
            f"BLOCKED: explicit database name \"{explicit_db}\" does not "
            f"visibly contain test/testing/demo - refusing a schema/data-"
            f"destructive command ({command}). An explicitly named target "
            f"always wins over any container or shell environment variable.\n"
        )
        return 2

    container = find_container(tokens)
    if container:
        db_values = container_db_values(container)
        if not db_values:
            sys.stderr.write(
                f"BLOCKED: could not read container \"{container}\"'s real "
                f"environment to verify its target database before running a "
                f"schema/data-destructive command ({command}). Resolve this "
                f"manually and re-run, or get explicit confirmation from the "
                f"user.\n"
            )
            return 2
        # Every recognized database-name env var present must look safe, not
        # just one of them - a container can carry more than one of these
        # keys (e.g. a leftover MYSQL_DATABASE alongside the DB_DATABASE the
        # invoked tool actually reads), and this hook cannot always tell
        # which one governs a given tool/invocation. Requiring unanimity
        # means one unsafe-looking value blocks, rather than one
        # safe-looking value rescuing an otherwise-unsafe target.
        if all(SAFE_NAME_PATTERN.search(v) for v in db_values):
            return 0
        sys.stderr.write(
            f"BLOCKED: container \"{container}\"'s resolved database "
            f"({', '.join(db_values) or '<none found>'}) does not visibly "
            f"contain test/testing/demo - refusing a schema/data-destructive "
            f"command ({command}). A container's env vars are process-wide, "
            f"not scoped to any working directory you copied files into. "
            f"Confirm the real target with the user before proceeding, or "
            f"point this at a database whose name actually indicates it is "
            f"disposable.\n"
        )
        return 2

    # No docker-exec target - bare local command or an invocation shape this
    # hook doesn't recognize. Best-effort check of this shell's own env, but
    # fail closed if it's not conclusively safe.
    import os
    local_values = [
        v for k, v in os.environ.items()
        if k in DB_NAME_ENV_KEYS
    ]
    if local_values and all(SAFE_NAME_PATTERN.search(v) for v in local_values):
        return 0

    sys.stderr.write(
        f"BLOCKED: {command} looks like a schema/data-destructive command "
        f"and this hook could not confirm the actual target database is a "
        f"test/testing/demo database (checked this shell's own "
        f"{'/'.join(DB_NAME_ENV_KEYS)} env vars: "
        f"{', '.join(local_values) or '<none found>'}). Ambiguous or "
        f"unresolvable targets are treated as production until proven "
        f"otherwise. Confirm the real target with the user before "
        f"proceeding.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
