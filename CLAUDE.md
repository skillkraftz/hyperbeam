# hyperbeam

Personal launcher for Ubuntu 26.04 (GNOME/Wayland, kitty). Hotkey -> fzf picker of ~/projects ->
one tmux session per project with Claude Code, a shell, services (auto-started in order) and logs.
Works locally and from Termux over Tailscale.

## Decisions
- Claude Code is the default agent.
- One tmux session per project.
- Manifests in the style of Tim's juggler, kept outside the project repos.
- Each project gets a fixed port, set through tmux session env vars. No direnv.
- A kk-style status command comes later.
- ~/.config/tmux/tmux.conf already exists. hyperbeam adds small changes to it later and never replaces it.

## Rules
- Prototype for personal use: keep it simple.
- Verify, don't assume. Check the machine before writing down a fact about it.
- Never print or commit secrets (.env files, keys, tokens). Say only that such a file exists.
- Ignored files are listed in PRIVATE.md.
