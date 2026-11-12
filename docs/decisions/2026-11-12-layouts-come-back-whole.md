---
id: 2026-11-12-layouts-come-back-whole
status: implemented
prs: [50]
topic: sessions
---
# Layouts come back whole: the hyperbeam session is saved too, panes restart their programs, no restore question

- **Decision:** the `hyperbeam` session's layout is saved like a project's (its `home` windows; the `menu` window is always rebuilt) and `ensure_menu` rebuilds it after a reboot (Claude with `--continue`). Each pane that runs a program (not a shell, Claude, `sudo` or tmux) records its command line (the shell's first child process) and gets it typed again on restore. A saved layout is restored without asking: the "Restore last layout?" question is gone. The hyperbeam session no longer gets a "did not stop cleanly" note.
- **Why:** after a reboot the hyperbeam session came back as the fixed default (Claude left, one shell right) and the layout the user had built was lost, because `save_layout` and `save_all` skipped it. Restored panes were empty shells, so editors and log tails had to be started by hand. A restore question has no sensible "no" for a set of panes; the real choice is about the Claude conversation, which is its own step (continue or start fresh, the work loop).
- **Rejected:** a separate saved layout file for the manager session (same `layout.json` as every project); recording the program from `pane_current_command` alone (name only, no arguments); restarting `sudo` commands (never rerun by itself).
