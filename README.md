# hyperbeam

hyperbeam is a personal "senior engineer" for many AI-assisted prototype projects on one Linux laptop. One hotkey opens a sidebar of every project in ~/projects; each opens as a tmux session with Claude Code, a shell and its services, ready to work at the laptop (and later from the phone over Tailscale).

**Why.** AI-assisted prototypes drift. Docs stop matching code, PRs pile up, decisions live in old chats, tests break live work, and tokens run out. hyperbeam keeps every project aligned to one set of rules (RULES.md), keeps each project's memory in its repo (CLAUDE.md, docs/DECISIONS.md), runs all agent testing in an isolated lab, shows problems with status dots, and turns the daily loop (prompt, PR, review, merge) into a few clicks.

**Goals, in order.** Smooth work at the laptop; fewer tokens (Opus plans and Sonnet builds in one session; cheap scripts before Claude; repeated lab work becomes tools); a system that gets better the more it is used; then the phone; then a polish phase (refactor, README, demos).

## Using it
- **Hotkey** (Ctrl+Alt+H, runs `hyperbeam`): opens the sidebar window, the project menu on the left, the project's tmux session on the right. Pressing it again says it is already open. Over SSH or inside tmux, `hyperbeam` attaches to the menu in tmux instead.
- **Sidebar:** click a row to select it, double-click (or Enter) to open it: its tmux session starts with Claude Code, a shell and the services from its manifest (`projects/<name>.toml`). `hyperbeam ~/other-folder` uses another folder's projects for this run.
- **Dots:** green = running, blue = Claude waits for you, cyan = Claude is working, red = rare and real (a service is down, secrets in unpushed commits, a stuck merge). Quieter things (uncommitted work, setup changed since onboarding) are notes, never red. A magenta branch = you have an open PR.
- **Buttons:** Open, Stop, Done (wrap-up check, then closes the sidebar), Settings, Update (pull main, reload), Onboard (manifest, then alignment with RULES.md), Copy context (a bundle to paste into a chat), Copy report (Claude's last message, for review), Merge (only with an open PR; it asks first), Project (one screen per project), Hide.
- **`kk`** (`hyperbeam info`): the project's URLs and endpoints (services, ports, Tailscale, Docker, Supabase, open PRs).
- **Keys inside tmux:** `M-h` back to the menu, `M-[` and `M-]` previous and next session, `M-y` copy the Claude conversation (or the pane's whole scrollback), `M-s` hide or show the sidebar, `M-arrows` select a pane, `M-z` zoom. Shift+Tab is Claude Code's plan mode.
- **The lab:** all agent testing runs there, as the separate user `hblab`: `hyperbeam lab run --why "unit tests" -- npm test`. Set it up once with `sudo bash lab/setup.sh`; then `hyperbeam lab status`, `hyperbeam lab stop`, `hyperbeam lab log --today`. Details in CLAUDE.md.

Roadmap: IDEAS.md. Why things are the way they are: docs/DECISIONS.md. How it works now: CLAUDE.md. The rules every project follows: RULES.md.
