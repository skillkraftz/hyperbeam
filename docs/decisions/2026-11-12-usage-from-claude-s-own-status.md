---
id: 2026-11-12-usage-from-claude-s-own-status
status: implemented
prs: [30]
topic: unsorted
---
# Usage from Claude's own status line; `dotwork help` in the session; `hyperbeam new`

- **Decision:** the 5-hour and weekly limits come from the numbers Claude Code's status line receives (the ones claude.ai shows, web chats included), captured by a snippet hyperbeam adds to the user's status line script; times are the system's local time, 12-hour. The estimate from local files is gone as the headline: local files only give per-project tokens and conversation sizes, and a conversation that re-reads 300k+ tokens per request gets a quiet note. Inside a project's session `NAME VERB` and `hb VERB` work (shims on the session PATH, never shadowing a real command). `hyperbeam new` creates a project that already has version/help/update/install, README, CLAUDE.md, DECISIONS.md and a manifest, and RULES.md tells every project's Claude to build that in from the first commit.
- **Why:** the limit is shared with claude.ai, so any local window was wrong (3:02 am versus Thu 1:00 am; 66 requests versus 83%). The user wants to type the project's name and a verb, and prototypes that become projects never get these features added later.
- **Rejected:** estimating the percentage (it cannot see web chats); the usage endpoint behind `/usage` (undocumented); a global alias for every project name (it would shadow real commands and touches every terminal); a scaffolder with many templates (two small ones).
