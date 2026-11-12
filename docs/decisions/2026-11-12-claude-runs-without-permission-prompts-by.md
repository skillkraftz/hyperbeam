---
id: 2026-11-12-claude-runs-without-permission-prompts-by
status: implemented
prs: [37]
topic: unsorted
---
# Claude runs without permission prompts by default (setting `claude_permissions`)

- **Decision:** `claude_base()` adds `--dangerously-skip-permissions` (setting `claude_permissions = "skip"`, `"ask"` turns it off). A Claude started with an injected prompt gets `--permission-mode plan --allow-dangerously-skip-permissions` instead: plan mode first, bypass available once the plan is approved.
- **Why:** hyperbeam never passed a permission flag; the user had been starting Claude with the bypass flag by hand, so sessions asked questions (edits outside the project folder, unlisted commands) while he was away. The lab covers running things, not Claude's file edits. The guard hook still runs in bypass mode and blocks the dangerous commands.
- **Rejected:** per-directory allow rules for `~/.cache/hyperbeam-work` and each project (many rules to keep in sync, still prompts for new commands); `--dangerously-skip-permissions` together with `--permission-mode plan` (which wins is unclear).
