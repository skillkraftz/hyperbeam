# Ideas

One line each. A PR that finishes an item moves it to Done (PR number, decision id); new ideas go to Open.

## Open
- Phone round: linked session, copy delivery, Tailscale rename. The user's notes: SSH from the phone attaches to the same busy sessions as the laptop, where many windows and panes are hard to use on a small screen. Needed: a phone view that makes a session usable there, e.g. one pane at a time, a list of panes to jump to. Unsolved; after the laptop is solid, near the polish phase.
- stenographr: paused in its own repo. The integration contract is `HB_CLAUDE_PANE` (the tmux pane id of a session's Claude pane). Later, a Dictate toggle.
- Polish phase.
- Prompt files as skills, exportable to claude.ai.
- Sidebar redesign, next round (docs/UI.md, "Redesign directions that remain"): one status area, a half-height Project panel, the phone at keyboard height; on resize the sidebar keeps a fixed `menu_width` in columns (PR #45), the user has not said whether proportional is wanted.
- Compact local context, next step (the CLAUDE.md trim is done, PR #27): trim the other projects' CLAUDE.md the same way (dotwork 13 KB); generated per-project `.hyperbeam/MAP.md` (file map, recent changes, open PR) so a session reads one file.
- Merge-time docs gate (stale docs: ask Claude to update / merge anyway), "Mark docs reviewed" snooze for the stale-docs note, a Promote prompt that rewrites a settled prototype's README for an end user.
- Docker in the lab: works for single containers and host-network compose (docs/PODMAN.md); compose's own networks need `sudo loginctl enable-linger hblab` (untested) when a project needs them.
- Exporting the parts: the machine keeps every record; a reference-carrying summary is what Claude reads when it needs context.

## Done
- ~~Work loop step 1 (START.md), the review loop (counter, Review button, review pass, review records), the offers at Merge and Done~~ Cut (decisions cut-review-start-choice, cut-merge-and-done-extras): the manager plans and sends reviews as worker tasks.
- ~~Daily lab digest offering tool proposals at Done~~ Cut (decision cut-merge-and-done-extras); the digest itself stays (`hyperbeam lab digest`).
- ~~Plan mode for every prompt hyperbeam injects~~ Cut (decision sonnet-default-and-manager-workers): workers never use plan mode, planning is the manager's.
- ~~No automatic prompts: a failed service is a red dot and a note; no popup, no RECOVER.md, no Onboard/Fix buttons~~ Done (decision no-automatic-prompts).
- ~~Cut the review counter, the start choice, Previous Claude, `hyperbeam review|audit|back`~~ Done (decision cut-review-start-choice): the manager asks for reviews and audits as worker tasks.
- ~~Cut what follows a Merge (Fresh/Review/Keep) and Done's digest, review and wrap-up offers~~ Done (decision cut-merge-and-done-extras): the manager does that job.
- ~~Sonnet as the default model; manager workers (`work`, `wait`, `close`, reports)~~ Done (PR #57, decision sonnet-default-and-manager-workers).
- ~~Lab refuses nesting itself, the guard stops guessing; `hyperbeam shot --dir`~~ Done (PR #53, decision lab-refuses-nesting, which collapses lab-setup-is-the-users).
- ~~Project screen and drift detection.~~ Done (PR #22), kept simple: the polish phase will redesign the sidebar.
- ~~README-staleness check.~~ Done (PR #24): commands, paths and age against the run setup. Later: version numbers and ports mentioned in the docs.
- ~~Wrap-up notes into .hyperbeam/notes.~~ Done (PR #24).
- ~~Usage window~~ Done (PR #28, exact numbers in PR #30): the 5-hour and weekly limits as claude.ai shows them, a note for huge conversations. Later: ask Claude to write a short hand-off when a conversation is huge, so the fresh one starts with it.
- ~~`hyperbeam new`~~ Done (PR #30: `--cli`, `--web`). Next for verbs: `hyperbeam NAME version` in the sidebar title, `status` and `logs` verbs, per-project `[commands]` suggested by Align, a `new` verb that scaffolds a project with the verbs already in place.
- ~~Merge: oldest first, one click, stops only at a real problem~~ Done (PRs #32, #36, #38, #44; decision merge-flow): files-in-common check, conflicts handed to Claude to rebase, the installed copy always updates, the working branch is never switched.
- ~~Tests run in parallel by default; Align times the suite~~ Done (PR #34, decision tests-run-in-parallel-by-default).
- ~~Tools in Go, a daily tool check, `test-timing`~~ Done (PR #35, decision tools-go-for-real-work-a).
- ~~Claude without permission prompts by default~~ Done (PR #37, decision claude-runs-without-permission-prompts-by).
- ~~PR list refreshed at once after gh pr create/merge/close~~ Done (PR #39, decision hyperbeam-refresh-prs-an-agent-tells); hook installs no longer duplicate.
- ~~hyperbeam installed at ~/.local/lib/hyperbeam, developed in ~/projects/hyperbeam~~ Done (PR #40, decision hyperbeam-is-installed-local-lib-hyperbeam).
- ~~Decisions as one file each with a status and what they collapsed into; generated index; `decisions` tool~~ Done (PR #41, decision decision-records).
- ~~Sidebar core: Stop returns the right side to the hyperbeam session, hyperbeam row always first, width kept on resize, closed right split reopens~~ Done (PR #45, decision manager-session-is-home).
- ~~Lab nesting and setup guard: no lab inside the lab, setup scripts and sudo are the user's, error messages state facts~~ Done (PR #46, decision lab-setup-is-the-users).
- ~~Lab digest ranks by total time (count x duration) so frequent work bubbles up~~ Done (PR #47, decision digest-ranks-by-total-time).
- ~~README with recordings of the loop~~ Done (task 9 of the 2026-11-15 audit): README rewritten for the manager/worker flow; `tools/demo` regenerates `docs/img/` (loop.gif and PNGs, fake projects and fake claude, in the lab, drawn with pyte and Pillow instead of asciinema/agg).
- ~~Docs match the code (audit 2026-11-16, tasks 1, 8, 9)~~ Done: worker, Merge and IDEAS wording corrected; README lists the commands that matter and the project loop.
- ~~Search over everything said and done with Claude~~ Done (PR pending, decision 2026-11-18-recall-search-tool): `hyperbeam tool recall search|show|index|stats`.
