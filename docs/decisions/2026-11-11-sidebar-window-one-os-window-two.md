---
id: 2026-11-11-sidebar-window-one-os-window-two
status: implemented
prs: [13, 15]
topic: unsorted
---
# Sidebar window: one OS window, two splits

- **Decision:** desktop `open_mode = "sidebar"`: one kitty window with the menu on the left (outside tmux) and `tmux attach` on the right; opening a project switches the right client only. The session file must not start with `new_os_window`. Hide/show uses kitty's stack/splits layouts. The hotkey repairs a half-open window; Done closes it.
- **Why:** the user works mostly by mouse and voice and wanted a persistent project sidebar; Textual's double-click works outside tmux.
- **Rejected:** a tmux pane menu on desktop (clicks switch the whole client); a leading `new_os_window` (opened an extra empty window); guessing the right client from activity (record its tty instead).
