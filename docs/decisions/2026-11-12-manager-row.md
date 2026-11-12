---
id: 2026-11-12-manager-row
status: implemented
prs: [56]
topic: ui
supersedes: [2026-11-12-manager-session-is-home]
---
# The manager: the first row is a conversation with Opus about every project; hyperbeam the project is an ordinary row

- **Decision:** the sidebar's first row is `manager`, the menu session (`MENU = "manager"`). Its Claude runs in `~/manager` with the `manager_model` setting (default `opus`), **not** in plan mode and not skipping permissions, with `--add-dir ~/projects` so it can read every project. `~/manager` is a local git repo made once from the template in `manager/` (`ensure_manager_dir`, never overwrites): a CLAUDE.md that sets the role (a colleague to talk with, no plans unless asked, no changes to projects, a prompt in `outbox/<project>.md` for work that belongs to a project), `now.md`, `projects/<name>.md`, `hyperbeam.md`, `inbox/` for claude.ai exports; its settings deny Edit/Write under `~/projects` and the installed copy. "Wrap up" updates and commits the notes, then `/clear`: the next conversation starts from them. The manager is not a project: no injected prompts, no start choice, no review; prompts about hyperbeam (tool proposals, wrap-up from Done) go to the hyperbeam project's own session (`DEV`). Kept from the decision this replaces: the first row, a fresh list highlighting the row the right side shows, Stop returning the right side to the manager (`manager:home`), `menu_width` re-applied on resize, `detach-on-destroy off` on project sessions.
- **Why:** the first row was a Claude in the hyperbeam project's folder on opusplan, so "talk about the work" turned into planning code for hyperbeam, and plan mode kept pushing plans instead of having a conversation. hyperbeam the tool and hyperbeam the project shared one row and one session. The knowledge that lives in claude.ai chats had no place here, and long chats cost 12-20% of the tokens per message.
- **Rejected:** making the existing hyperbeam row converse (it is a project, with its own CLAUDE.md and rules); another model setting only (plan mode is the problem, not the model); letting the manager edit projects (work goes out as a prompt so each project's Claude keeps its own context); a Send-to-project button now (paste is enough to start; add it if it proves needed).
