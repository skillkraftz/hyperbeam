---
id: 2026-11-09-menu-in-a-tmux-session-session
status: implemented
prs: [5, 7]
topic: ui
---
# Menu in a tmux session, session stack, M-keys

- **Decision:** the menu runs in the tmux session `hyperbeam`; each project is its own session (tagged `@hb`); `M-h`, `M-[`, `M-]` navigate the stack; mouse on; `M-y` copies history. Everything is in `hyperbeam.conf`, sourced by one added line in the user's tmux.conf, which hyperbeam never replaces.
- **Why:** one tool for laptop and phone (Termux over SSH/Tailscale), without new terminal windows per project.
- **Rejected:** a kitty window per project; replacing the user's tmux.conf.
