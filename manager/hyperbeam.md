# hyperbeam as a system

Two things share the name. **The tool**: the installed copy at `~/.local/lib/hyperbeam`, which runs every project (sidebar, tmux sessions, lab, Merge). Nobody edits it.
**The project**: `~/projects/hyperbeam`, a repo changed through Claude on branches like any other project; changes reach the tool by Merge.

## What it is for
Keep many small AI-built projects usable on one laptop: one place to open each (services, ports, Claude), tests that can't break live work (the lab),
the same verbs everywhere (install/update/test/version/help), a Merge button, and a repo-based memory instead of long chats.
It is **not** meant to be a process engine. The manager (this row) is the part that was missing: a conversation with Opus about all of it.

## What went wrong (audit of 2026-11-12, through 0ae0216; read-only, nothing fixed yet)
The workflow started work by itself and fed on itself: the last 8 PRs were mostly hyperbeam managing hyperbeam.
- The review counter reads the wrong file when two reviews share a date (`last_review`, hyperbeam ~797), and counts the review's own PR.
- After every Merge a "Fresh plan session / Review / Keep" choice appears with Fresh on Enter, which replaces the working Claude.
- A slow service starts ONBOARDING + ALIGN without asking. The red-problem popup comes back on every session switch.
- A failing tool test turns the hyperbeam row red. Done chains up to five questions (digest, reviews, wrap-up).
- Merge's "now the project's update" does nothing (the merge already pulled, so the update sees no change).
- The sidebar's Test button probably crashes (`cmd_lab` writes to `sys.stdout.buffer`, absent inside Textual).
- `~/.local/bin/kk` points at the dev folder's script, so sessions run dev code as the user.
- `guard.py`: 7 ways of parsing a command, rules in 5 places, kill checked 3 times. The lab already refuses most of what it blocks.
- Docs repeat and disagree (Docker in the lab, the guard's rules, settings, when a dot is red). INVENTORY.md and SESSION are leftovers.
- 6.6k-line script: old migrations, unused functions, 6 ways to find a project's path.

## A first draft of "what each piece is" (to argue with, not approved)
- Core: sidebar + one tmux session per project; manifests; status dots and PR badge; `kk`; the lab; standard verbs; Merge and the project update; CLAUDE.md + RULES.md.
- Keep, small: layout restore, usage line, Copy context/report, wrap-up check, Onboard/Align (only when pressed), the red-problem popup (once per problem).
- Shrink: the guard (only what hurts the live machine), decision records (one file each, without the index machinery).
- Cut: the start choice after Open/Merge, the review counter and Done offers, tool proposals and the daily tool check, Previous Claude (it only served those).
- Merge REVIEW.md and AUDIT.md into one clean-up prompt the user starts.
- Rule: a change to hyperbeam points at a piece; a new piece needs the user's approval first; hyperbeam never starts Claude work by itself.

## The problem this solves
Context lives in claude.ai chats and eats tokens. The data has to live here: per-project notes in `projects/`, kept short by rewriting and collapsing.
