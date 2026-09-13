---
name: git-identity-guard
description: Install a $PATH-level git wrapper that hard-blocks any commit or push whose author/committer identity doesn't match one configured name/email, everywhere on the machine, with no override. Use when commits keep landing under the wrong email (breaking CLA bots, GitHub's "Verified" badge, or account-linked contribution credit), when a project's own docs say "always commit as X" but agents keep overriding it anyway, or when setting up a fresh machine/session for an external-contribution campaign.
---

# Git Identity Guard

Installs a `git` shim ahead of the real binary in `$PATH` that inspects every
`commit`, `commit-tree`, and `push` invocation and refuses to let one through
under the wrong author/committer identity - regardless of what tries to set
one.

## The problem this solves

A documented rule ("always commit as `you <you@example.com>`") is not
self-enforcing. On a real campaign, this showed up as:

- The correct identity was already the git **global default**.
- Every commit still explicitly overrode it with `-c user.email=...`, using
  a *different* email available in context for an unrelated reason (a
  subscription/session address, not the account's own email) - because
  nothing stopped that override from winning.
- The result: dozens of PRs across several upstream repos landed
  unverifiable - GitHub had no account to link the commit to at all (not
  merely "unverified"), so CLA-assistant bots rejected them and the commits
  showed no avatar/username in GitHub's UI. This went unnoticed for a long
  stretch because nothing failed *loudly* - the commits succeeded, the pushes
  succeeded, only a downstream bot comment surfaced it, per PR, much later.

A rule stated once in a project's `CLAUDE.md`/`AGENTS.md` gets re-read (or
not) by every fresh agent context. An explicit command-line override always
wins over a global default, so restating the correct default doesn't help
once something is actively overriding it.

## Why a `$PATH` shim, not a Claude Code `PreToolUse` hook

This pack's other guardrails (`git-guardrails-claude-code`,
`docker-volume-guardrails`, `docker-db-guardrails`) are Claude Code
`PreToolUse` hooks - they intercept a tool call *before Claude's own Bash
tool runs it*. That pattern is a good fit for those because the thing being
protected against is Claude Code's own action.

Identity enforcement has a wider blast radius: the same OSS-contribution
campaign that motivated this skill also runs work through `codex exec`
subprocesses and dispatched subagents, none of which go through this
session's own `PreToolUse` hook chain - a hook registered in
`~/.claude/settings.json` only ever sees tool calls from *this* Claude Code
session. A `PreToolUse` hook here would still leave every other process on
the machine free to commit under the wrong identity.

A `$PATH` shim is transparent to *anything* that shells out to `git` -
this session, a subagent, a `codex exec` subprocess, a plain terminal, a cron
job. It also composes safely with a repo's own hooks (husky, lint-staged,
pre-commit framework): those live in `.git/hooks/` and run as part of the
*real* git binary's own execution, which this shim calls via `exec` after
its own check passes - it never touches `core.hooksPath` or a repo's hook
files, so nothing about a project's existing tooling changes.

## What Gets Blocked

- `git commit` (any form) where the effective `user.name`/`user.email` -
  from an explicit `-c user.name=...`/`-c user.email=...`, or a plain
  `git config` default - doesn't match the configured identity.
- `git commit-tree` under a `GIT_AUTHOR_*`/`GIT_COMMITTER_*` environment
  override that doesn't match (this is the one commit-creation path that
  bypasses git's own hook system entirely, so a hook-based approach alone
  cannot catch it - see "Known limitations" for why the shim's push-time
  check is the actual backstop for this case).
- `git push` of any commit - however it was created (`commit`,
  `commit-tree`, `rebase`, `cherry-pick`, an inherited bad commit from
  upstream history) - not already reachable from a known remote-tracking
  branch, if its author or committer identity doesn't match.

Every other subcommand, and a repo's own commit-time hooks, are untouched.

## Steps

### 1. Decide the identity

Almost always: whatever `git config --global user.name`/`user.email`
already is. Confirm with the user if there's any doubt - this is the one
identity every commit on the machine will be forced to use.

### 2. Run the installer

```bash
bash scripts/install.sh                       # uses the existing global git config
# or, explicitly:
bash scripts/install.sh "Your Name" "you@example.com"
# or, to a specific directory (must precede the real git in $PATH):
bash scripts/install.sh "Your Name" "you@example.com" ~/.local/bin
```

This writes `~/.config/git-identity-guard/config`, copies
[scripts/git-identity-guard.sh](scripts/git-identity-guard.sh) to
`<install-dir>/git`, `chmod +x`s it, sets the git global config to match
(belt-and-suspenders for tools that read config directly), and verifies
`which git` now resolves to the wrapper.

If the installer warns that `$PATH` doesn't pick up the wrapper, add the
printed `export PATH=...` line to the shell rc file and open a new shell
before relying on this.

### 3. Verify

Test both directions before trusting this in a new environment:

```bash
cd "$(mktemp -d)" && git init -q
echo x > x.txt && git add x.txt

# Should be BLOCKED (exit 1) - wrong email explicitly forced:
git -c user.name="Your Name" -c user.email="wrong@example.com" commit -m "should fail"

# Should SUCCEED (exit 0) - correct identity:
git -c user.name="Your Name" -c user.email="you@example.com" commit -m "should pass"

# Should be BLOCKED (exit 1) - commit-tree bypass with a bad env override:
echo y > y.txt && git add y.txt
TREE=$(git write-tree); PARENT=$(git rev-parse HEAD)
GIT_AUTHOR_NAME="Your Name" GIT_AUTHOR_EMAIL="wrong@example.com" \
GIT_COMMITTER_NAME="Your Name" GIT_COMMITTER_EMAIL="wrong@example.com" \
  git commit-tree "$TREE" -p "$PARENT" -m "should fail too"
```

Then confirm a repo's own hooks still fire (coexistence, not replacement):

```bash
mkdir -p .git/hooks
printf '#!/bin/bash\necho REPO HOOK FIRED\n' > .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
echo z > z.txt && git add z.txt
git -c user.name="Your Name" -c user.email="you@example.com" commit -m "hook coexistence check"
# Expected output includes both "REPO HOOK FIRED" and a successful commit.
```

## Known limitations

- `check_identity` (the commit-time gate) reads `GIT_AUTHOR_*`/
  `GIT_COMMITTER_*` env vars and `-c`/`git config` overrides, which covers
  every realistic way a commit gets created *through this wrapper*. It
  cannot see a commit created by a process that bypassed the wrapper
  entirely (e.g. a differently-pathed `git` binary invoked by full path, or
  a language binding that calls libgit2 directly instead of shelling out).
  The `push`-time check is the actual backstop for those: it inspects the
  real metadata of every commit about to leave the machine, regardless of
  how it was created, and blocks the push if any of them don't match - so
  nothing wrong reaches a remote even if something upstream of push slipped
  past the commit-time gate.
- Requires `<install-dir>` to precede the real git's directory in `$PATH`.
  `install.sh` checks this and warns rather than silently no-op'ing, but it
  can't force a running shell to pick up a `$PATH` change - a new shell is
  needed if it warns.
- No override flag or environment variable exists by design, matching this
  pack's other unconditional guardrails (`docker-volume-guardrails`) - if
  this blocks a commit under a genuinely different, correct identity (e.g.
  co-maintaining someone else's fork under their name), the fix is to run
  `scripts/install.sh` again with the new identity, not to bypass the check
  for one commit.
