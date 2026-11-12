# hyperbeam

@RULES.md

Personal launcher for Ubuntu 26.04 (GNOME/Wayland, kitty): a "senior engineer" for many AI-assisted prototype projects (README.md has the why and the goals; IDEAS.md the roadmap; docs/DECISIONS.md the design decisions).
Hotkey -> a sidebar (a Textual menu) of every project in ~/projects -> one tmux session per project with Claude Code, a shell, services (auto-started in order) and logs.
Works locally; the phone (SSH from Termux over Tailscale) attaches to the same sessions and gets its own round later.

## Decisions (the short list; docs/decisions/ has the why, one file per decision; docs/DECISIONS.md is the generated index)
- Claude Code is the default agent, on `opusplan` (Opus plans, Sonnet builds, one session per project).
- One tmux session per project.
- Manifests (`projects/<name>.toml`, in this repo, not in the projects) say how a project starts: ordered services, ports, env.
- Each project gets a fixed port, set through tmux session env vars. No direnv.
- `kk` (`hyperbeam info`) lists a project's URLs and endpoints; status dots show what needs attention.
- ~/.config/tmux/tmux.conf already exists. hyperbeam never replaces it: it holds one added line, `source-file -q ~/.config/tmux/hyperbeam.conf`; everything else is in hyperbeam.conf (this repo), symlinked there (`ln -sfn ~/projects/hyperbeam/hyperbeam.conf ~/.config/tmux/hyperbeam.conf`).

## Rules
- **hyperbeam is installed, like any project.** The app the user runs is a clone of main at `~/.local/lib/hyperbeam` (`install.sh` makes it and links `~/.local/bin/hyperbeam` and the tmux conf to it; `hyperbeam update` and Merge fast-forward it): never edit it, never branch in it. Manifests (`projects/<name>.toml`) are written and committed to main there. **Development happens in ~/projects/hyperbeam** (this folder) **on a branch**: `git fetch`, then `git switch -c <branch> origin/main`; commit, push, open the PR; when it is merged, `git switch main && git pull`. Test with this folder's script through the lab (`hyperbeam lab run --dir ~/projects/hyperbeam -- uv run --quiet --script hyperbeam ...`). A git worktree (`~/.cache/hyperbeam-work/<branch>`) is only for two branches at once.
- **WINDOWS: never open, focus or leave a real window (kitty or anything else) on the user's primary monitor.** The only screen allowed is the far-left monitor near 0/0 (eDP-1, the laptop panel, which the user does not use), and the window must not take focus. The primary monitor is DP-7, not the laptop. GNOME/Wayland can't place windows, so default to NOT opening any: test with an isolated tmux server and pty clients. If a real window is truly needed, use an Xwayland kitty (`HB_KITTY_ARGS="-o linux_display_server=x11 --class hbwin"`), move it with XMoveWindow to ~100,1000, check X focus before and after, and close it at once. **Every test run has WAYLAND_DISPLAY and DISPLAY unset** (a fake `kitty` on PATH that only logs its arguments is fine for launch tests) (`env -u WAYLAND_DISPLAY -u DISPLAY`, including when the isolated tmux server is started) so no window can open on any screen; with a test config (`HB_CONFIG`) `spawn_kitty` also refuses to open a window unless `HB_KITTY_ARGS` is set. Never run a test with `open_mode = "window"` unless that is the test.
- **ALL TESTING RUNS IN THE LAB (see Lab).** Never run test servers (tmux, kitty, a hyperbeam menu), kills (`kill`, `pkill`, `killall`, `tmux kill-*`) or GUI apps as the user; run them with `hyperbeam lab run`. This has gone wrong repeatedly: a `tmux kill-server` took down every session, tests opened windows on the main screen, and a `pkill -f "hyperbeam _menu"` killed the whole live tmux server (a server's command line is the command that created it, so any pattern can match it). Rules and guards kept missing the next case; the lab removes the possibility.
- **Never run the dev folder's or a worktree's `hyperbeam` script as the user** (only the installed one, `hyperbeam` on PATH): it uses the user's real state, tmux and config (PR #17: `lab status` from a worktree migrated the live state folder). Use `hyperbeam lab run --dir <worktree> -- uv run --quiet --script hyperbeam ...`; the guard blocks the rest. **The guard hook enforces the dangerous parts of the rules above for Claude sessions inside hyperbeam** (see Guard). A block message says what to do instead; don't look for a way around it, ask the user.
- Prototype for personal use: keep it simple.
- Verify, don't assume. Check the machine before writing down a fact about it.
- Never print or commit secrets (.env files, keys, tokens). Say only that such a file exists.
- Ignored files are listed in PRIVATE.md.
- **Steno files:** `steno-YYYY-MM-DD.txt` files whose first line starts with `stenographr` can appear in any project folder. They are the user's personal dictation notes, never project files. Never commit them, never `git add` them (no `git add -A`/`.` while one isn't ignored), and don't read them for project purposes. `steno` normally adds `steno-*.txt` to the repo's .gitignore (and ~/.config/git/ignore has it too, so untracked ones usually don't show in `git status`).
- Manifests (`projects/<name>.toml`) are committed straight to hyperbeam's main and pushed: no branch, no PR. Everything else goes through a branch and a PR.

## Where things are
- `install.sh`: installs hyperbeam (see Rules). `hyperbeam`: the whole app, one uv script (Textual menu, CLI commands, lab, verify, shot, digest, tools). `guard.py`: the Claude Bash hook. `hyperbeam.conf`: tmux keys and hooks.
- Prompts injected into Claude: `ONBOARDING.md`, `ALIGN.md`, `RECOVER.md`, `WRAPUP.md`, `TOOLS_PROPOSE.md`, `REVIEW.md`. `projects/<name>.toml`: a project's manifest (format in the reference).
- `lab/` (setup, remove, podman, rsync shell), `tools/` (tested scripts, listed in `TOOLS.md`), `docs/` (`decisions/` the why, one file per decision, `DECISIONS.md` their generated index, `REFERENCE.md` the details, `UI.md`, `PODMAN.md`), `IDEAS.md` the roadmap, `README.md` the why and the goals.
- State is in `~/.local/share/hyperbeam/` (per project: `projects/<name>-<hash>/`, linked into each project as `.hyperbeam`); settings in `~/.config/hyperbeam/config.toml`.

## Commands (details in the reference)
`hyperbeam` (sidebar), `update`, `scan`, `open NAME`, `stop NAME`, `info`/`kk`, `list`, `phone`, `context [--size|--full]`, `report`, `refresh-prs [NAME] [N...]`, `review [NAME] [--since C]`, `back [NAME]`, `align-facts`, `verify [merge]`, `shot [--cols 35]`, `usage`, `new NAME --cli|--web`, `lab run|status|stop|log|digest|reset`, `tool NAME|--list|--test`.
**`hyperbeam NAME VERB`**: the same verbs in every project: `install`, `update`, `test` (always in the lab), `version`, `help`, `restart`. A project's own script/Makefile target/manifest `[commands]` wins; otherwise hyperbeam derives a default from the lockfile (pnpm/npm/uv/pip/cargo). The sidebar's Update button runs `update` for the selected project, and **Merge runs the project's update by itself afterwards**: click Merge, nothing else. Inside a project's session `NAME VERB` and `hb VERB` do the same (`dotwork help`); `hyperbeam new` starts a project that already conforms.
`lab run [--dir D] [--why TEXT] [--fresh] [--collect PATH] [--timeout S] [--] COMMAND` runs as the user `hblab` in a synced copy of the project (secrets and `.git` are not copied); options go before the command. The lab shares the machine's network: bind port 0 or `$LAB_PORT_MIN`-`$LAB_PORT_MAX`. `lab reset` is the user's, agents use `lab stop`.

## Testing
All of it in the lab (see Rules). Pattern: a throwaway set of projects and manifests (`HB_MANIFESTS`, `HB_CONFIG`, `XDG_DATA_HOME`), fake `claude`/`gh`/`wl-copy` on PATH, the menu driven through a pty read with pyte, tmux isolated by the lab. `hyperbeam shot --cols 35` shows the real sidebar as pictures (`~/.cache/hyperbeam-shots/`): look at them after any UI change; `docs/UI.md` has the design constraints (35 columns on the laptop, about 42 on the phone, mouse first).

## Guard (PreToolUse hook on Bash; the full rule list is `guard.py`)
Blocks, with a message saying what to do instead: tmux kill commands aimed at the real server, `kill`/`pkill`/`killall` outside `hyperbeam lab run`, GUI apps with a display set, `hyperbeam lab reset`, `git worktree remove --force`, deleting a dirty worktree, and running the `hyperbeam` script of the dev folder or a worktree as the user (`lab run`, `tool`, `shot`, `lab status|stop|log|digest` are the exceptions). It is textual: a command that only mentions a blocked word is blocked too (write such text with the Write tool). Never look for a way around a block: ask the user.

## Reference: docs/REFERENCE.md sections
- Conventions: the same verbs in every project
- Usage (the numbers claude.ai shows)
- Commands inside a session, and `hyperbeam new`
- Data layout, .hyperbeam, RULES.md
- Context: the repo is the memory
- Align (projects follow the system)
- Review loop: report, PR badge, Merge
- Project screen and drift
- Lab digest and tools (the system improves with use)
- Stale docs and wrap-up notes
- Verify, shot, UI (what the user and the agent each do)
- Commands
- The menu
- Stack, copy, mouse (hyperbeam.conf, no prefix)
- Lab (agent testing)
- Guard (PreToolUse hook on Bash)
- HB_CLAUDE_PANE (for tools running in a pane, e.g. stenographr)
- Sidebar mode (desktop)
- Update and try
- Beam in: layouts and the start check
- Beam out: session record and wrap-up check
- Manifest format
- Reachable over Tailscale
- Testing
- Environment
- Gotchas
