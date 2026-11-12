---
id: 2026-11-12-review-pass
status: implemented
prs: []
topic: workflow
---
# A review pass after every few merged PRs, recorded in docs/reviews/

- **Decision:** after `review_after` (default 5) PRs merged since a project's last review, Done offers a review: REVIEW.md plus the facts (merged PRs and their files, decision records added, IDEAS.md, the last record) injected into the project's Claude in plan mode. Opus proposes ONE cleanup PR (duplication, hacks, missing tests, stale docs, decisions that replaced each other, IDEAS items to close), then it is done after approval, with a review record `docs/reviews/YYYY-MM-DD.md` (`through`, `prs`, what was refactored and updated) and the regenerated decisions index. The newest record is how a project (and a new Claude session, via `hyperbeam context` and a note on the project row) knows how much work has gone by since the last check. IDEAS.md has `## Open` and `## Done`; the work loop around it is listed there as ideas to plan, not built.
- **Why:** work done fast by many PRs layers up (PRs #31 to #40 were never checked as a whole and no test of them was kept). A planned, bounded review keeps the repo close to a refactored, final state without a token-expensive back and forth, and says when a session's batch of work is finished.
- **Rejected:** a git tag for the last review (pushing tags is one more outward step; a record also carries what was covered); a marker line in IDEAS.md (cannot say what the review covered); reviewing after every merge (most tokens); a hard block in Done (Done never stops the user from stopping).
