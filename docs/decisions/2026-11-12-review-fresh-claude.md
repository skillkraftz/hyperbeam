---
id: 2026-11-12-review-fresh-claude
status: implemented
prs: [43]
topic: workflow
---
# The review runs in a fresh plan-mode Claude swapped into the pane

- **Decision:** `hyperbeam review` and the Done offer replace the project's Claude, in the same pane, with a fresh `claude --permission-mode plan` (opusplan: Opus plans) that starts from REVIEW.md, the facts and a compact snapshot (CLAUDE.md, decisions index, IDEAS.md, last review, recent history, what the previous session last said; about 6k tokens). The conversation it replaced is remembered and returns with `hyperbeam back` or the Previous Claude button. Every prompt hyperbeam writes starts with a plan-first line, and the guard blocks `hyperbeam review --print` outside plan mode. Refines `2026-11-12-review-pass` (how the review starts); the Onboard/Fix/wrap-up steps still inject `/plan` into the running Claude.
- **Why:** the first review was done by Sonnet because it was run inside an ordinary-mode turn, and an injected `/plan` depends on the session being idle and on its mode. A fresh plan-mode start is guaranteed Opus, needs nothing from the old session, and the review batch is a natural session boundary (the repo is the memory); the snapshot keeps it from starting blind without a huge context.
- **Rejected:** a new tmux window (goes unnoticed); `/plan` into the running session (the mode and idleness of that session decide); the review as an Opus subagent of a Sonnet session (no control from hyperbeam, and subagents are only spawned on request).
