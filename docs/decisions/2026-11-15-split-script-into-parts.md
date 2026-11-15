---
id: 2026-11-15-split-script-into-parts
status: implemented
prs: []
topic: layout
---
# The hyperbeam script is split into parts in hb/

- **Decision:** `hyperbeam` stays the entry point (uv script, same commands and install) and execs `hb/<part>.py` in order into its own namespace; the parts are the old file cut at its `# ----------` sections (config, state, session, workers, checks, sidebar, lab, verify, verbs, new, context, merge, info, menu, cli), none over ~1500 lines. CLAUDE.md has the map and the rule to read only the part you change.
- **Why:** one ~6k-line file (~90k tokens) was read in large chunks by every agent that changed any part of it, paid again on every later turn.
- **Rejected:** real Python modules with imports: the tests (and tools) patch functions and constants on the script (`hb.gh_run`, `hb.DATA_DIR`, even `hb.time`) and rely on callers seeing them, so a real split would need every cross-module call rewritten (behaviour risk for no gain here).
