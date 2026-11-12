---
id: 2026-11-11-stale-doc-hints-and-wrap-up
status: implemented
prs: [24]
topic: unsorted
---
# Stale-doc hints and wrap-up notes

- **Decision:** a plain-script check compares README.md and CLAUDE.md with the project: commands and paths they mention that don't exist, and docs far older than the run setup. A finding is a quiet note (never red) with Onboard/Align as the fix, and ALIGN.md gets the full list. Every wrap-up check that finds something is saved as a dated note in `.hyperbeam/notes` before the user chooses what to do next.
- **Why:** after a changed run setup (drift), docs that no longer match the code are the next silent failure; wrap-up findings used to vanish into chat and the next session started blind.
- **Rejected:** asking Claude to judge the docs every time (tokens for nothing when they are fine); a red alert (it is not an emergency); one note file per run (a dated file per day is enough and stays readable); writing a note for a clean wrap-up.
