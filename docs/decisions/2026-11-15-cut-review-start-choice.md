---
id: 2026-11-15-cut-review-start-choice
status: implemented
prs: [60]
topic: work-loop
supersedes: [2026-11-12-review-pass, 2026-11-12-review-fresh-claude, 2026-11-12-review-every-project, 2026-11-12-audit-process]
---
# Open continues the last conversation; reviews and audits are worker tasks the manager writes

- **Decision:** Open attaches when the session runs; otherwise it starts the session and Claude types `claude --continue ... || claude ...` (the last conversation of the folder, a fresh one if there is none). No question. Gone: `start_choice`, `begin_claude`, `choose_tty`, `set_aside`, `swap_claude`, `back_claude`, `previous-claude` and the Previous Claude button, `hyperbeam back`, the review counter (`reviews_due`, `last_review`, `review_baseline`, `review_notes`, `review_line`, the `review_after` setting, the row note and the `Last review` part of `hyperbeam context`), `hyperbeam review` and `hyperbeam audit` with REVIEW.md, AUDIT.md, START.md and the Review button, and the guard's review-outside-plan rule. An old `review_after` in config.toml is ignored. `docs/reviews/` files stay as history.
- **Why:** the manager plans and dispatches work (`hyperbeam work`); when the user wants a review or an audit it writes one as a worker task. The counter was buggy (the wrong file for two reviews on one date, it counted its own PR) and the start choice, swap and back machinery only served the old plan-session flow; Fresh was the default and replaced a working Claude.
- **Rejected:** keeping the counter as a hint for the manager (it can read the merged PRs itself); keeping `hyperbeam review --print` as a prompt builder (the manager writes the prompt).
