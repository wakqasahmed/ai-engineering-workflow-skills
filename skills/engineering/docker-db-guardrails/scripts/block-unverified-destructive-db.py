#!/usr/bin/env python3
"""
PreToolUse hook (Bash matcher): blocks schema/data-wipe commands (Laravel
artisan migrate:fresh / migrate:refresh / migrate:reset / db:wipe, Rails
db:drop / db:reset, prisma migrate reset, sequelize db:drop, alembic
downgrade base, raw DROP DATABASE / DROP TABLE / DROP SCHEMA / TRUNCATE,
dropdb / mysqladmin drop, mongo dropDatabase, redis FLUSHALL / FLUSHDB)
unless the actual resolved target database visibly indicates it is
disposable (name contains test/testing/demo/sandbox/scratch).

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
commit message or GH issue body describing this very hook) cannot make the
command *look* like a real invocation of a database tool. Prose values are
excluded from the invoking-tool and target-name decisions only; their text
is still scanned for destructive keywords, so a prose value can never hide a
real destructive command from the pattern check.
"""
import json
import os
import re
import shlex
import subprocess
import sys

DESTRUCTIVE_PATTERN = re.compile(
    r"migrate:fresh|migrate:refresh|migrate:reset|db:wipe|db:drop|db:reset"
    r"|migrate\s+reset"
    r"|drop\s+(database|table|schema)"
    r"|truncate\s+(table\s+)?\S"
    r"|dropdatabase"
    r"|\bdropdb\b"
    r"|mysqladmin[^;&|]*\bdrop\b"
    r"|downgrade\s+base"
    r"|\bflushall\b|\bflushdb\b",
    re.IGNORECASE,
)
INVOKING_TOOLS = {
    "artisan", "psql", "mysql", "mariadb", "sqlite3", "mongosh", "mongo",
    "redis-cli", "dropdb", "mysqladmin", "rails", "rake", "prisma",
    "sequelize", "alembic",
}

# Anchored on token boundaries, not a bare substring match: an unanchored
# `test|demo` search reads db_latest, contest_live, attestation and
# demographics as "safe" and lets a production wipe through. Both `test` and
# `testing` are listed because boundary-anchored `test` alone does not match
# `testing` (the `ing` fails the trailing boundary).
SAFE_NAME_PATTERN = re.compile(
    r"(^|[_.\-])(test|testing|demo|sandbox|scratch)([_.\-]|$)", re.IGNORECASE
)

# Single source of truth for every "which env var names the database"
# lookup - a container's env (container_db_values) and this shell's own env
# (the local fallback in main()) both use this, so they can never drift out
# of sync with each other again the way they briefly did during review.
DB_NAME_ENV_KEYS = ("DB_DATABASE", "DB_NAME", "POSTGRES_DB", "MYSQL_DATABASE", "MARIADB_DATABASE")

# Flags whose value is free-form prose, not a command/argument to inspect.
SHORT_PROSE_FLAGS = ("-m", "-F")
LONG_PROSE_FLAGS = ("--message", "--body", "--title", "--comment", "--file")
PROSE_FLAGS = set(SHORT_PROSE_FLAGS) | set(LONG_PROSE_FLAGS)

CONTAINER_RUNNERS = {"docker", "docker-compose", "compose", "podman"}
SHELL_TOOLS = {"bash", "sh", "zsh", "dash", "ksh"}
CHAIN_TOKENS = {"&&", "||", ";", "|", "&"}

# Which flag actually names a *database* for each client, and which flags
# consume a following value (so a value is never mistaken for a positional
# database name). Deliberately tool-specific: Laravel's `artisan --database`
# names a *connection* from config/database.php, not a database, so artisan
# is absent here and can never whitelist itself with `--database=testing`.
TOOL_DB_FLAGS = {
    "psql": {"-d", "--dbname"},
    "mysql": {"-D", "--database"},
    "mariadb": {"-D", "--database"},
    "dropdb": set(),
}
TOOL_VALUE_FLAGS = {
    "psql": {"-c", "-f", "-h", "-p", "-U", "-v", "-o", "-d", "-F", "-P", "-R", "-T", "-L"},
    "mysql": {"-e", "-h", "-P", "-u", "-D", "-S", "-r", "--execute", "--host", "--user"},
    "mariadb": {"-e", "-h", "-P", "-u", "-D", "-S", "-r", "--execute", "--host", "--user"},
    "dropdb": {"-h", "-p", "-U"},
}
# Clients whose trailing positional argument is the database actually acted
# on - for mysql this outranks -D, so both must be collected and both must
# look safe.
POSITIONAL_DB_TOOLS = {"psql", "mysql", "mariadb", "dropdb"}

MAX_SHELL_NESTING = 3


class InvalidPayload(Exception):
    pass


def read_command(stream=sys.stdin) -> str:
    """Raises InvalidPayload rather than returning "" for a malformed or
    structurally unexpected hook payload. Returning "" made main() fall
    through to `return 0` and run the command unchecked - a fail-open shape
    on exactly the malformed input this hook must be paranoid about."""
    try:
        payload = json.load(stream)
    except (json.JSONDecodeError, ValueError) as exc:
        raise InvalidPayload(f"payload is not valid JSON ({exc})")
    if not isinstance(payload, dict):
        raise InvalidPayload("payload is not a JSON object")
    tool_input = payload.get("tool_input", {})
    if not isinstance(tool_input, dict):
        raise InvalidPayload("tool_input is not a JSON object")
    command = tool_input.get("command", "")
    if command is None:
        return ""
    if not isinstance(command, str):
        raise InvalidPayload("tool_input.command is not a string")
    return command


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


def command_words(tokens: list[str]) -> list[str]:
    """Tokens that are real command words, excluding any token that is the
    *value* of a prose flag (its own commit message, PR body, issue title).
    Prose values are excluded from the invoking-tool and database-name
    decisions only - main() still scans their text for destructive
    keywords, so a prose value cannot hide a real destructive command."""
    words = []
    skip_next = False
    for tok in tokens:
        if skip_next:
            skip_next = False
            continue
        if tok in PROSE_FLAGS:
            skip_next = True
            continue
        # A short flag glued directly onto its value with no space
        # (-m"a message here" shlex-tokenizes as one word). Only genuinely
        # short flags qualify: a startswith() test against the long forms
        # would also swallow an arbitrary token that merely begins with
        # "-m"/"--f", dropping real arguments from the scan.
        if any(tok.startswith(flag) and len(tok) > len(flag) for flag in SHORT_PROSE_FLAGS):
            continue
        # Long forms must be the exact "--flag=value" shape, not any prefix.
        if any(tok.startswith(flag + "=") for flag in LONG_PROSE_FLAGS):
            continue
        words.append(tok)
    return words


def shell_payloads(tokens: list[str]) -> list[str]:
    """Command strings handed to a nested shell (`bash -c "..."`). The whole
    inner command arrives as ONE token, so without re-tokenizing it no token
    ever equals `artisan` and the invoking-tool check silently passes."""
    payloads = []
    for i, tok in enumerate(tokens):
        if os.path.basename(tok) not in SHELL_TOOLS:
            continue
        j = i + 1
        while j < len(tokens) and tokens[j].startswith("-"):
            if "c" in tokens[j].lstrip("-"):
                if j + 1 < len(tokens):
                    payloads.append(tokens[j + 1])
                break
            j += 1
    return payloads


def expand(tokens: list[str], depth: int = 0) -> list[list[str]] | None:
    """All token lists to analyse: the outer command plus every nested
    `bash -c` payload, recursively. None means a payload could not be
    tokenized - fail closed."""
    groups = [tokens]
    if depth >= MAX_SHELL_NESTING:
        return groups
    for payload in shell_payloads(command_words(tokens)):
        inner = tokenize(payload)
        if inner is None:
            return None
        nested = expand(inner, depth + 1)
        if nested is None:
            return None
        groups.extend(nested)
    return groups


def find_container(tokens: list[str]) -> str | None:
    """`exec` preceded by ANY earlier docker/compose token, not just the
    immediately preceding one - `docker compose -f compose.yml exec app`
    puts the yml path directly before `exec`."""
    exec_index = None
    for i, tok in enumerate(tokens):
        if tok == "exec" and any(
            os.path.basename(t) in CONTAINER_RUNNERS for t in tokens[:i]
        ):
            exec_index = i
            break
    if exec_index is None:
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


def _scan_tool_args(tokens: list[str], start: int, tool: str) -> tuple[int, list[str]]:
    db_flags = TOOL_DB_FLAGS[tool]
    value_flags = TOOL_VALUE_FLAGS[tool]
    names = []
    i = start + 1
    while i < len(tokens) and tokens[i] not in CHAIN_TOKENS:
        tok = tokens[i]
        if tok in db_flags and i + 1 < len(tokens):
            names.append(tokens[i + 1])
            i += 2
            continue
        glued = [f for f in db_flags if f.startswith("--") and tok.startswith(f + "=")]
        if glued:
            names.append(tok[len(glued[0]) + 1:])
            i += 1
            continue
        if tok in value_flags:
            i += 2
            continue
        if tok.startswith("-"):
            i += 1
            continue
        if tool in POSITIONAL_DB_TOOLS:
            names.append(tok)
        i += 1
    return i, names


def collect_explicit_dbnames(tokens: list[str]) -> list[str]:
    """EVERY explicitly named database in the command, not just the first.
    Returning on the first match let one safe name whitelist a whole
    chained command line (`psql -d test -c ... && psql -d appdb -c ...`)."""
    names = []
    i = 0
    while i < len(tokens):
        tool = os.path.basename(tokens[i])
        if tool in TOOL_DB_FLAGS:
            i, found = _scan_tool_args(tokens, i, tool)
            names.extend(found)
            continue
        i += 1
    return names


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
    try:
        command = read_command()
    except InvalidPayload as exc:
        sys.stderr.write(
            f"BLOCKED: could not read this hook's input payload ({exc}), so "
            f"the command could not be checked for schema/data-destructive "
            f"operations. An unreadable payload is treated as unsafe.\n"
        )
        return 2
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

    groups = expand(tokens)
    if groups is None:
        sys.stderr.write(
            f"BLOCKED: could not safely tokenize a nested shell command "
            f"inside {command} while checking it for schema/data-destructive "
            f"operations. This hook cannot verify a command it cannot parse.\n"
        )
        return 2

    # Compare on the basename: a path-qualified binary
    # (/tmp/test-branch/artisan) is the same tool as `artisan`, and exact
    # token equality let the original incident command straight through.
    scanned_groups = [command_words(g) for g in groups]
    tool_hits = [
        tok for words in scanned_groups for tok in words
        if os.path.basename(tok) in INVOKING_TOOLS
    ]
    if not tool_hits:
        return 0

    explicit_dbs = [
        name for words in scanned_groups for name in collect_explicit_dbnames(words)
    ]

    # Chained invocations are only as resolvable as their least-resolved
    # member: a safe explicit name on one link must not vouch for a sibling
    # link whose target this hook never resolved at all.
    chained = any(tok in CHAIN_TOKENS for g in groups for tok in g)
    if chained and len(tool_hits) > 1 and len(explicit_dbs) < len(tool_hits):
        sys.stderr.write(
            f"BLOCKED: {command} chains more than one database-tool "
            f"invocation and this hook cannot resolve each one's target "
            f"separately. Run them one at a time, or name each target "
            f"explicitly.\n"
        )
        return 2

    if explicit_dbs:
        # Unanimity, mirroring the container-env rule below: one unsafe name
        # blocks, rather than one safe name rescuing everything else on the
        # same command line.
        unsafe = [n for n in explicit_dbs if not SAFE_NAME_PATTERN.search(n)]
        if not unsafe:
            return 0
        sys.stderr.write(
            f"BLOCKED: explicitly named database target(s) "
            f"{', '.join(unsafe)} do not visibly indicate a disposable "
            f"database - refusing a schema/data-destructive command "
            f"({command}). An explicitly named target always wins over any "
            f"container or shell environment variable.\n"
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
            f"indicate a disposable database - refusing a schema/data-"
            f"destructive command ({command}). A container's env vars are "
            f"process-wide, not scoped to any working directory you copied "
            f"files into. Confirm the real target with the user before "
            f"proceeding, or point this at a database whose name actually "
            f"indicates it is disposable.\n"
        )
        return 2

    # No docker-exec target - bare local command or an invocation shape this
    # hook doesn't recognize. Best-effort check of this shell's own env, but
    # fail closed if it's not conclusively safe.
    local_values = [
        v for k, v in os.environ.items()
        if k in DB_NAME_ENV_KEYS
    ]
    if local_values and all(SAFE_NAME_PATTERN.search(v) for v in local_values):
        return 0

    sys.stderr.write(
        f"BLOCKED: {command} looks like a schema/data-destructive command "
        f"and this hook could not confirm the actual target database is a "
        f"disposable one (checked this shell's own "
        f"{'/'.join(DB_NAME_ENV_KEYS)} env vars: "
        f"{', '.join(local_values) or '<none found>'}). Ambiguous or "
        f"unresolvable targets are treated as production until proven "
        f"otherwise. Confirm the real target with the user before "
        f"proceeding.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
