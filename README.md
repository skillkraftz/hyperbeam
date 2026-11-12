# hyperbeam

hyperbeam is a personal "senior engineer" for many AI-assisted prototype projects on one Linux laptop. One hotkey opens a sidebar of every project in ~/projects; each opens as a tmux session with Claude Code, a shell and its services, ready to work at the laptop (and later from the phone over Tailscale).

**Why.** AI-assisted prototypes drift. Docs stop matching code, PRs pile up, decisions live in old chats, tests break live work, and tokens run out. hyperbeam keeps every project aligned to one set of rules (RULES.md), keeps each project's memory in its repo (CLAUDE.md, docs/DECISIONS.md), runs all agent testing in an isolated lab, shows problems with status dots, and turns the daily loop (prompt, PR, review, merge) into a few clicks.

**Goals, in order.** Smooth work at the laptop; fewer tokens (Opus plans and Sonnet builds in one session; cheap scripts before Claude; repeated lab work becomes tools); a system that gets better the more it is used; then the phone; then a polish phase (refactor, README, demos).

## Using it
- **Hotkey** (Ctrl+Alt+H, runs `hyperbeam`): opens the sidebar window, the project menu on the left, the project's tmux session on the right. Pressing it again says it is already open. Over SSH or inside tmux, `hyperbeam` attaches to the menu in tmux instead.
- **Sidebar:** click a row to select it, double-click (or Enter) to open it: its tmux session starts with Claude Code, a shell and the services from its manifest (`projects/<name>.toml`). `hyperbeam ~/other-folder` uses another folder's projects for this run.
- **Dots:** green = running, blue = Claude waits for you, cyan = Claude is working, red = rare and real (a service is down, secrets in unpushed commits, a stuck merge). Quieter things (uncommitted work, setup changed since onboarding) are notes, never red. A magenta branch = you have an open PR.
- **Buttons:** Open, Stop, Done (wrap-up check, then closes the sidebar; it never stops a project whose Claude is working or waiting), Update (the selected project's `update`), Merge (only with an open PR; it asks, merges, then updates the project), More (the Project screen: Install, Test in the lab, Version, Help, Onboard, Copy context, Copy report, Edit manifest, Settings, Keys, Hide). The title line shows your 5-hour limit the way claude.ai does (`5h 83% - resets Thu 1:00am`) or `update available`; `hyperbeam usage` has the weekly limit and which conversations are huge. Prompts hyperbeam sends to Claude (Onboard, Fix, wrap-up) start in plan mode, so Opus proposes and Sonnet builds after you approve.
- **PRs show up at once:** after any `gh pr create|merge|close` in a project session a hook runs `hyperbeam refresh-prs`, so the Merge button appears about a second later.
- **Install:** `bash install.sh` installs hyperbeam to `~/.local/lib/hyperbeam` (the app you run, kept current by `hyperbeam update` and Merge) and links `hyperbeam` and the tmux conf to it; you work on hyperbeam in `~/projects/hyperbeam` on branches like any other project.
- **Review pass:** after 5 merged PRs (a setting) Done offers a review: Claude, in plan mode, checks the whole batch and proposes one cleanup PR; the result is a record in `docs/reviews/`. `hyperbeam review` starts one by hand.
- **Same verbs everywhere:** `hyperbeam NAME update` (also `install`, `test`, `version`, `help`, `restart`) works for every project, and inside a project's session just `NAME update` or `hb update`; after you click Merge the project updates itself. `hyperbeam new NAME --cli|--web` starts a project that already has them.
- **`kk`** (`hyperbeam info`): the project's URLs and endpoints (services, ports, Tailscale, Docker, Supabase, open PRs).
- **Keys inside tmux:** `M-h` back to the menu, `M-[` and `M-]` previous and next session, `M-y` copy the Claude conversation (or the pane's whole scrollback), `M-s` hide or show the sidebar, `M-arrows` select a pane, `M-z` zoom. Shift+Tab is Claude Code's plan mode.
- **The lab:** all agent testing runs there, as the separate user `hblab`: `hyperbeam lab run --why "unit tests" -- npm test`. Set it up once with `sudo bash lab/setup.sh`; then `hyperbeam lab status`, `hyperbeam lab stop`, `hyperbeam lab log --today`. Details in CLAUDE.md.

Roadmap: IDEAS.md. Why things are the way they are: docs/DECISIONS.md. How it works now: CLAUDE.md. The rules every project follows: RULES.md.
