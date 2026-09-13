#!/bin/bash
# GIT_IDENTITY_GUARD_MARKER_V1 - do not remove this line. Used to recognize
# another copy of this same wrapper on $PATH (see the real-git search below)
# so two installed copies never mistake each other for the real git binary
# and exec-loop forever.
#
# git-identity-guard: a git wrapper enforcing one hard-coded commit identity.
#
# Installed ahead of the real git in $PATH so it applies to every process on
# this machine (interactive shells, subagents, codex subprocesses, CI-style
# scripts) regardless of whether anything sourced a shell rc file. It only
# gates `commit`, `commit-tree`, and `push` - every other subcommand, and any
# repo's own hooks (husky, lint-staged, pre-commit framework, etc.), run
# completely unaffected, since this checks identity and then execs the real
# git normally rather than replacing git's own hook mechanism.
#
# Why this exists: agents kept committing OSS-contribution work using an
# email that is never registered on the intended GitHub account (often an
# unrelated email injected into context for a different purpose - session
# metadata, a subscription address, etc.), silently breaking CLA bots and
# "Verified" commit badges across upstream PRs before anyone noticed. Docs
# alone (a rule stated in a project's own CLAUDE.md or CONTRIBUTING.md) kept
# getting overridden by an explicit `-c user.email=...` on individual commit
# commands, so enforcement has to happen at the git invocation itself.
#
# Config: ~/.config/git-identity-guard/config sets REQUIRED_NAME/REQUIRED_EMAIL.
# Set GIT_IDENTITY_GUARD_CONFIG to point elsewhere if you keep it somewhere else.
set -u

CONFIG_FILE="${GIT_IDENTITY_GUARD_CONFIG:-$HOME/.config/git-identity-guard/config}"

# Find the real git binary: the first `git` on $PATH whose file content does
# NOT carry our own marker. Checking content (not path/inode identity)
# correctly skips every copy of this wrapper even if more than one is
# installed at different paths - a path/inode comparison against just "$0"
# can't do that, and got two installed copies stuck exec-looping into each
# other in testing, each one wrongly treating the other as "the real git".
REAL_GIT=""
IFS=':' read -ra path_dirs <<< "$PATH"
for dir in "${path_dirs[@]}"; do
  candidate="$dir/git"
  if [ -x "$candidate" ] && ! grep -q "GIT_IDENTITY_GUARD_MARKER_V1" "$candidate" 2>/dev/null; then
    REAL_GIT="$candidate"
    break
  fi
done
if [ -z "$REAL_GIT" ]; then
  echo "git-identity-guard: could not find the real git binary on \$PATH (every 'git' found is a copy of this wrapper). Aborting." >&2
  exit 127
fi

if [ ! -f "$CONFIG_FILE" ]; then
  # No config installed yet - fail open rather than block every git command
  # on a machine that hasn't finished setup.
  exec "$REAL_GIT" "$@"
fi
# shellcheck source=/dev/null
source "$CONFIG_FILE"
REQUIRED_NAME="${REQUIRED_NAME:-}"
REQUIRED_EMAIL="${REQUIRED_EMAIL:-}"
if [ -z "$REQUIRED_NAME" ] || [ -z "$REQUIRED_EMAIL" ]; then
  exec "$REAL_GIT" "$@"
fi

# Replay every leading global option (-C, -c, --git-dir=, --work-tree=, etc.)
# up to the first token that isn't a recognized global flag - that token is
# the subcommand. We only need to detect "commit" / "commit-tree" / "push";
# every other subcommand (and any option layout we don't specifically
# recognize) passes straight through unexamined.
leading_args=()
subcommand=""
i=0
args=("$@")
n=${#args[@]}
while [ "$i" -lt "$n" ]; do
  arg="${args[$i]}"
  case "$arg" in
    -C|--git-dir|--work-tree|--namespace|--super-prefix)
      leading_args+=("$arg" "${args[$((i+1))]}")
      i=$((i+2))
      ;;
    -c)
      leading_args+=("-c" "${args[$((i+1))]}")
      i=$((i+2))
      ;;
    --git-dir=*|--work-tree=*|--namespace=*)
      leading_args+=("$arg")
      i=$((i+1))
      ;;
    -p|--paginate|--no-pager|--no-replace-objects|--bare|--no-lazy-fetch|--no-optional-locks|--literal-pathspecs|--glob-pathspecs|--noglob-pathspecs|--icase-pathspecs)
      leading_args+=("$arg")
      i=$((i+1))
      ;;
    -*)
      leading_args+=("$arg")
      i=$((i+1))
      ;;
    *)
      subcommand="$arg"
      break
      ;;
  esac
done

check_identity() {
  # GIT_AUTHOR_*/GIT_COMMITTER_* env vars override `git config user.*` for the
  # actual commit (this is exactly how `commit-tree` is normally driven, and
  # how a bypass could slip past a check that only reads `git config`), so
  # check those first if set - they win over config, same as real git does.
  local effective_name effective_email
  effective_name="${GIT_AUTHOR_NAME:-${GIT_COMMITTER_NAME:-}}"
  effective_email="${GIT_AUTHOR_EMAIL:-${GIT_COMMITTER_EMAIL:-}}"
  if [ -z "$effective_name" ]; then
    effective_name=$("$REAL_GIT" "${leading_args[@]}" config user.name 2>/dev/null || echo "")
  fi
  if [ -z "$effective_email" ]; then
    effective_email=$("$REAL_GIT" "${leading_args[@]}" config user.email 2>/dev/null || echo "")
  fi
  # commit-tree honors GIT_AUTHOR_* and GIT_COMMITTER_* independently (they
  # need not match each other) - check both explicitly when either is set.
  local author_name="${GIT_AUTHOR_NAME:-$effective_name}"
  local author_email="${GIT_AUTHOR_EMAIL:-$effective_email}"
  local committer_name="${GIT_COMMITTER_NAME:-$effective_name}"
  local committer_email="${GIT_COMMITTER_EMAIL:-$effective_email}"
  if [ "$author_email" != "$REQUIRED_EMAIL" ] || [ "$author_name" != "$REQUIRED_NAME" ] ||
     [ "$committer_email" != "$REQUIRED_EMAIL" ] || [ "$committer_name" != "$REQUIRED_NAME" ]; then
    echo "" >&2
    echo "BLOCKED: git commit identity must be exactly '$REQUIRED_NAME <$REQUIRED_EMAIL>'." >&2
    echo "  Author:    '$author_name <$author_email>'" >&2
    echo "  Committer: '$committer_name <$committer_email>'" >&2
    echo "" >&2
    echo "Remove any -c user.email=... / -c user.name=... override, or any" >&2
    echo "GIT_AUTHOR_*/GIT_COMMITTER_* env var - the global git config is already" >&2
    echo "correct without one. (Config: $CONFIG_FILE)" >&2
    echo "" >&2
    return 1
  fi
  return 0
}

check_outgoing_commits() {
  local bad
  bad=$("$REAL_GIT" "${leading_args[@]}" log HEAD --not --remotes \
        --format='%H|%an|%ae|%cn|%ce' 2>/dev/null | \
        awk -F'|' -v n="$REQUIRED_NAME" -v e="$REQUIRED_EMAIL" \
          '$2!=n || $3!=e || $4!=n || $5!=e {print}')
  if [ -z "$bad" ]; then
    return 0
  fi
  echo "" >&2
  echo "BLOCKED PUSH: commit(s) about to be pushed have the wrong author/committer identity:" >&2
  echo "$bad" | while IFS='|' read -r sha an ae cn ce; do
    echo "  ${sha:0:8}  author=$an <$ae>  committer=$cn <$ce>" >&2
  done
  echo "" >&2
  echo "Every commit pushed anywhere on this machine must be authored AND committed as" >&2
  echo "'$REQUIRED_NAME <$REQUIRED_EMAIL>' - no exceptions, including plumbing commands" >&2
  echo "(commit-tree, rebase, cherry-pick) that bypass a commit-time check." >&2
  echo "Fix: git commit --amend --reset-author (or rebase -i + amend each bad commit" >&2
  echo "with the correct -c user.name=/-c user.email=), then re-push." >&2
  return 1
}

case "$subcommand" in
  commit|commit-tree)
    if ! check_identity; then
      exit 1
    fi
    ;;
  push)
    if ! check_outgoing_commits; then
      exit 1
    fi
    ;;
esac

exec "$REAL_GIT" "$@"
