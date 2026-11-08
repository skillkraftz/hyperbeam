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
`hyperbeam` is one Python script, a uv script with its dependency (textual) declared inline, symlinked to `~/.local/bin/hyperbeam`
(`ln -sfn ~/projects/hyperbeam/hyperbeam ~/.local/bin/hyperbeam`). The shebang hard-codes /home/andy/.local/bin/uv so a GNOME hotkey works
without PATH. `config.toml` holds the GitHub accounts that count as "mine".

- `hyperbeam`: the menu. GNOME hotkey command: `kitty /home/andy/.local/bin/hyperbeam`.
- `hyperbeam scan`: table of every git repo under ~/projects (any depth, skipping node_modules, .venv, target, dist, build...) plus top-level folders without git.
- `hyperbeam open NAME [-d]`: start the project's session if needed and attach in this terminal (`-d`: don't attach).
- `hyperbeam stop NAME`: the Stop action without the menu.

## The menu
Textual app in the storywheel style (tabs, option list, one-line buttons that never take focus, modal confirm). Everything is a visible
button, with its key in the label. Tabs: Running, Recent (last opened, kept in ~/.local/state/hyperbeam/state.json), Mine, Others
(not mine: other owner, no remote, no git), Not configured (no manifest). It opens on the first non-empty of Running/Recent/Mine.
Arrows move the selection, left/right change tab, Enter or a click on a row opens it.

- **Open (o):** starts the tmux session if it isn't running (services in order), then shows it: at the laptop in a new kitty window running
  `tmux attach`; over SSH (SSH_CONNECTION set, or no display) it switches/attaches in the current terminal instead.
  kitty can't focus an existing window on GNOME/Wayland (tested: `kitty @ focus-window` returns ok but the window stays unfocused), so a
  second Open gives a second window attached to the same session.
- **Stop (s):** asks first. Runs each service's `stop` command in reverse order, kills the session, then checks the project's ports are
  closed and warns if something is still listening. Refuses to stop the session the menu itself runs in.
- **Onboard (b):** opens kitty in ~/projects/hyperbeam running `claude` with ONBOARDING.md plus the project name and path. Claude reads
  the project and writes projects/<name>.toml, and replies with what should change in the project (it doesn't edit the project).
- **Refresh (r)**, **Quit (q)**. Action results stay on screen until you press Refresh.

`open` creates session `<name>` with `-e PORT=<port> -e HB_PORT=<port>` and windows: `claude`, `shell` (prints warnings: no git, no remote,
uncommitted changes, no CLAUDE.md), then one window per service. A service starts only after the previous one is ready. The window output is the log.

## Manifest format
`projects/<name>.toml` in this repo (not in the project). Written by Claude through Onboard (there is no heuristic drafting). Ports start at 3100 and never repeat across manifests.

```toml
path = "~/projects/plantlab"
port = 3101

[[service]]                # ordered; each waits for the previous one to be ready
name = "db"                # tmux window name
cmd = "docker compose up"  # run in the project dir; sees $PORT and $HB_PORT
ready_port = 54322         # wait until this TCP port opens. Default: the project's port. false = don't wait
stop = "docker compose down"   # optional; Stop runs these in reverse order before killing the session

[[service]]
name = "dev"
cmd = "pnpm dev"           # ready_port defaults to port = 3101
ready_delay = 5            # optional: sleep N seconds first (alone, it replaces the port check)
ready_timeout = 60         # optional: give up waiting after N seconds (default 120)
```
A service that exits before its port opens is reported as a warning and the next one still starts.

Docker rule: app dev servers run on the host in a tmux window; backing services (databases, Supabase, Caddy...) run through docker compose;
containerize the app itself only if the project specifically needs it.

## Testing
`HB_MANIFESTS=<dir>` points at another manifests directory. Test with an isolated tmux server (`TMUX_TMPDIR=$(mktemp -d /tmp/hbt.XXXX)`) and
`XDG_STATE_HOME`, never against the live sessions. A Textual pilot script can import the file with `importlib` (`SourceFileLoader`) and click the widgets.

## Gotchas
- pnpm 12 installs dependencies by itself on `pnpm dev`. Opening a project whose node_modules is missing therefore modifies it.
- `claude "prompt"` starts an interactive session with that first prompt (`claude --help`); `-n` names it, `-c` continues, `-r` resumes.
- Textual parses `[x]` in labels as markup: write shortcuts as `Open (o)`.
