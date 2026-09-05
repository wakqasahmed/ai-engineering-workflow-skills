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
        ((index += 1))
        break
        ;;
    esac
  done

  [ -n "${subcommand:-}" ] || return 1

  case "$subcommand" in
    reset)
      for argument in "${words[@]:$index}"; do
        [ "$argument" = --hard ] && return 0
      done
      ;;
    clean)
      for argument in "${words[@]:$index}"; do
        { [ "$argument" = -f ] || [ "$argument" = -fd ]; } && return 0
      done
      ;;
    branch)
      for argument in "${words[@]:$index}"; do
        [ "$argument" = -D ] && return 0
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
      for argument in "${words[@]:$index}"; do
        case "$argument" in
          -f|--force|--force-with-lease|--force-with-lease=*)
            return 0
            ;;
        esac
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
}

append_word() {
  if [ "$WORD_STARTED" -eq 1 ]; then
    SEGMENT_WORDS+=("$WORD")
    WORD=
    WORD_STARTED=0
  fi
}

# Parse shell words without eval so command substitutions in hook input never
# execute. Separators split compound commands; quoted separators remain data.
SEGMENT_WORDS=()
WORD=
WORD_STARTED=0
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
      elif [ "$CHARACTER" = '\\' ] && [ "$((INDEX + 1))" -lt "${#COMMAND}" ]; then
        ((INDEX += 1))
        WORD+="${COMMAND:$INDEX:1}"
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
        '\\')
          WORD_STARTED=1
          if [ "$((INDEX + 1))" -lt "${#COMMAND}" ]; then
            ((INDEX += 1))
            WORD+="${COMMAND:$INDEX:1}"
          fi
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
