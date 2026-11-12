---
id: 2026-11-12-merge-merges-every-open-pr-oldest
status: implemented
prs: [36]
topic: unsorted
---
# Merge merges every open PR, oldest first, and stops only at a real problem

- **Decision:** the Merge button merges all of the project's open PRs oldest first after one confirmation; each is re-checked against main (files in common) just before it merges; the first one that needs a look stops the run; the project's update runs once at the end. The just-merged PRs are removed from the list directly (GitHub's list lags).
- **Why:** Claude opens PRs in the background, so several are waiting; merging only the newest, with a question per PR, meant clicking Merge and answering for each. The user wants one click and a complaint only when something will need investigating.
- **Rejected:** merging only the newest (what it did); no re-check between merges (two PRs touching the same file would merge untested together); updating after every merge (hyperbeam's update restarts the menu).
