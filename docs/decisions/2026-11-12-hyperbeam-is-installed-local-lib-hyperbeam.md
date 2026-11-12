---
id: 2026-11-12-hyperbeam-is-installed-local-lib-hyperbeam
status: implemented
prs: [40]
topic: unsorted
---
# hyperbeam is installed (~/.local/lib/hyperbeam); development happens in ~/projects/hyperbeam on branches

- **Decision:** `install.sh` clones origin into `~/.local/lib/hyperbeam` (always main, never edited by hand), links `~/.local/bin/hyperbeam` and `~/.config/tmux/hyperbeam.conf` to it and re-points the Claude hooks (the guard) at it. The app already finds everything through `HERE` (its own folder), so it runs from there unchanged; `update` and Merge fast-forward that clone; manifests are committed to its main. The project "hyperbeam" (the sidebar row, the home session's Claude) is `~/projects/hyperbeam`, the dev folder, where work happens on a branch like in every other project. The guard blocks running any checkout's `hyperbeam` script as the user except the installed one.
- **Why:** the live app was the dev folder, so it had to stay on main, all work went into worktrees in `~/.cache`, and Claude kept asking for permission to edit there. Other projects (stenographr) are installed and developed in place.
- **Rejected:** `uv tool install` (hyperbeam is one script with prompts, tools, lab scripts and manifests beside it, found through its own folder); a symlink farm into the dev folder (the live app would still be the dev checkout); copying files at install time (update would need a rebuild step instead of `git pull`).
