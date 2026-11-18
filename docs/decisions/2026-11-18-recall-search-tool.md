---
id: 2026-11-18-recall-search-tool
status: implemented
topic: tools
prs: []
---

# `recall`: one local full-text index over everything said and done with Claude, run as the user

## Decision
`tools/recall/` (Go, pure-Go SQLite with FTS5, database `~/.local/share/hyperbeam/recall.db`) indexes Claude Code transcripts, claude.ai exports in `~/manager/inbox`, stenographr notes and the manager's notes into units (a message, a few steno lines, a note section), incrementally by size/mtime (Claude Code files by appended bytes). `search` ranks with bm25 and filters by source, project, date, role; `show ID` prints the units around a hit. A search re-indexes first when a source changed. Secret-looking strings are masked before they are stored and when printed. A tool with a `host` marker file (only recall) runs as the user through `hyperbeam tool NAME`; its test still runs in the lab.

## Why
The user's history lives in files nobody searched. The lab user cannot read the user's home, and the tool only reads and writes its own database, so running as the user is safe; every other tool stays in the lab.

## Rejected
- Running recall in the lab: it sees none of the data.
- An embedding/semantic index: heavy, and keyword search with bm25 answers "what did we decide about X".
- Grep over the files: slow on 123 MB and no ranking, no message boundaries.
