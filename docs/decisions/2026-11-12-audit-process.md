---
id: 2026-11-12-audit-process
status: implemented
prs: [55]
topic: review
---
# The whole-project audit: list, triage, small PRs, close; `hyperbeam audit` starts it

- **Decision:** a whole-project audit is a process of five steps started by `hyperbeam audit` (a fresh plan-mode Claude, AUDIT.md, the review's snapshot): a read-only pass lists findings; the user triages each (fix now, defer to IDEAS with a reason, accept with the reason written down); a docs-only PR records the findings in `docs/audits/<date>.md`; the fixes go in small PRs ordered by dependency, each with tests, a decision record and the docs it touches; it closes when every finding is fixed, deferred or accepted, with a review record so counting restarts. Reviews now also record what they looked at and left alone (`left_alone:`).
- **Why:** a review covers the PRs since the last one and ends in one cleanup PR. For the whole package (6.6k lines, 446 functions) one PR is too big to review, findings that are not fixed live only in a proposal's text and get rediscovered, and nothing says when the work is over. The same code grows faster than it is cleaned up, which is what reviews and superseding decisions are for.
- **Rejected:** running the audit as a review with no `through` commit (one PR, no triage, no record of what was left alone); fixing as findings are found (the user cannot weigh a fix without the whole list); a separate audit tool outside the review mechanism (the swap, the snapshot and Previous Claude already exist).
