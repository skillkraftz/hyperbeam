---
id: 2026-11-12-injected-prompts-start-in-plan-mode
status: implemented
prs: [31]
topic: unsorted
---
# Injected prompts start in plan mode

- **Decision:** `inject_prompt` always puts Claude in plan mode: a running Claude gets `/plan Read <file> and follow it.`; a Claude it starts gets `--permission-mode plan`. ONBOARDING.md and ALIGN.md tell Claude to re-enter plan mode before the alignment proposal (the first approval leaves plan mode).
- **Why:** with `opusplan`, Opus runs only in plan mode. Onboarding stenographr injected the prompt into a pane in the default mode, so Sonnet wrote the proposal. Every injected prompt is "propose, wait for approval, then act", which is what plan mode is for.
- **Rejected:** sending Shift+Tab to cycle modes (depends on the pane's current mode, fragile); a new Claude window for Onboard instead of injecting (extra window, loses the conversation); plan mode for normal opens (the user starts those and chooses).
