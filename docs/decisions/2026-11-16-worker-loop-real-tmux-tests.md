---
id: 2026-11-16-worker-loop-real-tmux-tests
status: implemented
topic: work-loop
prs: []
---

# The worker loop is tested on a real tmux, and a worker's hooks act only for its own Claude

## Decision
`HB_TMUX_SOCKET` makes `tmux()` use `tmux -L <name>` (tests only; unset for the user). `tests/test_worker_loop.py` runs work, wait, send, wait, close and a session ending during `wait` on an isolated tmux server with a fake `claude` that runs the real hook commands and takes the bracketed paste in raw mode. A worker's first UserPromptSubmit records the Claude's `session_id` in `$HB_STATE/session_id` (`_worker-prompt`); at Stop a worker's hook runs `_worker-report` first, which ignores a Stop whose session_id differs, and only then writes the state `finished` and the report.

## Why
The tests mocked tmux, so the paste, the hooks and `wait` seeing a session end were never exercised. A worker that ran a nested `claude -p` passed HB_WORKER/HB_STATE/HB_REPORTS on to it, and the nested Stop wrote the worker's report and marked it finished while it still worked.

## Rejected
- Clearing the HB_* variables for children in `claude_base`: only the worker's own command line goes through it, not the nested `claude` the worker's Bash tool starts.
