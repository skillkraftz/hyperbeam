---
id: 2026-11-16-tidy-merged-branches
status: implemented
topic: work-loop
prs: []
---

# `hyperbeam tidy`: merged branches and worktrees

## Decision
`hyperbeam tidy [NAME]` lists per project the local and origin branches merged into origin/main and the clean worktrees under ~/.cache/hyperbeam-work whose branch is merged (plus empty dirs there when no NAME is given); `--yes` deletes them with `git branch -d`, `git push origin --delete`, `git worktree remove` (no --force) and `git worktree prune`. It skips and names dirty worktrees, unmerged, checked-out and other-worktree branches. `hyperbeam close NAME` runs the worktree part quietly.

## Why
Workers leave merged branches and worktrees behind (26 local, 67 remote branches in hyperbeam).

## Rejected
Deleting by default (a list first is safer); detecting squash merges (such branches stay and are listed as not merged).
