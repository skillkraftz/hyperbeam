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
- ~/.config/tmux/tmux.conf already exists. hyperbeam never replaces it: it holds one added line, `source-file -q ~/.config/tmux/hyperbeam.conf`; everything else is in hyperbeam.conf (this repo), symlinked there (`ln -sfn ~/projects/hyperbeam/hyperbeam.conf ~/.config/tmux/hyperbeam.conf`).

## Rules
- **Branch work happens in a git worktree at ~/.cache/hyperbeam-work/<branch>** (`git worktree add -b <branch> ~/.cache/hyperbeam-work/<branch> main`), so ~/projects/hyperbeam stays on main: the user's live hyperbeam runs from there, and manifest commits go to its main. Remove the worktree when the PR is open (`git worktree remove`). Test with the worktree's script, never the live symlink.
- **WINDOWS: never open, focus or leave a real window (kitty or anything else) on the user's primary monitor.** The only screen allowed is the far-left monitor near 0/0 (eDP-1, the laptop panel, which the user does not use), and the window must not take focus. The primary monitor is DP-7, not the laptop. GNOME/Wayland can't place windows, so default to NOT opening any: test with an isolated tmux server and pty clients. If a real window is truly needed, use an Xwayland kitty (`HB_KITTY_ARGS="-o linux_display_server=x11 --class hbwin"`), move it with XMoveWindow to ~100,1000, check X focus before and after, and close it at once. **Every test run has WAYLAND_DISPLAY and DISPLAY unset** (`env -u WAYLAND_DISPLAY -u DISPLAY`, including when the isolated tmux server is started) so no window can open on any screen; with a test config (`HB_CONFIG`) `spawn_kitty` also refuses to open a window unless `HB_KITTY_ARGS` is set. Never run a test with `open_mode = "window"` unless that is the test.
- **The guard hook enforces the dangerous parts of the rules above for Claude sessions inside hyperbeam** (see Guard). A block message says what to do instead; don't look for a way around it, ask the user.
- Prototype for personal use: keep it simple.
- Verify, don't assume. Check the machine before writing down a fact about it.
- Never print or commit secrets (.env files, keys, tokens). Say only that such a file exists.
- Ignored files are listed in PRIVATE.md.
- **Steno files:** `steno-YYYY-MM-DD.txt` files whose first line starts with `stenographr` can appear in any project folder. They are the user's personal dictation notes, never project files. Never commit them, never `git add` them (no `git add -A`/`.` while one isn't ignored), and don't read them for project purposes. `steno` normally adds `steno-*.txt` to the repo's .gitignore (and ~/.config/git/ignore has it too, so untracked ones usually don't show in `git status`).
- Manifests (`projects/<name>.toml`) are committed straight to hyperbeam's main and pushed: no branch, no PR. Everything else goes through a branch and a PR.

## Commands
`hyperbeam` is one Python script, a uv script with its dependency (textual) declared inline, symlinked to `~/.local/bin/hyperbeam`
(`ln -sfn ~/projects/hyperbeam/hyperbeam ~/.local/bin/hyperbeam`). The shebang hard-codes /home/andy/.local/bin/uv so a GNOME hotkey works
without PATH. **Settings** (`open_mode`, `claude_model`, `claude_effort`, `menu_width`, `recent_days`, also `accounts` = the GitHub accounts that count as "mine", `projects_dir`) live in the user's `~/.config/hyperbeam/config.toml` (`$XDG_CONFIG_HOME`; `HB_CONFIG` overrides it in tests), laid over the repo's `config.default.toml` (defaults, never written by hyperbeam). The Settings screen writes only the user file, so the repo stays clean. If the user file is missing and the repo still has an old `config.toml`, its values are copied over once (`hyperbeam _migrate-config [FILE]`).

- `hyperbeam`: attaches to the tmux session `hyperbeam` (creating it if needed), in which the menu runs; switches the client instead if already inside tmux. GNOME hotkey command: `kitty /home/andy/.local/bin/hyperbeam`. The project called `hyperbeam` *is* this session (there is no separate project session for it). Its layout is one window: the menu on the left (55%), Claude top right (cwd ~/projects/hyperbeam), a shell bottom right.
- `hyperbeam scan`: table of every git repo under ~/projects (any depth, skipping node_modules, .venv, target, dist, build...) plus top-level folders without git.
- `hyperbeam open NAME [-d]`: start the project's session if needed (no manifest: investigate prompt, see Open) and attach in this terminal (`-d`: don't attach).
- `hyperbeam stop NAME`: the Stop action without the menu.
- `hyperbeam info [NAME]` = `kk` (`ln -sfn ~/projects/hyperbeam/hyperbeam ~/.local/bin/kk`; the script checks its own name; no `kk`/`hb-info` existed before): the project's URLs and endpoints, discovered, plain text, one value per line (a label may follow after two spaces).
  NAME defaults to $HB_PROJECT, which every session has. Sections, each skipped if it doesn't apply: Services (up/down), App (ports
  listened on by processes inside the project's session), Tailscale (those ports if not loopback-only, docker published ports, supabase URLs),
  Docker (containers matched by the compose `working_dir` label or the supabase CLI `workdir` label), Supabase (`supabase status -o json`,
  URL values only, only when the project's supabase containers run; plus the linked project's dashboard URL), Vercel (project name from
  `.vercel/project.json`/`repo.json`; the production URL needs `vercel login`, but the GitHub repo homepage often has it), Git (web URL, GitHub homepage via
  `gh`), .env (URL-valued variables of `.env*` except examples; passwords masked unless the host is this machine), Extra (`[links]`).
  The menu's Info (i) button opens the same text in a plain tmux window (Enter closes it), so mouse-drag copy works.
- `hyperbeam list`: numbered running project sessions, most recent first, with port, up/down, the Tailscale URL (and the local URL at the
  laptop). A number switches (inside tmux) or attaches (outside); q quits (single keypress up to 9 sessions). Also the status view. The
  session you are in is marked `(here)`. Every hyperbeam session is listed (tagged `@hb`, or with a manifest); without a manifest or port it shows `no port`.
- `hyperbeam phone`: for SSH from the phone. Prints the same URL list, then attaches/switches to the most recently used running session
  (not the current one). If nothing runs it says so and points at `list` and the menu.

## The menu
Textual app, built for a ~45-column phone screen: one list, no tabs. A row is a dot (only for running projects), the name (clipped with `…`
so the dot and port always fit) and the port right-aligned (`unset` in orange = no manifest, `-` = manifest without a port). Name: bold white if
opened within `recent_days`, else grey. Order: running, then recent, then the rest, alphabetical within each. Under the list one line gives the
selected project's dot reason (or nothing). Buttons: Open (o), Stop (s), Done (d), Settings (t), a 2x2 grid below 50 columns. Hidden keys: b onboard,
i info, r refresh, q quit (detach). Arrows move. A single click or tap on a row selects it; a double click or tap (Textual's `Click.chain >= 2`: same spot within `CLICK_CHAIN_TIME_THRESHOLD`) or Enter opens it (`ProjectList`; its handler must call `event.prevent_default()` or the base class still selects on every click).

**Dots:** green = running, services up; red = a service is down/exited (checked live) or the start check found git problems (stored in ~/.local/state/hyperbeam/status/<project>.json, cleared on Stop; **Refresh re-runs the git checks** so red clears when the problem is gone); blue = Claude waits for the user; cyan = Claude is working. Priority red > blue > cyan > green. A crash alone (saved layout not `clean`, git clean) is not red: it is a *note*, listed under Notes in the hyperbeam session's `kk` until the project is opened (with git problems it is added to them). The row of a red project selected shows a **Fix (f)** button: RECOVER.md plus the red reasons into that project's Claude pane (`fix_project`). The port column: the number, `-` for a manifest without a port, orange `unset` only without a manifest (manifests are re-read every 5 s, not only on Refresh). The hyperbeam row is bold because the menu records `hyperbeam` as opened. `kk` shows the same as text: in a project session `status: [red] reason` plus the detail; in the hyperbeam session, for every open project (red first) its `[colour] name: reason` line, its full kk detail, and a divider, then Notes.

**Hooks (blue/cyan):** `hyperbeam _hooks` merges command hooks into ~/.claude/settings.json (nothing else touched; one backup `settings.json.hyperbeam-backup`; idempotent; replaces PR #10's older ones) that write ~/.local/state/hyperbeam/claude/$HB_PROJECT: `waiting <reason>` on `Stop`, `Notification` (any type) and `PreToolUse` matching `AskUserQuestion|ExitPlanMode` (Claude asks a question or proposes a plan without ending its turn, which `Stop` alone misses); `working` on `UserPromptSubmit` and `PostToolUse` (so approving a permission or answering a question turns it cyan again). Plain shell, ~20 ms, a no-op without $HB_PROJECT. The state is ignored unless a process named `claude` runs in the project's Claude pane. Claude Code reads hooks at start: a Claude that was already running when the hooks were installed or changed needs a restart.
Event names and settings structure are from the Claude Code docs (code.claude.com/docs/en/hooks).

**Settings screen (t)** is a `ModalScreen`: it owns all input while open. Up/Down choose a row; Left/Right (or Enter) and the − / + buttons change it (a toggle flips, numbers and lists clamp at the ends); Esc or Close goes back. open_mode, claude_model (sonnet/opus/haiku/fable), claude_effort (low..max), menu_width, recent_days, written to the user's config file, then the key cheat sheet. Why input used to leak (PR #10): the screen was a plain `Screen`, so (1) the App's bindings (o, s, d...) still applied on top of it (`_modal_binding_chain` stops only at a modal), and (2) its OptionList `OptionSelected` message bubbled up to the Menu's handler, which opened the next project. Now: modal, the Menu's `check_action` disables its actions whenever another screen is up, its handlers check the message's source widget, and Settings stops the events it handles. Confirm and Choice were already modals that stop their button events. Every Claude hyperbeam starts is `claude --model <claude_model> --effort <claude_effort>` (defaults sonnet, medium).

**Layout of the hyperbeam session:** the menu is a column of `menu_width` columns (default 45), Claude top right, a shell bottom right. The menu keeps its own width (`resize-pane -x`) when a client of another size attaches;
on a client narrower than 2*width+10 (the phone) it zooms itself once (`M-z` shows the rest) and unzooms when the client gets wide again.

**Prompt injection (`inject_prompt`, used by recover, wrap-up and onboarding):** Claude running in the target pane: one line `Read <file> and follow it.` and Enter. Otherwise `claude --continue "$(cat file)" || claude "$(cat file)"` (with the model/effort flags). Pane choice (`find_claude_pane`): the pane running claude, else the left pane of `work`, or pane 1 of the hyperbeam session. Never the menu pane (text sent there is keystrokes for the menu).

- **Open (o):** open-or-onboard. Starts the tmux session if it isn't running, then shows it according to `open_mode` (the user's config):
  `"switch"` (default) switches the client that looks at the menu to it, at the laptop and over SSH (one terminal; the stack keys go back);
  `"window"` opens a new kitty window attached to the session at the laptop (over SSH it switches, there is no kitty to open).
  Local or remote is the menu client's (`client_pid`, see below), not the menu's own environment. `HB_KITTY_ARGS` adds kitty options (tests).
  If there is no manifest, or a service exits or misses its ready check, the session still opens, but its Claude pane starts
  `claude "<prompt>" --add-dir ~/projects/hyperbeam` with the investigate prompt instead of plain `claude` (it runs in the project dir,
  inside the project's session). With a manifest and no failure Claude starts plain, after the services are ready.
  The prompt is ONBOARDING.md plus project name, manifest path or "none", the tmux session, why, and the last 50 lines of each failing
  service's window; it is saved to ~/.local/state/hyperbeam/prompts/.
- **Stop (s):** asks first. Runs each service's `stop` command in reverse order, kills the session, then checks the project's ports are
  closed and warns if something is still listening. Without a manifest it only kills the session. Refuses to stop the session the menu itself runs in.
- **Onboard (b):** forces the same investigate path: a new session if none runs, else a new `investigate` window in the running session.
  ONBOARDING.md tells Claude to read the project, install dependencies, start and test it (Docker rule), propose the manifest and
  WAIT for approval before writing projects/<name>.toml, list project changes, not commit.
- **Refresh (r)**, **Quit (q)**: Quit detaches the client; the menu keeps running in its session. Action results stay on screen until you press Refresh.

`open` creates session `<name>` with `HB_PROJECT=<name>`, `PORT`, `HB_PORT` (if the project has a port), `HOST=0.0.0.0` and the manifest's `[env]` in its environment (no manifest: only HOST), and windows: `work` (Claude on the left 60%, a shell on the right 40%), then one window per service (its output is the log).
A service starts only after the previous one is ready. After the last one the shell pane prints real warnings (no git, no remote, uncommitted changes,
no CLAUDE.md; nothing if there are none) and then runs `kk`, and Claude starts in the left pane. Splits are percentages, so they scale when a client of another size
attaches (tested at 150 and 58 columns: at phone width the right pane gets ~9 columns, so use M-z).

## Stack, copy, mouse (hyperbeam.conf, no prefix)
- Sessions hyperbeam creates carry the tmux option `@hb`. The **stack** is the `hyperbeam` session, then those sessions by creation time.
  `M-h` goes back to the `hyperbeam` session (the menu) from anywhere (plain `switch-client`, the client that pressed it). `M-]` next, `M-[` previous, in the current client only (each client has its own position). Not in the stack: your other sessions; from one of those, `M-]` goes to the menu.
- `M-y` copies the current pane's whole scrollback, trailing blank lines trimmed. Local client: wl-copy, message "copied N lines".
  Remote client: saved to ~/.local/state/hyperbeam/outbox/<session>-<time>.txt and the path is shown (phone delivery comes later).
- Mouse is on. Dragging a selection copies it to the tmux buffer, and at the laptop to the Wayland clipboard too. Shift+drag is kitty's own selection.
- `M-Left/Right/Up/Down` select the pane (wraps around), `M-z` zooms. Checked: tmux.conf binds M-Arrow only in the prefix table (resize), GNOME's Alt bindings (Tab, F4, Space, Esc, Above_Tab...) and kitty's defaults (ctrl+shift only) don't use plain Alt+Arrow or Alt+z, so nothing was moved.
  The cost: inside Claude Code's prompt, tmux now takes M-Left/M-Right, so Alt+arrow word jumps there don't work (Alt+b / Alt+f are the readline alternatives; not tested).
- The keys are shown in the Settings screen and the status-right of every hyperbeam session (set per session at creation, so other sessions keep the old bar). If you change a key, change `KEYS`/`HINT` in the script and hyperbeam.conf.
- Local or remote is decided per client, not per server: `#{client_pid}` -> that process's environment has SSH_CONNECTION/SSH_TTY, or an ancestor is sshd*, mosh-server or tailscaled. `#{client_tty}` tells nothing (both are ptys).
- wl-copy runs from the tmux server, so it needs the server's WAYLAND_DISPLAY; if the server was started over SSH it hasn't one, so the script falls back to the socket in $XDG_RUNTIME_DIR.
- Window positioning: GNOME/Wayland gives clients no way to place windows. A kitty started with `-o linux_display_server=x11` is an Xwayland window and can be moved with XMoveWindow (tested: lands on the far-left monitor, X focus unchanged). Not used by hyperbeam.

## Guard (PreToolUse hook on Bash)
Why: agents inside a hyperbeam session have `$TMUX`, so a bare `tmux ...` talks to the user's REAL tmux server. A `tmux kill-server` from a Claude working on stenographr once took down hyperbeam and every project session. CLAUDE.md text didn't stop it; this does.
- **Mechanism** (Claude Code hooks docs): a `PreToolUse` hook with matcher `Bash` gets `{"tool_name": "Bash", "tool_input": {"command": ...}}` on stdin. **Exit 2 with a message on stderr blocks the call and the message goes to Claude**; exit 0 with no output allows it (JSON `hookSpecificOutput.permissionDecision: "deny"` is the other way). Tested with a real `claude -p --permission-mode bypassPermissions`: still blocked, message delivered.
- **Which server a `tmux` reaches:** the socket in `$TMUX` (the real server) unless `-L <name>` or `-S <path>` names another. Verified on an isolated server: from inside a pane, `TMUX_TMPDIR=...` and `env -u TMUX` still reached that same server; only `-L`/`-S` reached another. So the guard accepts only `-L`/`-S` naming another socket (a `-L` equal to the basename of the `$TMUX` socket, or `-S` the same path, is the real one).
- **Rules** (`RULES` in `guard.py`, the whole list is there): (1) tmux kill-server/-session/-window/-pane (and killw/killp) not aimed at another socket; (2) pkill/killall/kill aimed at tmux or kitty (by name, `$(pgrep|pidof tmux|kitty)`, or a pid whose /proc comm is tmux/kitty; a pattern naming `tmux -L`/`-S` is allowed); (3) a GUI app (kitty, terminals, browsers, editors...) started while WAYLAND_DISPLAY or DISPLAY is set in the environment, unless the command unsets both (`env -u WAYLAND_DISPLAY -u DISPLAY ...`). Everything else is allowed. It is textual, so a command that merely mentions `tmux kill-server` (e.g. in `echo`) is blocked too; that is accepted.
- **Install:** `hyperbeam _hooks` merges it into `~/.claude/settings.json` with the state hooks (idempotent, other keys untouched). The hook command runs `exit 0` at once without `$HB_PROJECT`, else `/usr/bin/python3 <repo>/guard.py` (stdlib only, ~17 ms). Run `_hooks` from the live checkout (`~/projects/hyperbeam`), not a worktree, since the settings point at that path. Claude Code reads hooks at start: restart Claude sessions.
- hyperbeam's own tmux calls are not affected: hooks see only Claude's tool calls. Test a rule by feeding sample JSON to `guard.py`, never by running the command.

## Beam in: layouts and the start check
- **Layouts** are saved to ~/.local/state/hyperbeam/layouts/<project>.json: per window its name and tmux `#{window_layout}`, per pane its cwd and role (`claude`, `shell`, `service:<name>`, `other`), the active window and pane, a time and `clean`. Saved: on Stop (with `clean: true`), when a client detaches or its terminal goes away or it switches session (tmux hooks `client-detached[90]` and `client-session-changed[90]` in hyperbeam.conf run `hyperbeam _save`, which saves every hyperbeam session because the hook has no session name left to give), every 5 minutes while the menu runs, and once when a session starts. `select-layout` with a saved string works on a different window size (tmux rescales when a client attaches) but is silently ignored if the pane count differs, so panes are created first.
- **Open** on a project that isn't running but has a saved layout asks "Restore last layout?" (a modal in the menu, y/n in the terminal for `hyperbeam open`; no terminal means no). Yes recreates windows, panes, cwds, layouts and active pane; services restart from the manifest in order; Claude panes run `claude --continue` (the most recent conversation in that directory; verified it takes an initial prompt too; falls back to a fresh `claude` if there is none), only the first per directory; other panes get a shell. No gives the default layout.
- **Start check** (`start_check`, built on `git_problems`, which the wrap-up check will reuse; `hyperbeam _check PATH [--fetch]` prints it): uncommitted changes, unpushed commits (or commits on no remote), stashes, detached HEAD, merge/rebase/cherry-pick/revert in progress, behind the upstream (after a `git fetch` with a 6 s limit, no prompts, ssh ConnectTimeout 3, failure ignored), and "not stopped cleanly" (a saved layout with `clean: false` and no running session: crash, reboot, killed session). steno files are left out of the counts; one git could commit (tracked, or untracked and not ignored) is reported as its own warning. The results print above `kk` in the shell pane. If anything was found (and the project has a manifest and it isn't Onboard) it asks "Start Claude to sort it out?": yes starts Claude with RECOVER.md plus the findings (with `--continue` if the layout was restored). RECOVER.md: diagnose read-only, propose, wait for approval, never commit steno files. No Claude unless the user says yes.

## Beam out: session record and wrap-up check
- **Session record** `~/.local/state/hyperbeam/journal.json`: `started`, `menu_started`, and the projects opened or switched to (`touch_opened`, and the `client-session-changed` hook via `hyperbeam _save <session>`). Survives a menu restart; cleared only by a completed Done for now.
- **Wrap-up check** (`wrapup_check`, reuses `git_problems(..., behind=False)`; `hyperbeam _wrapup PATH [--since TS]` prints it): uncommitted/unpushed work, stashes, detached HEAD, merge/rebase; steno files tracked or not ignored; obvious secrets in commits since the record started, staged and unstaged changes, untracked files, and secret-looking tracked file names (.env, id_*, *.pem, *.key, credentials.*; `.env.example` etc. are safe). Patterns: private-key headers, AWS/GitHub/Slack/Stripe-live/Google/Anthropic-OpenAI keys, URLs with a password (not localhost), literal password/secret/token/api_key assignments (skipped in test/fixture dirs, placeholders and low-variety values). Output is file, line, pattern name (and commit), never a value. Real repos: 0 hits on 21 repos' tracked files after the test-dir exemption (1 before).
- **Stop** (menu or `hyperbeam stop`, `--force` skips) runs it first: clean, confirm and stop; not clean, choose Start Claude to wrap up (WRAPUP.md plus findings, in the project's Claude pane: typed as a one-line pointer if Claude runs there, else `claude "$(cat file)"`), Stop anyway, or Cancel.
- **Done for now (d)** checks every recorded project: all clean, offers to stop their sessions and clears the record; otherwise offers Claude in the hyperbeam session's Claude pane with all findings; press Done again when finished.

## Manifest format
`projects/<name>.toml` in this repo (not in the project). Written by Claude through Onboard (there is no heuristic drafting). `port` is optional: a project with nothing to serve has none, and then no PORT/HB_PORT is set. Ports start at 3100 and never repeat across manifests.

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

[env]                      # optional: extra session env, overrides the defaults (HOST=0.0.0.0)
SOME_VAR = "value"

[links]                    # optional: extras `kk` cannot discover; name = url
docs = "https://example.com/docs"
```
A service that exits before its port opens is reported as a warning and the next one still starts.

Docker rule: app dev servers run on the host in a tmux window; backing services (databases, Supabase, Caddy...) run through docker compose;
containerize the app itself only if the project specifically needs it.

## Reachable over Tailscale
The phone reaches dev servers directly: `http://<this machine's MagicDNS name>:<port>` (from `tailscale status --json`, currently
`xps-1.tail9babd7.ts.net`; the short name `xps` belongs to an old offline node, so don't use it). No tunnels. A server must bind all
interfaces, so each manifest makes that so, never the project:
- Next.js (`next dev`, 15 and 16): binds 0.0.0.0 by default and reads `PORT`. Nothing to do.
- Vite (verified, 8.3.6): binds localhost unless `--host`; ignores `HOST`; its host check answers 403 for the MagicDNS name unless
  `__VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS=.ts.net` is set. Use `--host $HOST --port $HB_PORT` in `cmd` and that variable in `[env]`.
- docker compose services publish ports on 0.0.0.0 by default (so a Supabase db is reachable from the LAN/tailnet with its dev password).
- Last used = tmux `#{session_last_attached}` (empty until first attach, updated by attach and switch-client), falling back to `#{session_created}`.
- ufw is configured off (`ENABLED=no` in /etc/ufw/ufw.conf); the live ruleset needs root to read.

## Testing
**Visual tests (opening or closing real windows, e.g. `open_mode = "window"`) go only on the far-left monitor near 0/0 (eDP-1, a screen the user does not use), and must not take focus.** Never open a window anywhere else. GNOME/Wayland can't place windows, so use an Xwayland kitty (`HB_KITTY_ARGS="-o linux_display_server=x11 --class hbwin"`) and move it with XMoveWindow; check X focus before and after; close it right away. If that can't be done cleanly, test on an isolated tmux server with a pty client instead. Use a throwaway config (`HB_CONFIG`) and make sure it says `open_mode = "switch"` unless that test needs `"window"`: a leftover `"window"` made a test open four real kitty windows.
`HB_MANIFESTS=<dir>` points at another manifests directory. Test with an isolated tmux server (`TMUX_TMPDIR=$(mktemp -d /tmp/hbt.XXXX)`: the socket path must be short) and
`XDG_STATE_HOME`, never against the live sessions. Start the server with `tmux -f <conf that sources tmux.conf and hyperbeam.conf> start-server`.
A fake remote client: a private sshd (`sshd -f` with its own host key, authorized_keys, 127.0.0.1:<port>, run as yourself) and `ssh -tt ... tmux attach`.
Drive clients through a pty, not by `tmux send-keys` (that bypasses the client). Never `pkill -f` a pattern that appears in your own command line. A Textual pilot script can import the file with `importlib` (`SourceFileLoader`) and click the widgets.

## Environment
`uv run --script` puts VIRTUAL_ENV, UV, UV_RUN_RECURSION_DEPTH and `~/.cache/uv/environments-*/bin` first in PATH into hyperbeam's environment, and a tmux server started by
hyperbeam keeps it in its global environment, so every session inherited it (`python` was hyperbeam's). The script now strips those at startup, and `start_session`
removes them from an already-running server's global environment. Verified on a server started with a fake VIRTUAL_ENV/UV: new sessions have none of them and `python` is /usr/bin/python.

## Gotchas
- `supabase status` prints keys and secrets next to URLs; never print its raw output, only URL values (`-o json`, stdout only).
- pnpm 12 installs dependencies by itself on `pnpm dev`. Opening a project whose node_modules is missing therefore modifies it.
- `claude "prompt"` starts an interactive session with that first prompt (`claude --help`); `-n` names it, `-c` continues, `-r` resumes.
- Textual parses `[x]` in labels as markup: write shortcuts as `Open (o)`.
