---
id: 2026-11-12-merge-flow
status: implemented
prs: [32, 36, 38, 44]
topic: merge
supersedes: [2026-11-12-merge-stops-only-when-main-changed, 2026-11-12-merge-merges-every-open-pr-oldest, 2026-11-12-a-conflicting-pr-is-handed-to]
code: hyperbeam:_merge_all
---
# Merge merges every open PR oldest first and stops only at a real problem

- **Decision:** the Merge button merges all of the project's open PRs, oldest first, after one confirmation. Before each one `pr_state` (a fresh fetch, because the PR before it moved main) says how far behind it is, which files main changed that the PR also changed (`overlap`) and which a merge would conflict in (`conflicts`). Behind only in other files (a manifest, another PR) merges without a question. An overlap asks: update and re-test (Claude is given the update prompt) / merge anyway / cancel. A conflict, or GitHub refusing with one, has no merge-anyway: Claude is asked to rebase and re-test and the run stops; Merge again finishes the rest. The first PR that needs a look stops the run and the summary says where. The checkout is only touched when it is on the default branch or the merged branch and clean. The project's update runs once at the end: for hyperbeam always (the installed copy updates from GitHub), for others when the checkout was pulled. A check that cannot be made (offline, a fork) is said out loud and merges without it. Merged PRs are dropped from the list at once.
- **Why:** Claude opens PRs in the background, so several wait at once; the user wants one click and a complaint only when something needs investigating. It started as a "behind main" warning for every newer commit (a manifest commit flagged PR #31), grew into overlap-only, then merge-all, then conflicts handed to Claude; the dev folder became the working checkout, so the local step must not switch a branch being worked on.
- **Rejected:** a warning for every newer commit on main; merging only the newest PR; no re-check between merges (two PRs touching one file would merge untested together); a bot that rebases and merges by itself (Claude should see the conflict and re-run the tests); updating after every merge (hyperbeam's update restarts the menu).
