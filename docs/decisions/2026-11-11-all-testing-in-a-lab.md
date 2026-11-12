---
id: 2026-11-11-all-testing-in-a-lab
status: implemented
prs: [16]
topic: lab
---
# All testing in a lab

- **Decision:** agent testing runs only through `hyperbeam lab run`, as the user `hblab` on a fixed-size disk image (own home, tmux, Xvfb display). The guard blocks every `kill`/`pkill`/`killall` outside it, and a worktree's script outside it.
- **Why:** rules and per-command guards kept missing the next way to hurt live work (`tmux kill-server`, windows on the main screen, `pkill -f "hyperbeam _menu"` matching the live tmux server's own command line). A different uid cannot signal the user's processes at all.
- **Rejected:** more regex rules alone; containers/VMs (heavier than needed for a personal prototype); letting agents have root.
