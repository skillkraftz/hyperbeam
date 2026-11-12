---
id: 2026-11-11-the-repo-is-the-memory-copy
status: implemented
prs: [18]
topic: claude
---
# The repo is the memory; Copy context; opusplan

- **Decision:** each project's CLAUDE.md describes how it works now and `docs/DECISIONS.md` records design decisions; both change in the same PR as the code. `hyperbeam context` (and the Copy context button) puts RULES.md, CLAUDE.md, DECISIONS.md, README, manifest and recent history on the clipboard for a web chat. The default Claude model is `opusplan` (Opus plans, Sonnet implements, one session). A worktree's `hyperbeam` script may only be started through `hyperbeam lab run`.
- **Why:** decisions lived in chat histories, so every new chat started blind. One session per project avoids re-explaining between a planning chat and an implementation chat. Running a worktree script as the user migrated the live state folder (PR #17).
- **Rejected:** an MCP server (more to run; skills come later); separate planning and implementation sessions.
