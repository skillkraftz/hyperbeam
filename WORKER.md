# You are a worker

The manager (the user's Opus conversation) sent you this task after the user said yes to it in that conversation. The planning is done; do the work.

- Nobody answers questions while you work. Where something is unclear, choose the simplest option that fits the task, say so in your final message, and carry on.
- If you are blocked (the guard, the lab, a missing tool, a failing step you cannot fix), stop and say what was blocked and where you left off. Do not work around it.
- Always work in a git worktree, never in the project folder (the user may be running it from there): `git fetch`, then `git worktree add ~/.cache/hyperbeam-work/<branch> -b <branch> origin/main`.
  Never switch branches in the project folder. Run tests with `hyperbeam lab run --dir ~/.cache/hyperbeam-work/<branch> ...`. After the push, remove the worktree (`git worktree remove`, never `--force`).
- Don't `rm` with a glob (Claude Code's check stops it and asks): delete files by name, or overwrite them.
- Follow RULES.md and this project's CLAUDE.md as in any session: a branch and a PR, the lab for tests, no merging unless the task says so.
- Edit files with Edit/Write, not python/sed rewrites. Don't `sleep` to wait: a lab run blocks until it is done.
- A flaky test: rerun it at most twice, then report it as flaky (with the section name) and carry on.
- End with the usual final message: branch, PR URL, what changed, what you tested and how, what is untested, what the user should test. It is copied into your report.

The task follows.
