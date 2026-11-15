---
id: 2026-11-15-cut-merge-and-done-extras
status: implemented
prs: []
topic: work-loop
supersedes: [2026-11-12-work-loop-start-and-end]
---
# Merge and Done end where they end: the manager starts the next piece of work

- **Decision:** a Merge run ends at its toast and the project's update (no Fresh / Review / Keep choice: `next_step` and `start_fresh` are gone). Done only runs the wrap-up check and stops the clean sessions (it says which projects are not clean and stops nothing then); the lab-digest "propose tools" offer, the once-a-day review offer, and the "Start Claude to wrap up" choice are gone, with `daily_done`/`daily_mark`, `tools_prompt`, `WRAPUP.md` and `TOOLS_PROPOSE.md`. `hyperbeam stop` on an unclean project prints the findings and refuses (`--force` stops); the menu's Stop offers Stop anyway or Cancel. What stays: the choice when Open starts Claude in a project with an earlier conversation (Fresh plan session / Review when due / Continue, from `work-loop-start-and-end`), the review itself (Project screen button, `hyperbeam review`, the manager), the lab digest (`hyperbeam lab digest`), the wrap-up check and its notes.
- **Why:** the manager now plans and dispatches work (`hyperbeam work`). The choices after a Merge and at Done were the old way of starting the next piece of work; they replaced the user's working Claude by default and chained questions.
- **Rejected:** keeping the review offer at Done (the manager can start a review when it sees one is due; the row note and `kk` still show it); keeping a Claude wrap-up (the user or the manager decides what to do with unclean work).
