---
id: 2026-11-12-merge-stops-only-when-main-changed
status: superseded
prs: [32]
topic: merge
collapsed_into: [2026-11-12-merge-flow]
code: hyperbeam:_merge_all
---
# Merge stops only when main changed the PR's own files

- **Decision:** Merge's "behind main" modal (Ask Claude to update / Merge anyway) appears only when commits on main since the branch point touch files the PR also changes. Behind in other files: the plain Yes/No, with a one-line note.
- **Why:** manifests go straight to main by design, and Claude opens PRs in the background, so main moves on all the time. PR #31 was flagged "1 commit behind" for a stenographr manifest commit. The user wants Merge to complain only when the default would leave something to investigate.
- **Rejected:** ignoring only manifest commits (two independent PRs merged in a row would still warn); asking GitHub for mergeability (it reports textual conflicts only, and an overlap without a conflict is still worth a re-test).
