#!/bin/bash
#
# PreToolUse hook (Bash matcher): blocks a fixed list of destructive/hard-to-reverse
# git commands before Claude Code executes them.
#
# Source: mattpocock/skills — misc/git-guardrails-claude-code
# https://github.com/mattpocock/skills/blob/main/skills/misc/git-guardrails-claude-code/SKILL.md
# Adapted 2026-08-26: upstream blocks ALL `git push`; this version narrows that to
# force-push and direct pushes to protected branches only, per this repo's own
# git-workflow rules (system-level/core.md), which forbid force-push and direct
# commits/pushes to main/staging but require routine feature-branch pushes for
# the standard PR workflow (worktree -> branch -> push -> PR).
# Hardened 2026-08-26 per Open Code Review on PR #103: printf instead of echo
# (a COMMAND starting with a dash could be misread as an echo option).
# Hardened 2026-09-05 per Open Code Review: the parser cannot safely evaluate
# command/process substitution (`$(...)`, backticks, `<(...)`, `>(...)`) since
# doing so would mean executing arbitrary input. Words built from a live
# substitution are tracked as "tainted" (see WORD_TAINTED/SEGMENT_TAINTED
# below) and, wherever a tainted word lands in the git subcommand position or
# in one of the dangerous-flag/branch-destination scans, the command is
# fail-closed (treated as dangerous) rather than allowed through
# unrecognized. This closes `git $(echo reset) --hard`-style bypasses of the
# subcommand and dangerous-flag checks. A computed value assigned to a
# variable in an earlier command (`BRANCH="release/$(date +%Y)"; git push
# origin "$BRANCH"`) is unaffected — only a substitution written inline in
# the git invocation itself is tainted. Known, accepted residual limitation:
# a bare (non-substitution) variable expansion choosing the subcommand or a
# flag (`git $BRANCH_OP --hard`) cannot be resolved without executing the
# command, and is not tracked as tainted — this is the same limitation Open
# Code Review noted for command substitution in general.

INPUT=$(cat)
COMMAND=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty')

[ -z "$COMMAND" ] && exit 0

PROTECTED_BRANCHES=(main master staging)

is_protected_branch() {
  local argument="$1"
  local branch

  for branch in "${PROTECTED_BRANCHES[@]}"; do
    if [ "$argument" = "$branch" ] || [ "$argument" = "HEAD:$branch" ]; then
      return 0
    fi
  done

  return 1
}

is_dangerous_git_command() {
  local -a words=("$@")
  local index=0
  local i
  local executable
  local subcommand
  local argument

  while [ "$index" -lt "${#words[@]}" ]; do
    while [ "$index" -lt "${#words[@]}" ] && [[ "${words[$index]}" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; do
      ((index += 1))
    done

    [ "$index" -lt "${#words[@]}" ] || return 1
    executable="${words[$index]##*/}"

    case "$executable" in
      command)
        ((index += 1))
        while [ "$index" -lt "${#words[@]}" ]; do
          case "${words[$index]}" in
            -p)
              ((index += 1))
              ;;
            --)
              ((index += 1))
              break
              ;;
            -v|-V|-*)
              return 1
              ;;
            *)
              break
              ;;
          esac
        done
        ;;
      env)
        ((index += 1))
        while [ "$index" -lt "${#words[@]}" ]; do
          argument="${words[$index]}"
          if [[ "$argument" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
            ((index += 1))
            continue
          fi
          case "$argument" in
            -|-i|--ignore-environment|-v|--debug|--block-signal|--default-signal|--ignore-signal|--list-signal-handling)
              ((index += 1))
              ;;
            -u|-C|-S|-a|--unset|--chdir|--split-string|--argv0)
              ((index += 2))
              ;;
            -u?*|-C?*|-S?*|-a?*|--unset=*|--chdir=*|--split-string=*|--argv0=*|--block-signal=*|--default-signal=*|--ignore-signal=*)
              ((index += 1))
              ;;
            --)
              ((index += 1))
              break
              ;;
            -*)
              return 1
              ;;
            *)
              break
              ;;
          esac
        done
        ;;
      sudo)
        ((index += 1))
        while [ "$index" -lt "${#words[@]}" ]; do
          argument="${words[$index]}"
          if [[ "$argument" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
            ((index += 1))
            continue
          fi
          if [[ "$argument" =~ ^-[AbEHiknPSs]+$ ]]; then
            ((index += 1))
            continue
          fi
          case "$argument" in
            --askpass|--background|--bell|--login|--non-interactive|--preserve-env|--preserve-groups|--reset-timestamp|--set-home|--shell|--stdin)
              ((index += 1))
              ;;
            -a|-C|-c|-D|-g|-h|-p|-R|-r|-T|-t|-u|--auth-type|--close-from|--login-class|--chdir|--group|--host|--prompt|--chroot|--role|--command-timeout|--type|--user)
              ((index += 2))
              ;;
            -a?*|-C?*|-c?*|-D?*|-g?*|-h?*|-p?*|-R?*|-r?*|-T?*|-t?*|-u?*|--auth-type=*|--close-from=*|--login-class=*|--chdir=*|--group=*|--host=*|--prompt=*|--preserve-env=*|--chroot=*|--role=*|--command-timeout=*|--type=*|--user=*)
              ((index += 1))
              ;;
            --)
              ((index += 1))
              break
              ;;
            -*)
              return 1
              ;;
            *)
              break
              ;;
          esac
        done
        ;;
      *)
        break
        ;;
    esac
  done

  [ "$index" -lt "${#words[@]}" ] || return 1
  executable="${words[$index]##*/}"
  [ "$executable" = git ] || return 1
  ((index += 1))

  while [ "$index" -lt "${#words[@]}" ]; do
    argument="${words[$index]}"
    case "$argument" in
      -C|-c|--git-dir|--work-tree|--namespace|--config-env|--super-prefix|--attr-source)
        ((index += 2))
        ;;
      -C?*|-c?*|--git-dir=*|--work-tree=*|--namespace=*|--config-env=*|--super-prefix=*|--attr-source=*|--exec-path=*)
        ((index += 1))
        ;;
      -p|--paginate|-P|--no-pager|--bare|--no-replace-objects|--no-lazy-fetch|--literal-pathspecs|--glob-pathspecs|--noglob-pathspecs|--icase-pathspecs|--no-optional-locks|--no-advice)
        ((index += 1))
        ;;
      -v|--version|-h|--help|--exec-path|--html-path|--man-path|--info-path)
        return 1
        ;;
      --)
        return 1
        ;;
      -* )
        return 1
        ;;
      *)
        subcommand="$argument"
        # A subcommand built from a live command/process substitution (e.g.
        # `git $(echo reset) --hard`) cannot be resolved without executing
        # it. Fail closed instead of letting an unrecognized value through.
        if [ "${SEGMENT_TAINTED[$index]:-0}" -eq 1 ]; then
          return 0
        fi
        ((index += 1))
        break
        ;;
    esac
  done

  [ -n "${subcommand:-}" ] || return 1

  case "$subcommand" in
    reset)
      for ((i = index; i < ${#words[@]}; i++)); do
        if [ "${words[$i]}" = --hard ] || [ "${SEGMENT_TAINTED[$i]:-0}" -eq 1 ]; then
          return 0
        fi
      done
      ;;
    clean)
      for ((i = index; i < ${#words[@]}; i++)); do
        if [ "${words[$i]}" = -f ] || [ "${words[$i]}" = -fd ] || [ "${SEGMENT_TAINTED[$i]:-0}" -eq 1 ]; then
          return 0
        fi
      done
      ;;
    branch)
      for ((i = index; i < ${#words[@]}; i++)); do
        if [ "${words[$i]}" = -D ] || [ "${SEGMENT_TAINTED[$i]:-0}" -eq 1 ]; then
          return 0
        fi
      done
      ;;
    checkout|restore)
      if [ "${#words[@]}" -eq "$((index + 1))" ] && [ "${words[$index]}" = . ]; then
        return 0
      fi
      if [ "${#words[@]}" -eq "$((index + 2))" ] && [ "${words[$index]}" = -- ] && [ "${words[$((index + 1))]}" = . ]; then
        return 0
      fi
      ;;
    push)
      for ((i = index; i < ${#words[@]}; i++)); do
        argument="${words[$i]}"
        case "$argument" in
          -f|--force|--force-with-lease|--force-with-lease=*)
            return 0
            ;;
        esac
        if [ "${SEGMENT_TAINTED[$i]:-0}" -eq 1 ]; then
          return 0
        fi
        is_protected_branch "$argument" && return 0
      done
      ;;
  esac

  return 1
}

inspect_segment() {
  [ "${#SEGMENT_WORDS[@]}" -gt 0 ] || return

  if is_dangerous_git_command "${SEGMENT_WORDS[@]}"; then
    printf 'BLOCKED: %s contains a prohibited Git operation. Force-push, direct pushes to main/master/staging, reset --hard, clean -f/-fd, branch -D, and bare checkout/restore . are not permitted. The user has prevented you from doing this.\n' "$COMMAND" >&2
    exit 2
  fi

  SEGMENT_WORDS=()
  SEGMENT_TAINTED=()
}

append_word() {
  if [ "$WORD_STARTED" -eq 1 ]; then
    SEGMENT_WORDS+=("$WORD")
    SEGMENT_TAINTED+=("$WORD_TAINTED")
    WORD=
    WORD_STARTED=0
    WORD_TAINTED=0
  fi
}

# A single backslash character, held in a variable so every comparison below
# tests one literal backslash. Writing it as the bare pattern/string literal
# '\\' is a trap: inside single quotes bash performs no escaping at all, so
# '\\' is *two* literal backslash characters and can never equal the
# single-character $CHARACTER — silently disabling the branch. (This is
# exactly the bug Open Code Review flagged: both the plain- and
# double-quote-state backslash handling below used to compare against '\\'
# and so never fired.)
BACKSLASH=$'\\'

# Parse shell words without eval so command substitutions in hook input never
# execute. Separators split compound commands; quoted separators remain data.
# A word built from a live (unquoted or double-quoted) command/process
# substitution is marked tainted via WORD_TAINTED/SEGMENT_TAINTED — see the
# header comment and is_dangerous_git_command for how taint is used.
SEGMENT_WORDS=()
SEGMENT_TAINTED=()
WORD=
WORD_STARTED=0
WORD_TAINTED=0
STATE=plain
INDEX=0

while [ "$INDEX" -lt "${#COMMAND}" ]; do
  CHARACTER="${COMMAND:$INDEX:1}"

  case "$STATE" in
    single)
      if [ "$CHARACTER" = "'" ]; then
        STATE=plain
      else
        WORD+="$CHARACTER"
      fi
      ;;
    double)
      if [ "$CHARACTER" = '"' ]; then
        STATE=plain
      elif [ "$CHARACTER" = '`' ]; then
        WORD_STARTED=1
        WORD_TAINTED=1
        WORD+="$CHARACTER"
      elif [ "$CHARACTER" = '$' ] && [ "${COMMAND:$((INDEX + 1)):1}" = '(' ]; then
        WORD_STARTED=1
        WORD_TAINTED=1
        WORD+="$CHARACTER"
      elif [ "$CHARACTER" = "$BACKSLASH" ] && [ "$((INDEX + 1))" -lt "${#COMMAND}" ]; then
        # Inside double quotes the shell only treats backslash as an escape
        # when the next character is $, `, ", \, or newline; otherwise the
        # backslash itself is kept literally, alongside that next character.
        NEXT_CHARACTER="${COMMAND:$((INDEX + 1)):1}"
        case "$NEXT_CHARACTER" in
          '$'|'`'|'"'|"$BACKSLASH")
            ((INDEX += 1))
            WORD+="$NEXT_CHARACTER"
            ;;
          $'\n')
            ((INDEX += 1))
            ;;
          *)
            WORD+="$CHARACTER"
            ;;
        esac
      else
        WORD+="$CHARACTER"
      fi
      ;;
    plain)
      case "$CHARACTER" in
        "'")
          STATE=single
          WORD_STARTED=1
          ;;
        '"')
          STATE=double
          WORD_STARTED=1
          ;;
        "$BACKSLASH")
          if [ "$((INDEX + 1))" -lt "${#COMMAND}" ]; then
            NEXT_CHARACTER="${COMMAND:$((INDEX + 1)):1}"
            if [ "$NEXT_CHARACTER" = $'\n' ]; then
              # Backslash-newline is a line continuation: both characters
              # vanish and do not start or end a word.
              ((INDEX += 1))
            else
              WORD_STARTED=1
              WORD+="$NEXT_CHARACTER"
              ((INDEX += 1))
            fi
          else
            # Trailing backslash with nothing after it: kept as a literal
            # character rather than silently dropped.
            WORD_STARTED=1
            WORD+="$CHARACTER"
          fi
          ;;
        '`')
          WORD_STARTED=1
          WORD_TAINTED=1
          WORD+="$CHARACTER"
          ;;
        '$')
          WORD_STARTED=1
          if [ "${COMMAND:$((INDEX + 1)):1}" = '(' ]; then
            WORD_TAINTED=1
          fi
          WORD+="$CHARACTER"
          ;;
        '<'|'>')
          WORD_STARTED=1
          if [ "${COMMAND:$((INDEX + 1)):1}" = '(' ]; then
            WORD_TAINTED=1
          fi
          WORD+="$CHARACTER"
          ;;
        ' '|$'\t'|$'\r')
          append_word
          ;;
        $'\n'|'&'|'|'|';'|'('|')')
          append_word
          inspect_segment
          ;;
        *)
          WORD_STARTED=1
          WORD+="$CHARACTER"
          ;;
      esac
      ;;
  esac

  ((INDEX += 1))
done

append_word
inspect_segment

exit 0
