---
id: 2026-11-11-per-project-data-folders-hyperbeam-link
status: implemented
prs: [17]
topic: unsorted
---
# Per-project data folders, `.hyperbeam` link, shared RULES.md

- **Decision:** config stays in `~/.config/hyperbeam/`; all other state lives in `~/.local/share/hyperbeam/`, with one folder per project (`projects/<name>-<6 hex of the path hash>/`). Each project gets a `.hyperbeam` symlink to it (globally git-ignored). RULES.md in this repo is linked into each folder as `.hyperbeam/RULES.md`, and every project's CLAUDE.md imports it.
- **Why:** hyperbeam is the one place that holds each project's state, and one rules file keeps every project's Claude consistent. The hash keeps same-named projects in different folders apart; the link is remade on Open, so deleting it loses nothing.
- **Rejected:** keeping state inside each project (pollutes repos, dies with a clone); name-only keys (collide).
