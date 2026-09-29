---
name: vps-cleanup
description: Reclaim disk on a shared dev/staging VPS or server in approval-gated tiers without breaking concurrent agent sessions. Use when disk usage is high or full, on "No space left on device", when asked to clean up the disk, or before a large build on a nearly full box.
---

# VPS Cleanup

On a box where several agent sessions run at once, "stale-looking" is not "unused": a `/tmp`
worktree can back someone's open PR, a `<none>` image can back a running container, a cache dir
can be held open by a live process. Work in tiers: survey read-only, clear regenerable caches,
then ask the user **once, batched** before each approval tier. Anything uncertain goes on the
**keep list** with its reason.

## 0. Survey (read-only, delete nothing)

1. Baseline: `df -h /`, `docker system df`, `docker buildx du`. Trust `buildx du` for build
   cache: `docker system df` can report most of it as non-reclaimable (shared vs private
   records) while `buildx du` shows all of it reclaimable.
2. Size directories in the background: `du` across large file counts (`node_modules`, pnpm
   stores) runs for minutes and hits tool timeouts in the foreground.

   ```bash
   nice du -xh --max-depth=2 /tmp "$HOME" /opt /srv 2>/dev/null | sort -rh | head -80 > /tmp/du-survey.txt
   ```

   Root-only dirs (`/var/lib/docker`) are unreadable; size them with `docker system df`.
3. List containers and images: `docker ps -a --size`, `docker images`.
4. Find live users of every candidate cache path before touching it:

   ```bash
   pgrep -af 'npm|npx|pnpm|yarn|bun|pip|uv|playwright|puppeteer|go '
   for p in /proc/[0-9]*; do
     ls -l "$p/cwd" "$p/fd" 2>/dev/null | grep -F "<candidate-path>" && echo "in use by ${p#/proc/}"
   done
   ```

   A path in use is skipped and goes on the keep list. Example: `~/.npm/_npx` and
   `~/.cache/ms-playwright` held open by running playwright-mcp servers.

Done when: `df` baseline recorded, candidate list sized, every candidate cache checked for live
processes.

## Tier 1: regenerable caches (no approval needed)

The only cost is re-downloading or rebuilding. Skip anything the survey found in use.

- `docker builder prune -af`: usually the single largest win.
- `pnpm store prune`: removes only packages no registered project references. Repeat with
  `pnpm store prune --store-dir <dir>` for each extra store.
- `pip cache purge`, `uv cache clean`, `yarn cache clean`, `npm cache clean --force` (leaves
  `_npx` alone).
- Tool caches under `~/.cache` (`puppeteer`, `go-build`, and similar), except ones in use.

Done when: `df -h /` re-run and the tier's reclaim recorded.

## Tier 2: `/tmp` caches and worktrees (ask the user once, batched)

Build the full candidate list first, then ask one question listing every path with its size.
Delete only what the user approves. If a permission classifier or the user denies a deletion,
stop there: that path goes on the keep list.

Candidates:

- Per-issue cache dirs in `/tmp`: `*-npm-cache`, `*-uv-cache`, `*-bun-cache`, `*-m2`, XDG caches.
- Issue worktrees such as `/tmp/<repo>-issue-<n>`, only when **all** of these hold:

  ```bash
  d=/tmp/<repo>-issue-<n>
  [ "$(git -C "$d" rev-parse --show-toplevel)" = "$d" ]                        # git top-level
  [ -z "$(find "$d" -maxdepth 2 -path '*/.git' -prune -o -mtime -7 -print)" ] # untouched 7+ days
  [ -z "$(git -C "$d" status --porcelain)" ]                                  # clean
  [ -n "$(git -C "$d" branch -r --contains HEAD)" ]                           # HEAD is on a remote
  ```

  Anything failing a check goes on the keep list as *recent*, *dirty*, or *not pushed*. Large
  recent trees are usually active work in another concurrent session.

Deletion rules:

- Delete specific children only, never a shared parent dir (for example `/tmp/<shared-work-dir>`).
- Exclude live-process sockets (`/tmp/tmux-*`, `/tmp/ssh-*`, `/tmp/.X11-unix`, `/tmp/.ICE-unix`);
  see `tmux-orphaned-socket`.
- Go module caches are read-only: `chmod -R u+w <dir>` before `rm -rf <dir>`.
- Root-owned files from Docker runs without `--user`, for an already-approved path only:
  `docker run --rm -v /tmp:/host_tmp ubuntu rm -rf /host_tmp/<path>`. This clears approved
  paths; it never routes around a denial.
- After deleting a linked worktree, run `git worktree prune` in its parent clone.

Done when: approved paths deleted, worktrees pruned, `df -h /` re-run and reclaim recorded.

## Tier 3: Docker images (ask the user once, batched)

1. Find unused images: those whose ID no container (running or stopped) references.

   ```bash
   docker ps -aq | xargs -r docker inspect --format '{{.Image}}' | sort -u > /tmp/used-images.txt
   docker images -q --no-trunc | sort -u | comm -23 - /tmp/used-images.txt
   ```

2. Keep one previous tag per deployed app (`<app>:<prev-tag>`) for rollback.
3. Present the list with repo, tag, and size in one question.
4. Remove approved images by ID with plain `docker rmi <id>`, never `-f`, so Docker refuses
   anything still in use. A dangling `<none>` image can back a running container even when
   `docker system df -v` shows 0 containers for it.
5. `SIZE` double-counts shared layers: measure the reclaim with `df -h /` before and after,
   not by summing sizes.

Done when: approved images removed and reclaim measured by `df`.

## Report only (never delete)

- Docker volumes, including ones with 0 links: the user runs any volume deletion themselves
  (see `docker-volume-guardrails`).
- Running containers.
- Anything with uncommitted or unpushed git work.
- Root-owned system logs needing sudo (`/var/log/btmp`, the systemd journal): report sizes.

## Report

- `df -h /` before and after.
- Reclaim per tier.
- Keep list: every skipped path with its reason (in use, recent, dirty, not pushed, denied,
  rollback tag).
- Leftovers needing the user: volumes, sudo-only logs, denied paths, with sizes.
