---
id: 2026-11-12-a-conflicting-pr-is-handed-to
status: superseded
prs: [38]
topic: merge
collapsed_into: [2026-11-12-merge-flow]
code: hyperbeam:_merge_all
---
# A conflicting PR is handed to Claude to rebase, not left to the user

- **Decision:** before merging each PR, Merge does a dry-run merge of the branch against main (`git merge-tree`); on a conflict it injects the update prompt (rebase onto main, resolve, re-test in the lab, push, don't merge) into the project's Claude and stops; one more click on Merge finishes the rest.
- **Why:** PRs that each add a decision at the top of docs/DECISIONS.md conflict whichever order they merge in (#34, #35, #36 did); the user had to ask for the rebases and run the force-push. He wants Merge to complain only when something needs him.
- **Rejected:** merging in a "smarter" order (the conflict is between any two of them); a bot that rebases and merges by itself (Claude should see the conflict and re-run the tests); moving decisions to the end of the file (the file is newest first on purpose).
