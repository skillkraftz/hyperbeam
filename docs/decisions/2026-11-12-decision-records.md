---
id: 2026-11-12-decision-records
status: implemented
prs: []
topic: docs
---
# Decisions are one file each, with a status and what they collapsed into

- **Decision:** every design decision is its own file, `docs/decisions/YYYY-MM-DD-slug.md`, with front matter (`id`, `status` = `implemented` | `superseded`, `topic`, `prs`; a decision that replaces others lists them in `supersedes`; a superseded one must say what it collapsed into: `collapsed_into` (decision ids) or `code` (the code that now embodies it)). `docs/DECISIONS.md` is a generated index of the implemented ones per topic (superseded ones under what absorbed them); only the review pass regenerates it. The Go tool `decisions` (`list`, `check`, `index`) reads the records.
- **Why:** every PR added an entry at the top of one file, which conflicted on #34, #35 and #36, and later entries quietly replaced earlier ones (four about Merge). The user wants the parts kept with a reference to where each came from, so that a thousand decisions can later be condensed into a short README without losing the way back.
- **Rejected:** one file with the newest entry on top (conflicts); appending at the end (still one file, still conflicts); a status flag without saying what a decision collapsed into (the condensing needs the link); regenerating the index in every PR (it would conflict again).
