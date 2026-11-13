---
id: 2026-11-12-manager-session-is-home
status: superseded
prs: [45]
topic: ui
collapsed_into: [2026-11-12-manager-row]
code: hyperbeam:ensure_menu
---
# The hyperbeam session is home: first in the list, where Stop returns to, width kept on resize

- **Decision:** the `hyperbeam` row (the manager session: Claude and a shell for hyperbeam itself) is always the first row, and a fresh list highlights the project the right side shows, else that row. Stopping a project first moves every tmux client looking at it to `hyperbeam:home`, then kills the session; project sessions also get `detach-on-destroy off`. If the right split is missing, showing a session opens it again through kitty remote control. The menu re-applies `menu_width` when the window is resized (debounced, not while hidden).
- **Why:** killing the session the right client was on detached it, tmux attach exited and kitty closed the right split, and it could not be reopened without restarting the sidebar. The row order and the first-row highlight after a restart picked whatever running project sorted first alphabetically.
- **Rejected:** a global `detach-on-destroy off` in hyperbeam.conf (it would change the user's other tmux sessions); a tmux `session-closed` hook (it runs after the client is already gone); a separate manager session with another name (the hyperbeam project already is that session).
