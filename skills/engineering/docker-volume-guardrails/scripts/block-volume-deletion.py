#!/usr/bin/env python3
"""
PreToolUse hook (Bash matcher): unconditionally blocks Docker commands that
permanently delete one or more volumes - `docker volume rm`/`remove`,
`docker volume prune`, `docker rm -v`/`--volumes`, `docker system prune
--volumes`, and `docker compose`/`docker-compose ... down -v`/`--volumes`.

Why unconditional, with no override flag or safe-name exception (unlike
docker-db-guardrails' resolved-target check): this repo's own global
instructions already say "never delete volumes without explicit human
confirmation." A hook only ever sees the raw command string - it cannot
observe whether a human actually confirmed this specific deletion in the
conversation. The only mechanical enforcement that is actually faithful to
that rule is to never let the agent run this class of command at all,
exactly matching git-guardrails-claude-code's own precedent for force-push
and `reset --hard`: if a human has genuinely decided to delete a volume,
they run that command themselves, outside the agent.

Ordinary volume *mounting* (`docker run -v /host:/container ...`) is not
touched by this hook - it only matches `-v`/`--volumes` on the specific
subcommands that use those flags to mean "delete", never on `run`/`create`/
`compose up`, where the identical flag means "mount."
"""
import json
import shlex
import sys

# Prose-carrying flags whose value must never be scanned as a real command -
# same rationale as docker-db-guardrails: a commit message or issue body
# discussing this very hook must not be mistaken for the command it describes.
PROSE_FLAGS = {"-m", "--message", "--body", "--title", "--comment", "-F", "--file"}


def read_command() -> str:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return ""
    return payload.get("tool_input", {}).get("command", "") or ""


def tokenize(command: str) -> list[str]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=False)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return []


def scannable_tokens(tokens: list[str]) -> list[str]:
    result = []
    skip_next = False
    for tok in tokens:
        if skip_next:
            skip_next = False
            continue
        if tok in PROSE_FLAGS:
            skip_next = True
            continue
        if any(tok.startswith(f"{flag}=") for flag in PROSE_FLAGS):
            continue
        result.append(tok)
    return result


def find_reason(tokens: list[str]) -> str | None:
    for i, tok in enumerate(tokens):
        if tok not in ("docker", "docker-compose"):
            continue
        rest = tokens[i + 1:]
        if not rest:
            continue

        if tok == "docker-compose":
            if "down" in rest and any(arg in ("-v", "--volumes") for arg in rest):
                return "docker-compose down -v/--volumes deletes named volumes declared in the compose file"
            continue

        # tok == "docker"
        sub = rest[0]
        if sub == "volume" and len(rest) > 1 and rest[1] in ("rm", "remove"):
            return "docker volume rm/remove deletes a named volume permanently"
        if sub == "volume" and len(rest) > 1 and rest[1] == "prune":
            return "docker volume prune deletes all unused volumes permanently"
        if sub == "system" and len(rest) > 1 and rest[1] == "prune" \
                and any(arg in ("--volumes",) for arg in rest[2:]):
            return "docker system prune --volumes deletes volumes permanently"
        if sub == "rm" and any(arg in ("-v", "--volumes") for arg in rest[1:]):
            return "docker rm -v/--volumes removes anonymous volumes attached to the container"
        if sub == "compose" and "down" in rest and any(arg in ("-v", "--volumes") for arg in rest):
            return "docker compose down -v/--volumes deletes named volumes declared in the compose file"
    return None


def main() -> int:
    command = read_command()
    if not command:
        return 0
    tokens = tokenize(command)
    if not tokens:
        return 0

    reason = find_reason(scannable_tokens(tokens))
    if not reason:
        return 0

    sys.stderr.write(
        f"BLOCKED: this command permanently deletes one or more Docker "
        f"volumes ({reason}): {command}\n"
        f"Never delete volumes without explicit human confirmation - and a "
        f"hook cannot observe whether that confirmation happened in this "
        f"conversation, so this is never run via the agent, no exceptions. "
        f"If the user has explicitly confirmed this exact deletion, tell "
        f"them clearly what would be deleted and ask them to run the "
        f"command themselves outside the agent.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
