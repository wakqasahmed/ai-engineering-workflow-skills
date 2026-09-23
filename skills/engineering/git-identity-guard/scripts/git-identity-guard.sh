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
# GIT_IDENTITY_GUARD_CONFIG may point elsewhere, but it is not an escape
# hatch: if it is set and does not name a readable config, every gated
# subcommand is refused instead of being let through.
set -u

if [ -n "${GIT_IDENTITY_GUARD_CONFIG-}" ]; then
  CONFIG_FILE="$GIT_IDENTITY_GUARD_CONFIG"
  CONFIG_EXPLICIT=1
else
  CONFIG_FILE="${HOME-}/.config/git-identity-guard/config"
  CONFIG_EXPLICIT=0
fi

# Find the real git binary: the first `git` on $PATH that is not a copy of
# this wrapper. Detecting copies by content (not by path/inode identity)
# correctly skips every copy even if more than one is installed at different
# paths - a path/inode comparison against just "$0" can't do that, and got
# two installed copies stuck exec-looping into each other in testing, each
# one wrongly treating the other as "the real git".
is_guard_copy() {
  local file="$1"
  # A copy of this wrapper is always a shell script whose marker sits in the
  # header. Requiring a shebang and only scanning the header keeps the real
  # (multi-MB, binary) git out of the grep entirely, and stops an unrelated
  # git-adjacent script on $PATH that merely mentions the variable name
  # somewhere - a mise/asdf/direnv shim sourcing an env file, say - from
  # being mistaken for a wrapper copy.
  [ "$(head -c 2 "$file" 2>/dev/null)" = '#!' ] || return 1
  head -n 40 "$file" 2>/dev/null | grep -q -m1 "GIT_IDENTITY_GUARD_MARKER_V1"
}

REAL_GIT=""
IFS=':' read -ra path_dirs <<< "$PATH"
for dir in "${path_dirs[@]+"${path_dirs[@]}"}"; do
  # An empty $PATH entry means "the current directory"; taking it literally
  # builds the candidate "/git".
  [ -n "$dir" ] || continue
  candidate="$dir/git"
  if [ -x "$candidate" ] && [ -f "$candidate" ] && ! is_guard_copy "$candidate"; then
    REAL_GIT="$candidate"
    break
  fi
done
if [ -z "$REAL_GIT" ]; then
  echo "git-identity-guard: could not find the real git binary on \$PATH (every 'git' found is a copy of this wrapper). Aborting." >&2
  exit 127
fi

# Replay every leading global option (-C, -c, --git-dir=, --work-tree=, etc.)
# up to the first token that isn't a recognized global flag - that token is
# the subcommand.
leading_args=()
subcommand=""
subcommand_index=-1
unknown_option_seen=0
args=("$@")
n=${#args[@]}
i=0
while [ "$i" -lt "$n" ]; do
  arg="${args[$i]}"
  case "$arg" in
    -C|--git-dir|--work-tree|--namespace|--super-prefix|-c)
      # Bounds-check: these take a separate value, and as a trailing argument
      # there is nothing to read. Hand the whole thing to real git so it
      # prints its own usage error instead of dying on an unbound variable.
      if [ "$((i + 1))" -ge "$n" ]; then
        exec "$REAL_GIT" "$@"
      fi
      leading_args+=("$arg" "${args[$((i + 1))]}")
      i=$((i + 2))
      ;;
    --git-dir=*|--work-tree=*|--namespace=*)
      leading_args+=("$arg")
      i=$((i + 1))
      ;;
    -p|--paginate|--no-pager|--no-replace-objects|--bare|--no-lazy-fetch|--no-optional-locks|--literal-pathspecs|--glob-pathspecs|--noglob-pathspecs|--icase-pathspecs)
      leading_args+=("$arg")
      i=$((i + 1))
      ;;
    -*)
      unknown_option_seen=1
      leading_args+=("$arg")
      i=$((i + 1))
      ;;
    *)
      subcommand="$arg"
      subcommand_index=$i
      break
      ;;
  esac
done

is_gated() {
  case "$1" in
    commit|commit-tree|push) return 0 ;;
    *) return 1 ;;
  esac
}

# Fail closed on an argument layout this parser did not recognize, instead of
# letting an unparsed shape skip the check entirely.
if [ -z "$subcommand" ]; then
  # Every token looked like an option. Nothing should be gated here, but if a
  # gated word is in argv anyway, the parse was wrong - check rather than wave
  # it through.
  for arg in "${args[@]+"${args[@]}"}"; do
    if is_gated "$arg"; then
      subcommand="$arg"
      subcommand_index=-1
      break
    fi
  done
elif [ "$unknown_option_seen" -eq 1 ] && ! is_gated "$subcommand" &&
     [ "$((subcommand_index + 1))" -lt "$n" ] && is_gated "${args[$((subcommand_index + 1))]}"; then
  # An unrecognized global option that turns out to take a separate value
  # would make that value look like the subcommand, pushing the real one one
  # slot right. Treat that slot as the subcommand rather than fail open.
  subcommand_index=$((subcommand_index + 1))
  subcommand="${args[$subcommand_index]}"
fi

if ! is_gated "$subcommand"; then
  exec "$REAL_GIT" "$@"
fi

refuse() {
  echo "" >&2
  echo "BLOCKED: git-identity-guard cannot verify the commit identity for '$subcommand'." >&2
  echo "  $1" >&2
  echo "  Config: $CONFIG_FILE" >&2
  echo "" >&2
  exit 1
}

if [ ! -f "$CONFIG_FILE" ] || [ ! -r "$CONFIG_FILE" ]; then
  if [ "$CONFIG_EXPLICIT" -eq 1 ]; then
    # GIT_IDENTITY_GUARD_CONFIG was set deliberately. Letting a missing,
    # unreadable, or non-regular target (/dev/null, a directory, a dangling
    # path) fall through would turn this one variable into a kill switch.
    refuse "GIT_IDENTITY_GUARD_CONFIG is set but is not a readable regular config file."
  fi
  # No config installed at the default path yet - fail open rather than
  # block every git command on a machine that hasn't finished setup.
  exec "$REAL_GIT" "$@"
fi

# Parse the config rather than `source`-ing it: the config file is only ever
# two name/value pairs, and sourcing it executes whatever is in it as shell.
read_config_value() {
  local key="$1" line value=""
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      "$key"=*) ;;
      *) continue ;;
    esac
    value="${line#*=}"
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"
  done < "$CONFIG_FILE"
  printf '%s' "$value"
}

REQUIRED_NAME="$(read_config_value REQUIRED_NAME)"
REQUIRED_EMAIL="$(read_config_value REQUIRED_EMAIL)"
if [ -z "$REQUIRED_NAME" ] || [ -z "$REQUIRED_EMAIL" ]; then
  if [ "$CONFIG_EXPLICIT" -eq 1 ]; then
    refuse "The config names no REQUIRED_NAME/REQUIRED_EMAIL."
  fi
  exec "$REAL_GIT" "$@"
fi

real_git() {
  "$REAL_GIT" "${leading_args[@]+"${leading_args[@]}"}" "$@"
}

identity_error() {
  echo "" >&2
  echo "BLOCKED: git commit identity must be exactly '$REQUIRED_NAME <$REQUIRED_EMAIL>'." >&2
  echo "  $1" >&2
  echo "" >&2
  echo "Remove any -c user.email=... / -c user.name=... override, any --author=..." >&2
  echo "override, and any GIT_AUTHOR_*/GIT_COMMITTER_* env var - the global git" >&2
  echo "config is already correct without one. (Config: $CONFIG_FILE)" >&2
  echo "" >&2
}

# `--author="Name <email>"` sets the author directly and is not visible in
# `git config` or in any env var, so it needs its own check. It is validated
# rather than banned, because `git am` and `rebase --continue` legitimately
# pass a correct one through.
check_author_flag() {
  local idx author="" found=0 arg
  idx=$((subcommand_index + 1))
  if [ "$subcommand_index" -lt 0 ]; then
    idx=0
  fi
  while [ "$idx" -lt "$n" ]; do
    arg="${args[$idx]}"
    case "$arg" in
      --) break ;;
      --author=*)
        author="${arg#--author=}"
        found=1
        ;;
      --author)
        if [ "$((idx + 1))" -lt "$n" ]; then
          author="${args[$((idx + 1))]}"
          found=1
          idx=$((idx + 1))
        fi
        ;;
    esac
    idx=$((idx + 1))
  done
  if [ "$found" -eq 0 ]; then
    return 0
  fi
  if [ "$author" != "$REQUIRED_NAME <$REQUIRED_EMAIL>" ]; then
    identity_error "--author '$author' does not match the required identity."
    return 1
  fi
  return 0
}

check_identity() {
  # GIT_AUTHOR_*/GIT_COMMITTER_* env vars override `git config user.*` for the
  # actual commit (this is exactly how `commit-tree` is normally driven, and
  # how a bypass could slip past a check that only reads `git config`), so
  # check those first if set - they win over config, same as real git does.
  # Author and committer are resolved independently, each falling back to
  # config and never to the other's env var: a correct GIT_COMMITTER_EMAIL
  # must not launder a wrong configured author.
  local config_name config_email
  config_name="$(real_git config user.name 2>/dev/null || echo "")"
  config_email="$(real_git config user.email 2>/dev/null || echo "")"

  local author_name author_email committer_name committer_email
  author_name="${GIT_AUTHOR_NAME:-$config_name}"
  author_email="${GIT_AUTHOR_EMAIL:-$config_email}"
  committer_name="${GIT_COMMITTER_NAME:-$config_name}"
  committer_email="${GIT_COMMITTER_EMAIL:-$config_email}"

  if [ "$author_email" != "$REQUIRED_EMAIL" ] || [ "$author_name" != "$REQUIRED_NAME" ] ||
     [ "$committer_email" != "$REQUIRED_EMAIL" ] || [ "$committer_name" != "$REQUIRED_NAME" ]; then
    identity_error "Author:    '$author_name <$author_email>'
  Committer: '$committer_name <$committer_email>'"
    return 1
  fi
  if [ "$subcommand" = "commit" ] && ! check_author_flag; then
    return 1
  fi
  return 0
}

# Work out what a `git push` invocation actually sends, so the backstop
# inspects those commits instead of assuming HEAD. Sets push_remote and
# push_refspecs; returns 1 when nothing is being pushed (a delete).
push_remote=""
push_refspecs=()
push_all_refs=0
parse_push_args() {
  local idx arg
  idx=$((subcommand_index + 1))
  if [ "$subcommand_index" -lt 0 ]; then
    idx=0
  fi
  while [ "$idx" -lt "$n" ]; do
    arg="${args[$idx]}"
    case "$arg" in
      --delete|-d)
        return 1
        ;;
      --all|--branches|--mirror|--tags|--follow-tags)
        push_all_refs=1
        ;;
      --repo|--receive-pack|--exec|-o|--push-option)
        # Options that take a separate value; skip the value too so it is
        # never mistaken for a remote or a refspec.
        idx=$((idx + 1))
        ;;
      --)
        ;;
      -*)
        ;;
      *)
        if [ -z "$push_remote" ]; then
          push_remote="$arg"
        else
          push_refspecs+=("$arg")
        fi
        ;;
    esac
    idx=$((idx + 1))
  done
  return 0
}

# Which commits count as "leaving this machine": everything reachable from
# what is being pushed that the destination remote does not already have.
# Scoping the exclusion to the destination remote (rather than every
# remote-tracking ref) means a commit that reached one remote is still
# checked on its way to a different one.
push_exclusions() {
  if [ -n "$push_remote" ] && real_git config "remote.$push_remote.url" >/dev/null 2>&1 &&
     [ -n "$(real_git for-each-ref --count=1 --format='%(refname)' "refs/remotes/$push_remote/" 2>/dev/null)" ]; then
    printf '%s\n%s\n' "--not" "--remotes=$push_remote"
  else
    # A URL instead of a configured remote name, or a remote with no
    # tracking refs yet: excluding only that remote would drag the whole
    # inherited upstream history into the check on a first push.
    printf '%s\n%s\n' "--not" "--remotes"
  fi
}

check_outgoing_commits() {
  # Exception: a commit whose committer is GitHub's own web-merge identity
  # ("GitHub <noreply@github.com>", e.g. from a squash-merge or "Update
  # branch" button click) is created by GitHub itself, not authored locally -
  # its author *name* is the account's GitHub display name, not our git
  # config value, and that's correct/expected, not a violation. Only the
  # author *email* still has to be ours, since that's the actual signal CLA
  # bots and "Verified"/account-linking checks use.
  if ! parse_push_args; then
    return 0
  fi

  local -a tips=()
  local spec local_ref
  if [ "$push_all_refs" -eq 1 ] || [ "${#push_refspecs[@]}" -eq 0 ]; then
    tips=("--branches" "--tags")
  else
    for spec in "${push_refspecs[@]}"; do
      spec="${spec#+}"
      case "$spec" in
        *:*) local_ref="${spec%%:*}" ;;
        *) local_ref="$spec" ;;
      esac
      # An empty source is a ref deletion - nothing is being sent.
      [ -n "$local_ref" ] || continue
      tips+=("$local_ref")
    done
  fi
  if [ "${#tips[@]}" -eq 0 ]; then
    return 0
  fi

  local -a excludes=()
  local line
  while IFS= read -r line; do
    excludes+=("$line")
  done < <(push_exclusions)

  local bad
  bad=$(real_git log "${tips[@]}" "${excludes[@]}" \
        --format='%H|%an|%ae|%cn|%ce' 2>/dev/null | \
        awk -F'|' -v n="$REQUIRED_NAME" -v e="$REQUIRED_EMAIL" \
          '($4=="GitHub" && $5=="noreply@github.com") { if ($3!=e) print; next }
           $2!=n || $3!=e || $4!=n || $5!=e {print}')
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
