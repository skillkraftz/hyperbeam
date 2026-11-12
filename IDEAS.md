# Ideas

One line each. A PR that finishes an item moves it to Done (PR number, decision id); new ideas go to Open.

## Open
- **Whole-package audit (ready to start: `hyperbeam audit`, prompt AUDIT.md, decision audit-process):** hyperbeam's aim is ideas in, good code out, saving tokens without poor code; reviews, decision records and superseding exist because code grows faster than it is cleaned up. The process: (1) a read-only pass lists findings (area, where, why, kind, size, dependencies, recommendation, plus "looked at and fine"); (2) the user triages each: fix now, defer to IDEAS with a reason, or accept with the reason written down; (3) a docs-only PR records the findings and triage in `docs/audits/<date>.md`; (4) the fixes go in small PRs ordered by dependency, each with tests, a decision record that supersedes what it replaces, and the docs it touches; (5) closing: every finding fixed, deferred or accepted, a review record so counting restarts clean, and "Audit done." It covers `hyperbeam`, `guard.py`, `hyperbeam.conf`, `lab/`, `tools/`, the prompts and the docs. Seeds, checked in the code (the audit also checks the `[check]` items of docs/DESIGN.md section 4, and that the review counter starts at 1 of 5 after a review because the review's own PR merges after its `through` commit): `guard.py` has 4 layers of `RULES = RULES + [...]` and 5 ways of parsing a command (`tmux_calls` regex, `split_commands`, per-line `shlex.split` in two rules, the segment regexes of the kill rule); kill commands are checked in 3 places (`tmux_kill`, `kill_tmux_or_kitty`, `kill_outside_lab`); `ask`/`ask_tty`/`choose`/`choose_tty` and the `Confirm`/`Choice` modals overlap; the script is 6.6k lines with 446 functions; README, CLAUDE.md, docs/REFERENCE.md (long lines per topic), docs/SYSTEM.md and docs/DESIGN.md describe the same things. The first finding was already fixed (lab nesting was checked in the guard and in the lab, PR #53).
- Phone round: linked session, copy delivery, Tailscale rename. The user's notes: SSH from the phone attaches to the same busy sessions as the laptop, where many windows and panes are hard to use on a small screen. Needed: a phone view that makes a session usable there, e.g. one pane at a time, a list of panes to jump to. Unsolved; after the laptop is solid, near the polish phase.
- stenographr: paused in its own repo. The integration contract is `HB_CLAUDE_PANE` (the tmux pane id of a session's Claude pane). Later, a Dictate toggle.
- Polish phase.
- Prompt files as skills, exportable to claude.ai.
- Sidebar redesign, next round (docs/UI.md, "Redesign directions that remain"): one status area, a half-height Project panel, the phone at keyboard height; on resize the sidebar keeps a fixed `menu_width` in columns (PR #45), the user has not said whether proportional is wanted.
- Compact local context, next step (the CLAUDE.md trim is done, PR #27): trim the other projects' CLAUDE.md the same way (dotwork 13 KB); generated per-project `.hyperbeam/MAP.md` (file map, recent changes, open PR) so a session reads one file.
- Merge-time docs gate (stale docs: ask Claude to update / merge anyway), "Mark docs reviewed" snooze for the stale-docs note, a Promote prompt that rewrites a settled prototype's README for an end user.
- Docker in the lab: works for single containers and host-network compose (docs/PODMAN.md); compose's own networks need `sudo loginctl enable-linger hblab` (untested) when a project needs them.
- **Work loop, step 2:** step 1 is built (PR #52: the start choice with a fresh plan session, the same choice after a Merge). Left: ask at the hyperbeam session's start too (the sidebar has no UI when it is created); the end of the day (system up to date, project presentable, else that is the last work of the day).
- A "presentable" check at the end of the loop (README matches behaviour, screenshots current, no stale items) and how it feeds the day's close.
- When a Claude session starts and ends beyond token cost: tie it to the work loop instead of conversation size.
- README and screenshots rebuilt from the implemented decisions and the Done list (the condensing tool the decision records are meant for).
- Exporting the parts: the machine keeps every record; a reference-carrying summary is what Claude reads when it needs context.
- Swap a fresh plan-mode Claude (with a snapshot and Previous Claude) for the other propose-then-wait steps too (Onboard, Fix, wrap-up, tools): today they inject `/plan` into the running Claude, which keeps its history but depends on the session being idle.

## Done
- ~~Lab refuses nesting itself, the guard stops guessing; `hyperbeam shot --dir`~~ Done (PR #53, decision lab-refuses-nesting, which collapses lab-setup-is-the-users).
- ~~Work loop step 1: a fresh plan session (START.md) / review / continue when Claude starts, and after a finished Merge run~~ Done (PR #52, decision work-loop-start-and-end).
- ~~Every project in the review loop (count from onboarding), a Review button in the Project screen~~ Done (PR #51, decision review-every-project).
- ~~Review loop: Copy report, a PR badge, a Merge button.~~ Done (PR #20).
- ~~Project screen and drift detection.~~ Done (PR #22), kept simple: the polish phase will redesign the sidebar.
- ~~README-staleness check.~~ Done (PR #24): commands, paths and age against the run setup. Later: version numbers and ports mentioned in the docs.
- ~~Wrap-up notes into .hyperbeam/notes.~~ Done (PR #24).
- ~~Daily lab digest -> tool proposals at Done; TOOLS.md; flaky tests.~~ Done (PR #23). Later: tools the digest suggests for non-lab work, a weekly view.
- ~~Usage window~~ Done (PR #28, exact numbers in PR #30): the 5-hour and weekly limits as claude.ai shows them, a note for huge conversations. Later: ask Claude to write a short hand-off when a conversation is huge, so the fresh one starts with it.
- ~~`hyperbeam new`~~ Done (PR #30: `--cli`, `--web`). Next for verbs: `hyperbeam NAME version` in the sidebar title, `status` and `logs` verbs, per-project `[commands]` suggested by Align, a `new` verb that scaffolds a project with the verbs already in place.
- ~~Plan mode for every prompt hyperbeam injects (Opus plans, Sonnet builds)~~ Done (PR #31, decision injected-prompts-start-in-plan-mode); the review now swaps in a fresh plan-mode Claude (PR #43, decision review-fresh-claude).
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
- ~~Review pass after N merged PRs, review records~~ Done (PRs #42, #43, #44; decisions review-pass, review-fresh-claude).
