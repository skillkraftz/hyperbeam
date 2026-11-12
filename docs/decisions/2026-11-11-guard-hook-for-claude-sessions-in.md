---
id: 2026-11-11-guard-hook-for-claude-sessions-in
status: implemented
prs: [12]
topic: hooks
---
# Guard hook for Claude sessions in hyperbeam

- **Decision:** a PreToolUse hook (`guard.py`, exit 2 + message) blocks tmux kill commands, kills of tmux/kitty, and GUI apps with a display set. Textual and deliberately simple.
- **Why:** CLAUDE.md text did not stop a `tmux kill-server` from a Claude session that took down every session (agents inside hyperbeam have `$TMUX`).
- **Rejected:** relying on instructions only; a sandboxed tmux for agents.
