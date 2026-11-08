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

## Commands
`hyperbeam` is one Python 3 script (stdlib only), symlinked to `~/.local/bin/hyperbeam`. `config.toml` holds the GitHub accounts that count as "mine".

- `hyperbeam scan`: table of every git repo under ~/projects (any depth; skips node_modules, .venv, target, dist, build...) plus top-level folders without git. Columns: name, path, owner (mine / other / no remote / no git), uncommitted, manifest.
- `hyperbeam open <name> [-y] [-d]`: attach to the project's tmux session (switch-client if already in tmux), or create it. `-y` accepts a drafted manifest without asking; `-d` creates without attaching.
- `hyperbeam pick`: fzf over the projects (name + owner), then `open`. GNOME hotkey command: `kitty /home/andy/.local/bin/hyperbeam pick`.

`open` creates session `<name>` with `-e PORT=<port> -e HB_PORT=<port>` and windows: `claude` (runs `claude`), `shell` (prints warnings: no git, no remote, uncommitted changes, no CLAUDE.md), then one window per service, in order. A service starts only after the previous one's readiness check passes. The window output is the log.

## Manifest format
`projects/<name>.toml` in this repo (not in the project). If missing, `open` drafts one from detection (package.json scripts, supabase script, docker compose, Procfile), prints it, and asks before continuing. Ports are assigned from 3100 upward and never reuse a port held by another manifest or currently listening.

```toml
path = "~/projects/plantlab"
port = 3101

[[service]]               # ordered; each waits for the previous one's check
name = "dev"              # tmux window name
cmd = "pnpm dev"          # run in the project dir; sees $PORT and $HB_PORT
ready_port = 3101         # optional: wait until this TCP port opens
ready_delay = 5           # optional: sleep this many seconds first
ready_timeout = 60        # optional: give up waiting after N seconds (default 120)
```
A service that exits before its port opens is reported as a warning and the next one still starts.

## Gotchas
- pnpm 12 installs dependencies by itself on `pnpm dev`. Opening a project whose node_modules is missing therefore modifies it.
- `claude --help`: `claude "prompt"` starts an interactive session with that first prompt; `-n/--name` sets a display name; `-c` continues, `-r` resumes.
