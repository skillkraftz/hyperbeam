---
id: 2026-11-15-verbs-merge-update-kk
status: implemented
prs: [62]
topic: verbs
---
# The Test button, Merge's update and kk, fixed

- **Decision:** `run_verb(.., "test")` sends the lab's output through `say` (`cmd_lab` takes an optional `say` callback instead of writing `sys.stdout`, which is Textual's in the menu) and ends with `test ok` or `test FAILED (exit N); full output: <verb-test.txt>`. Merge records the default branch's commit before the first merge and passes it as `since` to `verb_update`, which measures changes from it (merge_pr had already pulled), installs when a lockfile changed, restarts services only when something changed, and says what it did. `install.sh` links `~/.local/bin/kk` to the installed script and `hyperbeam update` (`link_kk`) fixes an old link to the dev folder (a real file is left alone).
- **Why:** the Test button crashed on stdout; Merge's update saw "already up to date" and never installed; kk ran the dev folder's script, i.e. the user's state through unreviewed code.
- **Rejected:** a separate update path for Merge (one `verb_update` serves both); relinking kk on every start (only at install/update).
