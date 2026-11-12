---
id: 2026-11-09-phone-width-menu-status-dots-claude
status: implemented
prs: [10]
topic: unsorted
---
# Phone-width menu, status dots, Claude hooks

- **Decision:** one list (dot, name, port), no tabs, works at 45 columns. Blue/cyan dots come from Claude Code command hooks (Stop, Notification, AskUserQuestion/ExitPlanMode, UserPromptSubmit, PostToolUse) writing a state file; the state is ignored unless a `claude` process runs in the pane. Hooks are merged into `~/.claude/settings.json`, never overwritten.
- **Why:** the tabbed menu did not fit a phone, and the user needs to see which Claude is waiting.
- **Rejected:** parsing pane output to guess Claude's state.
