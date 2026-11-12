# Design decisions (newest first)
Date, decision, why, what was rejected. Seeded from the merged PRs and git history on 2026-11-11; add new entries at the top, in the PR that makes the decision.

## 2026-11-11 The shared lab: per-run isolation; merge safety (PR #21)
- **Decision:** every `lab run` is its own session with an id, recorded in `/srv/hblab/runs/` and tagged with `HB_RUN_ID` in the environment of everything it starts; `lab stop` stops only a project's own runs; `lab reset` refuses while other projects have runs and its `--force` is for the user only; the guard blocks agents from `lab reset` and from `git worktree remove --force` / deleting a worktree with uncommitted work. Each run gets its own tmux and runtime dirs. Merge checks how far the PR is behind main: if behind, the modal offers "Ask Claude to update and re-test" (default) or "Merge anyway"; PRs older than 7 days are marked stale.
- **Why:** a `lab reset` killed another project's e2e suite running in the same lab, and the other agent lost time chasing "random" SIGKILLs. A worktree with uncommitted work was force-removed once. A PR that passed its tests against an older main can break main when merged.
- **Rejected:** one lab per project (disk and caches would be duplicated); finding processes only by process group (daemonised children leave the group; the environment tag follows them); cgroups or a network namespace (need root); blocking merges of PRs that are behind (the user decides).

## 2026-11-11 Cheaper context, fitting modals, verify opens the PR, Docker in the lab (PR #26)
- **Decision:** hyperbeam's CLAUDE.md is cut from 66 KB to 8 KB (the rules, a map and the command list); the detail lives in `docs/REFERENCE.md`, read on demand and never imported. `hyperbeam context --size` shows what each part costs. Modals fit the screen and stack their buttons, Settings labels are short enough for 35 columns. `hyperbeam verify merge` opens the throwaway PR itself so the user only clicks Merge; `ignore_owners` in the user config takes an owner (algoviewz) out of the badge, Merge and verify. Rootless podman works in the lab through two shims (`podman`, `docker`) with one stable runtime dir under /tmp; compose with host networking works, compose's own networks need a user dbus (open).
- **Why:** in a 5-hour window ending at the usage limit there were 642 requests, 0.8M output tokens and 128M cache-read tokens: the cost is context size times requests, and CLAUDE.md is in every request. The two 35-column bugs hid buttons the user needs. verify had pushed work onto the user that the agent used to do.
- **Rejected:** `@docs/REFERENCE.md` in CLAUDE.md (it would load it again); a per-run podman runtime dir (breaks the second run); giving hblab the docker group; a systemd user session for hblab before a project needs it.

## 2026-11-11 Verify command, sidebar screenshots, rootless podman (PR #25)
- **Decision:** GitHub features are assumed to work and are verified by the user with one command, `hyperbeam verify` (PASS/FAIL/YOU with the exact commands); the lab gets no GitHub credentials for now. Docker in the lab is investigated through rootless podman (no docker group, no root) behind one sudo script and a decision gate in docs/PODMAN.md, with a libvirt VM as the fallback. The sidebar is designed from pictures: `hyperbeam shot` renders the real menu in the lab at a chosen width (35 laptop, 42 phone) and brings the PNGs back; docs/UI.md records the constraints and what breaks at 35 columns, which starts the redesign phase earlier than planned.
- **Why:** the user will test GitHub personally, a fake gh already covers the logic, and a lab with credentials was the wrong thing to build first; Docker-based projects (algoviewz-platform) are the real blocker; the 35-column menu has hidden buttons and clipped modals that only show up when looked at.
- **Rejected:** giving hblab the docker group (root); a GitHub token in the lab before there is a need; guessing at widths without looking.

## 2026-11-11 Stale-doc hints and wrap-up notes (PR #24)
- **Decision:** a plain-script check compares README.md and CLAUDE.md with the project: commands and paths they mention that don't exist, and docs far older than the run setup. A finding is a quiet note (never red) with Onboard/Align as the fix, and ALIGN.md gets the full list. Every wrap-up check that finds something is saved as a dated note in `.hyperbeam/notes` before the user chooses what to do next.
- **Why:** after a changed run setup (drift), docs that no longer match the code are the next silent failure; wrap-up findings used to vanish into chat and the next session started blind.
- **Rejected:** asking Claude to judge the docs every time (tokens for nothing when they are fine); a red alert (it is not an emergency); one note file per run (a dated file per day is enough and stays readable); writing a note for a clean wrap-up.

## 2026-11-11 Lab digest and tools; Copy report finds the real report (PR #23)
- **Decision:** every `lab run` is already logged; a plain script turns the log into a daily digest (flaky, slowest, repeated commands and sequences as tool candidates) shown at Done at no token cost. Only when there are real candidates, and the user says yes, Claude proposes at most 3 small tools (TOOLS_PROPOSE.md); approved ones are built as tested scripts in `tools/` (run with `hyperbeam tool NAME` in the lab), listed in TOOLS.md, which every agent checks first. The digest runs the tools' tests and flags a failing one. Copy report takes Claude's final answer in the turn of the user's last real prompt: real prompts are told apart by the conversation file's `origin.kind`, and a one-line reply to a background notice no longer replaces the report.
- **Why:** fewer tokens, and a system that gets better the more it is used: repeated multi-step lab work is the cheapest thing to turn into a script. The report bug cost a wrong paste.
- **Rejected:** a daily Claude run (tokens for nothing when there is no pattern); building tools without approval; treating "the last assistant text" as the report; flagging killed runs (a reset, a timeout) as flaky.

## 2026-11-11 Project screen, drift detection, README, Claude's default model (PR #22)
- **Decision:** a Project screen (modal, keys `i`/`j`, the Project (j) button) shows one project at a glance with its actions (Onboard, Edit manifest, Copy context/report, Info window, Mark as onboarded). Drift is detected without tokens: a fingerprint of the run-defining parts of the project (script names and commands, dependency names, compose services/images/ports, Makefile targets, .env.example variable names; not versions or lockfiles) is stored when the manifest is written or confirmed, compared on Open and Refresh, and a difference is a quiet note, never red. README.md, RULES.md "Working with the user" and IDEAS.md (also in the Copy context bundle) hold what a new chat was missing: the why, how the user works, the roadmap. `hyperbeam _hooks` sets Claude's global model to `opusplan`, once.
- **Why:** the repo is the memory, and a new chat reading the bundle was missing the purpose of hyperbeam and the roadmap. Drift is what makes a manifest wrong silently; a fingerprint finds it for free, Onboard fixes it.
- **Rejected:** a red drift alert (it is not an emergency); fingerprinting versions or lockfiles (noise on every install); resetting the model on every `_hooks` run (it would fight a manual `/model` choice); a YAML dependency for compose files (three facts are read by indentation instead).

## 2026-11-11 Review loop in the sidebar: Copy report, PR badge, Merge (PR #20)
- **Decision:** the user's loop (prompt, PR and report, paste for review, merge) is one click per slow step: Copy report puts Claude's last message on the clipboard; rows with an open PR of yours show a magenta branch and the PR title; Merge (only with an open PR) confirms, merges with a merge commit, deletes the branch, then updates the local checkout (hyperbeam also runs `hyperbeam update`). `gh` results are cached 5 minutes and fetched off the UI thread; each repo is called with the gh account that owns it.
- **Why:** copying the report and visiting GitHub to merge were the slow parts. Merge never runs without a confirmation.
- **Rejected:** auto-merge; a squash merge (the history keeps the branch); polling gh in the menu thread; one gh account for everything (the repos belong to three accounts).
- **Also:** pnpm in the lab comes from npm, not corepack (corepack 0.24 can't run pnpm 12).

## 2026-11-11 Align projects to the system; the lab keeps synced copies and a run log (PR #19)
- **Decision:** projects follow RULES.md; a difference is allowed only as an approved entry in the project's `## Exceptions to hyperbeam rules`. Onboard runs the manifest step and then ALIGN.md (compare docs with the rules and the real repo, propose, wait, then change on a branch). All agent testing, including unit and headless browser suites, runs in the lab. Docker-based tests are not run there (docker group = root) and are listed as exceptions. The lab keeps one rsync-synced copy per project and its dependency caches; every `lab run` is logged (`--why`) to `lab-runs.jsonl`.
- **Why:** projects drift from the docs (a CLAUDE.md saying a public repo isn't public) and from each other; a lab that reinstalls everything each run is too slow to use for all testing; the log is the base for turning repeated lab work into small tools.
- **Rejected:** letting each project override the rules silently; Docker in the lab (root-equivalent); a network namespace for ports (needs privileges: `unshare -n` is denied), so the lab uses a port convention instead; copying `.git` and secrets into the lab.

## 2026-11-11 The repo is the memory; Copy context; opusplan (PR #18)
- **Decision:** each project's CLAUDE.md describes how it works now and `docs/DECISIONS.md` records design decisions; both change in the same PR as the code. `hyperbeam context` (and the Copy context button) puts RULES.md, CLAUDE.md, DECISIONS.md, README, manifest and recent history on the clipboard for a web chat. The default Claude model is `opusplan` (Opus plans, Sonnet implements, one session). A worktree's `hyperbeam` script may only be started through `hyperbeam lab run`.
- **Why:** decisions lived in chat histories, so every new chat started blind. One session per project avoids re-explaining between a planning chat and an implementation chat. Running a worktree script as the user migrated the live state folder (PR #17).
- **Rejected:** an MCP server (more to run; skills come later); separate planning and implementation sessions.

## 2026-11-11 Per-project data folders, `.hyperbeam` link, shared RULES.md (PR #17)
- **Decision:** config stays in `~/.config/hyperbeam/`; all other state lives in `~/.local/share/hyperbeam/`, with one folder per project (`projects/<name>-<6 hex of the path hash>/`). Each project gets a `.hyperbeam` symlink to it (globally git-ignored). RULES.md in this repo is linked into each folder as `.hyperbeam/RULES.md`, and every project's CLAUDE.md imports it.
- **Why:** hyperbeam is the one place that holds each project's state, and one rules file keeps every project's Claude consistent. The hash keeps same-named projects in different folders apart; the link is remade on Open, so deleting it loses nothing.
- **Rejected:** keeping state inside each project (pollutes repos, dies with a clone); name-only keys (collide).

## 2026-11-11 All testing in a lab (PR #16)
- **Decision:** agent testing runs only through `hyperbeam lab run`, as the user `hblab` on a fixed-size disk image (own home, tmux, Xvfb display). The guard blocks every `kill`/`pkill`/`killall` outside it, and a worktree's script outside it.
- **Why:** rules and per-command guards kept missing the next way to hurt live work (`tmux kill-server`, windows on the main screen, `pkill -f "hyperbeam _menu"` matching the live tmux server's own command line). A different uid cannot signal the user's processes at all.
- **Rejected:** more regex rules alone; containers/VMs (heavier than needed for a personal prototype); letting agents have root.

## 2026-11-11 Sidebar window: one OS window, two splits (PRs #13, #15)
- **Decision:** desktop `open_mode = "sidebar"`: one kitty window with the menu on the left (outside tmux) and `tmux attach` on the right; opening a project switches the right client only. The session file must not start with `new_os_window`. Hide/show uses kitty's stack/splits layouts. The hotkey repairs a half-open window; Done closes it.
- **Why:** the user works mostly by mouse and voice and wanted a persistent project sidebar; Textual's double-click works outside tmux.
- **Rejected:** a tmux pane menu on desktop (clicks switch the whole client); a leading `new_os_window` (opened an extra empty window); guessing the right client from activity (record its tty instead).

## 2026-11-11 Guard hook for Claude sessions in hyperbeam (PR #12)
- **Decision:** a PreToolUse hook (`guard.py`, exit 2 + message) blocks tmux kill commands, kills of tmux/kitty, and GUI apps with a display set. Textual and deliberately simple.
- **Why:** CLAUDE.md text did not stop a `tmux kill-server` from a Claude session that took down every session (agents inside hyperbeam have `$TMUX`).
- **Rejected:** relying on instructions only; a sandboxed tmux for agents.

## 2026-11-11 Settings in `~/.config/hyperbeam/config.toml`, defaults in the repo (PR #12)
- **Decision:** user settings are written to the user's file and laid over `config.default.toml`; hyperbeam never writes into the repo.
- **Why:** the Settings screen used to dirty the checkout, which blocks `hyperbeam update`.

## 2026-11-11 Loud problems, red only when rare (PR #14)
- **Decision:** the dot is red only for a down service, secrets in unpushed commits, or a stuck merge with conflicts; everything else is a quiet note. Red shows a popup on entry (or sends RECOVER.md with `on_problem = "auto"`).
- **Why:** problems must not be missed, but constant red teaches the user to ignore it.

## 2026-11-09 Phone-width menu, status dots, Claude hooks (PR #10)
- **Decision:** one list (dot, name, port), no tabs, works at 45 columns. Blue/cyan dots come from Claude Code command hooks (Stop, Notification, AskUserQuestion/ExitPlanMode, UserPromptSubmit, PostToolUse) writing a state file; the state is ignored unless a `claude` process runs in the pane. Hooks are merged into `~/.claude/settings.json`, never overwritten.
- **Why:** the tabbed menu did not fit a phone, and the user needs to see which Claude is waiting.
- **Rejected:** parsing pane output to guess Claude's state.

## 2026-11-09 Beam in / beam out: saved layouts, start check, wrap-up check, Done (PRs #8, #9)
- **Decision:** layouts are saved per project and restored on Open (asked); a start check and a wrap-up check report git state and obvious secrets (file, line, pattern, never the value); Claude is started to fix things only when the user says yes. Stop and Done run the wrap-up check first.
- **Why:** sessions end by crash or reboot, and work gets left uncommitted or unpushed.

## 2026-11-09 Menu in a tmux session, session stack, M-keys (PRs #5, #7)
- **Decision:** the menu runs in the tmux session `hyperbeam`; each project is its own session (tagged `@hb`); `M-h`, `M-[`, `M-]` navigate the stack; mouse on; `M-y` copies history. Everything is in `hyperbeam.conf`, sourced by one added line in the user's tmux.conf, which hyperbeam never replaces.
- **Why:** one tool for laptop and phone (Termux over SSH/Tailscale), without new terminal windows per project.
- **Rejected:** a kitty window per project; replacing the user's tmux.conf.

## 2026-11-08 Manifests outside the projects; onboarding by Claude (PRs #1-#3)
- **Decision:** a project's manifest (`projects/<name>.toml`: ordered services, ready checks, fixed port, env) lives in this repo, not in the project. There is no heuristic drafting: Claude investigates, proposes the manifest and waits for approval (ONBOARDING.md). Manifests are committed straight to main.
- **Why:** the user does not want hyperbeam files in other repos; heuristics guessed wrong, Claude reads the project.

## 2026-11-08 Stack choices (PRs #1, #2)
- **Decision:** one uv script with Textual declared inline; Claude Code is the default agent; one tmux session per project; fixed ports per project through tmux session env (no direnv); the app runs on the host, backing services through docker compose.
- **Why:** a personal prototype: simplest thing that works, nothing to install.
- **Rejected:** a packaged app; direnv; containerizing every app.

## 2026-11-09 Phone access by Tailscale name, no tunnels (PR #4)
- **Decision:** dev servers bind all interfaces (set in each manifest, never in the project) and the phone uses `http://<MagicDNS name>:<port>`.
- **Why:** simplest; no tunnels to run. Vite needs `--host` and an allowed-hosts variable.
