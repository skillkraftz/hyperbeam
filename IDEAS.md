# Ideas

One line each. A PR that finishes an item moves it to Done (PR number, decision id); new ideas go to Open.

## Open
- Phone round: linked session, copy delivery, Tailscale rename. The user's notes: SSH from the phone attaches to the same busy sessions as the laptop, where many windows and panes are hard to use on a small screen. Needed: a phone view that makes a session usable there, e.g. one pane at a time, a list of panes to jump to. Unsolved; after the laptop is solid, near the polish phase.
- stenographr: paused in its own repo. The integration contract is `HB_CLAUDE_PANE` (the tmux pane id of a session's Claude pane). Later, a Dictate toggle.
- Polish phase.
- Prompt files as skills, exportable to claude.ai.
- Sidebar redesign, next round (docs/UI.md, "Redesign directions that remain"): one status area, a half-height Project panel, the phone at keyboard height.
- Compact local context, next step (the CLAUDE.md trim is done, PR #27): trim the other projects' CLAUDE.md the same way (dotwork 13 KB); generated per-project `.hyperbeam/MAP.md` (file map, recent changes, open PR) so a session reads one file.
- Merge-time docs gate (stale docs: ask Claude to update / merge anyway), "Mark docs reviewed" snooze for the stale-docs note, a Promote prompt that rewrites a settled prototype's README for an end user.
- Docker in the lab: works for single containers and host-network compose (docs/PODMAN.md); compose's own networks need `sudo loginctl enable-linger hblab` (untested) when a project needs them.
- **Work loop (to plan):** onboarding runs when a stopped session is started (a new Claude session, since changes are coming) and brings the project to a good state; then Claude recommends features or lists the still-relevant ideas to pick from; about 5 PRs; a review pass (refactor, README and the docs it touches); repeat until done. At the end the system is up to date and the project presentable; if not, that is the last work of the day.
- A "presentable" check at the end of the loop (README matches behaviour, screenshots current, no stale items) and how it feeds the day's close.
- When a Claude session starts and ends beyond token cost: tie it to the work loop instead of conversation size.
- README and screenshots rebuilt from the implemented decisions and the Done list (the condensing tool the decision records are meant for).
- Exporting the parts: the machine keeps every record; a reference-carrying summary is what Claude reads when it needs context.
- A Review button in the Project screen (today: `hyperbeam review`, and Done offers it after `review_after` merged PRs).

## Done
- ~~Review loop: Copy report, a PR badge, a Merge button.~~ Done (PR #20).
- ~~Project screen and drift detection.~~ Done (PR #22), kept simple: the polish phase will redesign the sidebar.
- ~~README-staleness check.~~ Done (PR #24): commands, paths and age against the run setup. Later: version numbers and ports mentioned in the docs.
- ~~Wrap-up notes into .hyperbeam/notes.~~ Done (PR #24).
- ~~Daily lab digest -> tool proposals at Done; TOOLS.md; flaky tests.~~ Done (PR #23). Later: tools the digest suggests for non-lab work, a weekly view.
- ~~Usage window~~ Done (PR #28, exact numbers in PR #30): the 5-hour and weekly limits as claude.ai shows them, a note for huge conversations. Later: ask Claude to write a short hand-off when a conversation is huge, so the fresh one starts with it.
- ~~`hyperbeam new`~~ Done (PR #30: `--cli`, `--web`). Next for verbs: `hyperbeam NAME version` in the sidebar title, `status` and `logs` verbs, per-project `[commands]` suggested by Align, a `new` verb that scaffolds a project with the verbs already in place.
