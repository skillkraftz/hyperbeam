---
id: 2026-11-11-review-loop-in-the-sidebar-copy
status: implemented
prs: [20]
topic: unsorted
---
# Review loop in the sidebar: Copy report, PR badge, Merge

- **Decision:** the user's loop (prompt, PR and report, paste for review, merge) is one click per slow step: Copy report puts Claude's last message on the clipboard; rows with an open PR of yours show a magenta branch and the PR title; Merge (only with an open PR) confirms, merges with a merge commit, deletes the branch, then updates the local checkout (hyperbeam also runs `hyperbeam update`). `gh` results are cached 5 minutes and fetched off the UI thread; each repo is called with the gh account that owns it.
- **Why:** copying the report and visiting GitHub to merge were the slow parts. Merge never runs without a confirmation.
- **Rejected:** auto-merge; a squash merge (the history keeps the branch); polling gh in the menu thread; one gh account for everything (the repos belong to three accounts).
- **Also:** pnpm in the lab comes from npm, not corepack (corepack 0.24 can't run pnpm 12).
