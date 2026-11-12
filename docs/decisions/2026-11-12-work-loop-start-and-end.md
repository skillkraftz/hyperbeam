---
id: 2026-11-12-work-loop-start-and-end
status: implemented
prs: [52]
topic: work-loop
---
# A conversation has a start and an end: a choice when Claude starts and after a finished Merge run

- **Decision:** when Open creates a session for a project that has a manifest and an earlier Claude conversation, a modal asks how Claude starts: **Fresh plan session** (default), **Review** (only when `review_after` merges are due) or **Continue last conversation** (also Escape). The fresh session is a new Claude in plan mode started from `START.md` plus the open PRs and the same snapshot the review uses: it checks for half-done work, proposes the next 1 to 3 items and waits. The old conversation is set aside (Previous Claude brings it back). After a Merge run that merged everything, the same choice is offered for the running project (fresh / review / keep). Not asked: onboarding, a Recover start, a project with no earlier conversation, the hyperbeam session after a reboot (it continues).
- **Why:** a Claude conversation is never done until the user says so, so work drifts on in one ever-growing session that re-reads more every request, and nothing pushes a piece of work to a resolved state. Merging is the natural end of a piece of work and Open the natural start; asking there costs one click and makes continuing a decision instead of a default.
- **Rejected:** always starting fresh without asking (sometimes the last conversation is exactly what is wanted); asking on every Open of a running session (nothing is started then); a separate Fresh button in the Project screen (not asked for; the Merge end and Open cover the moments); making the hyperbeam session ask at reboot (the sidebar's UI does not exist yet when it is created; left for step 2).
