---
"ai-engineering-workflow-skills": minor
---

Add the `git-identity-guard` skill: a `$PATH`-level git wrapper that hard-blocks any `commit`, `commit-tree`, or `push` whose author or committer identity does not match one configured name/email.

It is a wrapper rather than a Claude Code `PreToolUse` hook because identity enforcement has to cover `codex exec` subprocesses, dispatched subagents, and plain terminals, none of which go through this session's hook chain.

The commit-time gate checks `-c user.*` overrides, `--author`, `GIT_AUTHOR_*`/`GIT_COMMITTER_*` (author and committer resolved independently), and the `git config` default. The push-time backstop parses the invocation's actual refspecs, so it also covers a branch other than the checked-out one, a raw SHA, a tag, a detached HEAD, and `--all`/`--tags`. `GIT_IDENTITY_GUARD_CONFIG` is not an override: set to something unreadable, it refuses gated subcommands rather than failing open.
