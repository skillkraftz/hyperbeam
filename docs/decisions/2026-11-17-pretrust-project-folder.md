---
id: 2026-11-17-pretrust-project-folder
status: implemented
topic: work-loop
prs: [74]
---

# Pre-trust a managed project's folder in Claude's config

## Decision
`trust_folder(path)` (hb/session.py) sets `projects["<abs path>"].hasTrustDialogAccepted = true` in `$CLAUDE_CONFIG_DIR/.claude.json` (default `~/.claude.json`) before a Claude starts in a hyperbeam-managed folder: in `hyperbeam new`, `start_session` and `work`. It changes only that key, only when it is not already true, writes via a private (0600) temp file + rename keeping the file mode (a symlinked config is written through to its target), and skips quietly if the file is missing or unreadable.

## Why
A brand-new project's first worker stopped at "Do you trust the files in this folder?" and `wait` could not ride through it. Workers and sessions use the same Claude config (hyperbeam sets no config dir), so one file covers both.

## Rejected
- A flag to skip the dialog: none exists for trust alone, and `--dangerously-skip-permissions` does not cover it.
- Pre-trusting arbitrary paths: only folders hyperbeam manages.
