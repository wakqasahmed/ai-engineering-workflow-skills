#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRAPPER="$REPO_ROOT/skills/engineering/git-identity-guard/scripts/git-identity-guard.sh"
if [ ! -f "$WRAPPER" ]; then
  printf 'Error: wrapper not found: %s\n' "$WRAPPER" >&2
  exit 1
fi

# Resolve the real git explicitly: a machine that already has this guard
# installed has a wrapper copy first on $PATH, and driving the fixtures
# through it would test that copy instead of the one in this repo.
REAL_GIT=""
IFS=':' read -ra _path_dirs <<< "$PATH"
for _dir in "${_path_dirs[@]}"; do
  [ -n "$_dir" ] || continue
  if [ -x "$_dir/git" ] && [ -f "$_dir/git" ] &&
     ! head -n 40 "$_dir/git" 2>/dev/null | grep -q "GIT_IDENTITY_GUARD_MARKER_V1"; then
    REAL_GIT="$_dir/git"
    break
  fi
done
if [ -z "$REAL_GIT" ]; then
  printf 'Error: could not find a real git binary on $PATH\n' >&2
  exit 1
fi
GOOD_NAME="Good Name"
GOOD_EMAIL="good@example.com"

SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT

mkdir -p "$SANDBOX/bin"
cp "$WRAPPER" "$SANDBOX/bin/git"
chmod +x "$SANDBOX/bin/git"
cat > "$SANDBOX/config" <<EOF
REQUIRED_NAME="$GOOD_NAME"
REQUIRED_EMAIL="$GOOD_EMAIL"
EOF

export PATH="$SANDBOX/bin:$PATH"
export GIT_IDENTITY_GUARD_CONFIG="$SANDBOX/config"

failures=0

fail() {
  printf 'FAIL: %s\n%s\n' "$1" "${2:-}" >&2
  failures=$((failures + 1))
}

new_repo() {
  local dir="$SANDBOX/$1"
  rm -rf "$dir"
  "$REAL_GIT" init -q -b trunk "$dir"
  "$REAL_GIT" -C "$dir" config user.name "$GOOD_NAME"
  "$REAL_GIT" -C "$dir" config user.email "$GOOD_EMAIL"
  printf 'seed\n' > "$dir/seed.txt"
  "$REAL_GIT" -C "$dir" add seed.txt
  "$REAL_GIT" -C "$dir" commit -q -m seed
  printf '%s' "$dir"
}

stage() {
  printf '%s\n' "$RANDOM$RANDOM" > "$1/f-$2.txt"
  "$REAL_GIT" -C "$1" add "f-$2.txt"
}

assert_blocked() {
  local description="$1"
  shift
  local output status
  set +e
  output=$("$@" 2>&1)
  status=$?
  set -e
  if [ "$status" -eq 0 ]; then
    fail "$description (expected a non-zero exit, got 0)" "$output"
  fi
}

assert_allowed() {
  local description="$1"
  shift
  local output status
  set +e
  output=$("$@" 2>&1)
  status=$?
  set -e
  if [ "$status" -ne 0 ]; then
    fail "$description (expected exit 0, got $status)" "$output"
  fi
}

assert_blocked_saying() {
  local description="$1" needle="$2"
  shift 2
  local output status
  set +e
  output=$("$@" 2>&1)
  status=$?
  set -e
  if [ "$status" -eq 0 ]; then
    fail "$description (expected a non-zero exit, got 0)" "$output"
  elif ! printf '%s' "$output" | grep -q "$needle"; then
    fail "$description (output did not mention '$needle')" "$output"
  fi
}

assert_head_identity() {
  local dir="$1" description="$2" actual
  actual=$("$REAL_GIT" -C "$dir" log -1 --format='%an <%ae>|%cn <%ce>')
  if [ "$actual" != "$GOOD_NAME <$GOOD_EMAIL>|$GOOD_NAME <$GOOD_EMAIL>" ]; then
    fail "$description (HEAD identity is $actual)"
  fi
}

# --- commit-time gate -------------------------------------------------------

repo="$(new_repo commit-repo)"

stage "$repo" ok
assert_allowed "allows a commit under the required identity" \
  git -C "$repo" commit -q -m ok
assert_head_identity "$repo" "the allowed commit kept the required identity"

stage "$repo" dashc
assert_blocked "blocks -c user.email override" \
  git -C "$repo" -c user.email=evil@x.com commit -q -m nope

stage "$repo" author
assert_blocked "blocks a --author= override" \
  git -C "$repo" commit -q -m nope --author="Evil <evil@x.com>"

stage "$repo" author2
assert_blocked "blocks a separate-argument --author override" \
  git -C "$repo" commit -q -m nope --author "Evil <evil@x.com>"

assert_allowed "allows a --author that matches the required identity" \
  git -C "$repo" commit -q -m ok --author="$GOOD_NAME <$GOOD_EMAIL>"
assert_head_identity "$repo" "the matching --author commit kept the required identity"

# A correct committer env var must not launder a wrong configured author.
"$REAL_GIT" -C "$repo" config user.email bad@config.com
stage "$repo" launder
assert_blocked "blocks a wrong config author masked by a correct GIT_COMMITTER_EMAIL" \
  env GIT_COMMITTER_NAME="$GOOD_NAME" GIT_COMMITTER_EMAIL="$GOOD_EMAIL" \
  git -C "$repo" commit -q -m nope
"$REAL_GIT" -C "$repo" config user.email "$GOOD_EMAIL"

stage "$repo" authorenv
assert_blocked "blocks a wrong GIT_AUTHOR_EMAIL" \
  env GIT_AUTHOR_EMAIL=evil@x.com git -C "$repo" commit -q -m nope

assert_blocked "blocks commit-tree under a wrong env identity" \
  env GIT_AUTHOR_NAME=Evil GIT_AUTHOR_EMAIL=evil@x.com \
      GIT_COMMITTER_NAME=Evil GIT_COMMITTER_EMAIL=evil@x.com \
  git -C "$repo" commit-tree HEAD^{tree} -m nope

# --- config handling --------------------------------------------------------

stage "$repo" killswitch
assert_blocked "fails closed when GIT_IDENTITY_GUARD_CONFIG names a missing file" \
  env GIT_IDENTITY_GUARD_CONFIG="$SANDBOX/does-not-exist" \
  git -C "$repo" -c user.email=evil@x.com commit -q -m nope

stage "$repo" devnull
assert_blocked "fails closed when GIT_IDENTITY_GUARD_CONFIG points at /dev/null" \
  env GIT_IDENTITY_GUARD_CONFIG=/dev/null \
  git -C "$repo" -c user.email=evil@x.com commit -q -m nope

assert_allowed "leaves non-gated subcommands alone even with an unusable config" \
  env GIT_IDENTITY_GUARD_CONFIG=/dev/null git -C "$repo" status --short

printf 'REQUIRED_NAME="%s"\nREQUIRED_EMAIL="%s"\nid() { echo pwned > "%s/pwned"; }\nid\n' \
  "$GOOD_NAME" "$GOOD_EMAIL" "$SANDBOX" > "$SANDBOX/config-exec"
stage "$repo" noexec
assert_allowed "parses the config instead of executing it" \
  env GIT_IDENTITY_GUARD_CONFIG="$SANDBOX/config-exec" git -C "$repo" commit -q -m ok
if [ -e "$SANDBOX/pwned" ]; then
  fail "config file contents were executed"
fi

# --- argument-parsing robustness -------------------------------------------

assert_blocked "does not abort on a trailing -c with no value" \
  git -c
if git -c 2>&1 | grep -q 'unbound variable'; then
  fail "a trailing -c still triggers a set -u unbound variable error"
fi
if git -C 2>&1 | grep -q 'unbound variable'; then
  fail "a trailing -C still triggers a set -u unbound variable error"
fi

assert_allowed "tolerates an empty \$PATH entry" \
  env PATH="$SANDBOX/bin::$PATH" git -C "$repo" status --short

assert_allowed "tolerates an unset HOME" \
  env -u HOME PATH="$PATH" GIT_IDENTITY_GUARD_CONFIG="$SANDBOX/config" \
  git -C "$repo" status --short

# An unrecognized global option that looks like it took a separate value must
# not push the real subcommand out of view and make the gate fail open.
stage "$repo" failclosed
assert_blocked_saying "fails closed on an unrecognized global-option layout" 'BLOCKED' \
  git -C "$repo" -c user.email=evil@x.com --nonsense-global-option value commit -q -m nope

# --- push backstop ----------------------------------------------------------

remote="$SANDBOX/remote.git"
rm -rf "$remote"
"$REAL_GIT" init -q --bare "$remote"
repo="$(new_repo push-repo)"
"$REAL_GIT" -C "$repo" remote add origin "$remote"
assert_allowed "allows pushing clean history" \
  git -C "$repo" push -q origin trunk

tree=$("$REAL_GIT" -C "$repo" rev-parse 'HEAD^{tree}')
parent=$("$REAL_GIT" -C "$repo" rev-parse HEAD)
bad=$(GIT_AUTHOR_NAME=Evil GIT_AUTHOR_EMAIL=evil@x.com \
      GIT_COMMITTER_NAME=Evil GIT_COMMITTER_EMAIL=evil@x.com \
      "$REAL_GIT" -C "$repo" commit-tree "$tree" -p "$parent" -m forged)
"$REAL_GIT" -C "$repo" branch side "$bad"

assert_blocked "blocks pushing a non-HEAD branch carrying a forged commit" \
  git -C "$repo" push origin side:refs/heads/side
assert_blocked "blocks pushing a raw SHA carrying a forged commit" \
  git -C "$repo" push origin "$bad:refs/heads/sha"
assert_blocked "blocks a bare push while a forged commit sits on another branch" \
  git -C "$repo" push origin
"$REAL_GIT" -C "$repo" tag forged-tag "$bad"
assert_blocked "blocks pushing a tag pointing at a forged commit" \
  git -C "$repo" push origin forged-tag
assert_blocked "blocks --all when a forged commit is on any branch" \
  git -C "$repo" push --all origin

if "$REAL_GIT" --git-dir="$remote" rev-parse --verify -q side >/dev/null 2>&1 ||
   "$REAL_GIT" --git-dir="$remote" rev-parse --verify -q sha >/dev/null 2>&1 ||
   "$REAL_GIT" --git-dir="$remote" rev-parse --verify -q refs/tags/forged-tag >/dev/null 2>&1; then
  fail "a forged commit reached the remote"
fi

"$REAL_GIT" -C "$repo" tag -d forged-tag >/dev/null
"$REAL_GIT" -C "$repo" branch -D side >/dev/null
printf 'more\n' > "$repo/more.txt"
"$REAL_GIT" -C "$repo" add more.txt
"$REAL_GIT" -C "$repo" commit -q -m more
assert_allowed "still allows a clean push after the forged branch is gone" \
  git -C "$repo" push -q origin trunk

# GitHub's own web-merge identity keeps its documented exception: the author
# email still has to be ours, but the display names do not.
gh_ok=$(GIT_AUTHOR_NAME="Display Name" GIT_AUTHOR_EMAIL="$GOOD_EMAIL" \
        GIT_COMMITTER_NAME=GitHub GIT_COMMITTER_EMAIL=noreply@github.com \
        "$REAL_GIT" -C "$repo" commit-tree "$("$REAL_GIT" -C "$repo" rev-parse 'HEAD^{tree}')" \
        -p "$("$REAL_GIT" -C "$repo" rev-parse HEAD)" -m "web merge")
"$REAL_GIT" -C "$repo" branch ghmerge "$gh_ok"
assert_allowed "allows a GitHub web-merge commit with our author email" \
  git -C "$repo" push -q origin ghmerge
gh_bad=$(GIT_AUTHOR_NAME="Display Name" GIT_AUTHOR_EMAIL=evil@x.com \
         GIT_COMMITTER_NAME=GitHub GIT_COMMITTER_EMAIL=noreply@github.com \
         "$REAL_GIT" -C "$repo" commit-tree "$("$REAL_GIT" -C "$repo" rev-parse 'HEAD^{tree}')" \
         -p "$("$REAL_GIT" -C "$repo" rev-parse HEAD)" -m "web merge, wrong email")
"$REAL_GIT" -C "$repo" branch ghmergebad "$gh_bad"
assert_blocked "still blocks a GitHub web-merge commit with a foreign author email" \
  git -C "$repo" push origin ghmergebad
"$REAL_GIT" -C "$repo" branch -D ghmergebad >/dev/null

# Deleting a remote ref sends no commits and must not be gated.
"$REAL_GIT" -C "$repo" branch tmpdel >/dev/null
assert_allowed "allows pushing a throwaway branch" \
  git -C "$repo" push -q origin tmpdel
assert_allowed "allows a ref deletion" \
  git -C "$repo" push -q origin --delete tmpdel

if [ "$failures" -ne 0 ]; then
  printf '%s check(s) failed\n' "$failures" >&2
  exit 1
fi
printf 'All git-identity-guard checks passed\n'
