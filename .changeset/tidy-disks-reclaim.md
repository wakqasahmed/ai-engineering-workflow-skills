---
"ai-engineering-workflow-skills": minor
---

Add the `vps-cleanup` skill: reclaim disk on a shared dev/staging VPS in tiers without breaking concurrent agent sessions.

It surveys read-only first (`docker buildx du` over `docker system df` for build cache, background `du`, live-process checks on every candidate cache), clears regenerable caches, then asks the user once, batched, before deleting `/tmp` worktrees and caches or unused Docker images. Worktrees qualify only when clean, pushed, and untouched for 7+ days; images are removed by ID without `-f` and one rollback tag per app is kept. Volumes, running containers, unpushed work, and sudo-only logs are report-only.
