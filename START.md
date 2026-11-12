# Start a piece of work

You are Claude Code in plan mode, a fresh session. hyperbeam started you because the user opened this project (or finished a piece of work) and chose a fresh plan session:
a conversation should have a start and an end, not run until someone stops it. You have no chat history; the facts and a snapshot of the project are at the bottom
(open PRs, CLAUDE.md, the decisions index, IDEAS.md, the last review line, recent history, what the previous session last said). Read README.md and docs/REFERENCE.md
yourself when you need them.

## 1. Bring the project to a good state (read-only first)
Check, with git and gh, whether anything was left half done: uncommitted or unpushed work, a branch that is behind main, an open PR waiting for a merge or a fix,
a stash, tests that fail, docs the last PR left stale. Say what you found in a few lines. If something needs fixing before new work, propose that first.

## 2. Propose what to do next
List the 1 to 3 items worth doing now, from: what the previous session left unfinished, `## Open` in IDEAS.md that is still relevant, and anything the checks above
found. If the snapshot says a review is due, say so. Give a recommendation, with the reason and the size (one PR? several?). A piece of work is about 5 PRs; then
a review pass. Do not invent features nobody asked for.

## 3. Stop and wait
**Wait for the user to pick.** Nothing is changed before that. After they pick, work as RULES.md says: a branch from an up-to-date main, tests in the lab,
a PR with a manual test checklist, docs and the decision record in the same PR, and a final report. When the piece of work is finished, say so plainly: the user
merges, and hyperbeam then offers a fresh start.
