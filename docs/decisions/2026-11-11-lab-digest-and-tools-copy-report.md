---
id: 2026-11-11-lab-digest-and-tools-copy-report
status: implemented
prs: [23]
topic: unsorted
---
# Lab digest and tools; Copy report finds the real report

- **Decision:** every `lab run` is already logged; a plain script turns the log into a daily digest (flaky, slowest, repeated commands and sequences as tool candidates) shown at Done at no token cost. Only when there are real candidates, and the user says yes, Claude proposes at most 3 small tools (TOOLS_PROPOSE.md); approved ones are built as tested scripts in `tools/` (run with `hyperbeam tool NAME` in the lab), listed in TOOLS.md, which every agent checks first. The digest runs the tools' tests and flags a failing one. Copy report takes Claude's final answer in the turn of the user's last real prompt: real prompts are told apart by the conversation file's `origin.kind`, and a one-line reply to a background notice no longer replaces the report.
- **Why:** fewer tokens, and a system that gets better the more it is used: repeated multi-step lab work is the cheapest thing to turn into a script. The report bug cost a wrong paste.
- **Rejected:** a daily Claude run (tokens for nothing when there is no pattern); building tools without approval; treating "the last assistant text" as the report; flagging killed runs (a reset, a timeout) as flaky.
