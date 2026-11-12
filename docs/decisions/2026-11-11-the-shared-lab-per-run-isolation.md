---
id: 2026-11-11-the-shared-lab-per-run-isolation
status: implemented
prs: [21]
topic: lab
---
# The shared lab: per-run isolation; merge safety

- **Decision:** every `lab run` is its own session with an id, recorded in `/srv/hblab/runs/` and tagged with `HB_RUN_ID` in the environment of everything it starts; `lab stop` stops only a project's own runs; `lab reset` refuses while other projects have runs and its `--force` is for the user only; the guard blocks agents from `lab reset` and from `git worktree remove --force` / deleting a worktree with uncommitted work. Each run gets its own tmux and runtime dirs. Merge checks how far the PR is behind main: if behind, the modal offers "Ask Claude to update and re-test" (default) or "Merge anyway"; PRs older than 7 days are marked stale.
- **Why:** a `lab reset` killed another project's e2e suite running in the same lab, and the other agent lost time chasing "random" SIGKILLs. A worktree with uncommitted work was force-removed once. A PR that passed its tests against an older main can break main when merged.
- **Rejected:** one lab per project (disk and caches would be duplicated); finding processes only by process group (daemonised children leave the group; the environment tag follows them); cgroups or a network namespace (need root); blocking merges of PRs that are behind (the user decides).
