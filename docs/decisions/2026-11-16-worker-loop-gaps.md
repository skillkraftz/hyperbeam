---
id: 2026-11-16-worker-loop-gaps
status: implemented
prs: []
topic: work-loop
---
# Worker loop: wait rides through prompts, send, worktree commits, project loop

- **Decision:** `wait` keeps waiting up to 3 minutes through a "needs your input or permission" state (Claude Code blocks an unanswered prompt itself after ~2 minutes and carries on); a worker's question (`AskUserQuestion`) still ends the wait at once. `PostToolUseFailure` and `PermissionDenied` (both exist in Claude Code 2.1.325) write `working`, and the Notification hook ignores `idle_prompt`, so a finished worker stays finished. `hyperbeam send NAME FILE|-` pastes feedback (bracketed paste, then Enter) only into a finished worker. The report lists commits on any branch since the worker's start time (`git log --all --since`), because workers always use a worktree (WORKER.md). The manager's role (`manager/CLAUDE.md`) has the project loop, usage thresholds and the rule never to answer a worker's permission prompt.
- **Why:** a full loop on stenographr (9 workers) hit each of these: `wait` returned exit 2 on a prompt Claude then carried on from, the state stayed stale, review feedback had no way in, worktree commits were missing from reports, and a worker switching branches broke the folder the user runs from.
- **Rejected:** answering the prompt for the worker (a "No" interrupts it); polling the tmux pane for prompt text (fragile); recording refs instead of a time (a time also covers branches created later).
