# How hyperbeam works (the map)

One page. Details: `docs/REFERENCE.md`; the why: `docs/decisions/`; the UI constraints: `docs/UI.md`.
Two things share the name: **the tool** (the installed copy at `~/.local/lib/hyperbeam`, which runs everything; nobody edits it) and **the project** (`~/projects/hyperbeam`, changed on branches like any other project; a change reaches the tool by Merge).

```
 HOTKEY ─> sidebar window (kitty: menu left | tmux right)
            ├─ manager row (always first) = tmux session "manager": Opus, a conversation about all projects
            └─ project row ── Open ─> session: saved layout, services in order, start check, Claude continues
                                         WORK: you + Claude on a branch -> PR (every test runs in the lab, the guard watches)
                                         Merge: every open PR, oldest first -> the project's `update` runs
                                         Stop / Done: wrap-up check, then the sessions stop
```

## The pieces
- **Manager.** The first row, session `manager`: Claude on Opus, a conversation, read-only on the projects. Its role ships with hyperbeam (`manager/CLAUDE.md`, read from the installed copy at every start); its notes live in `~/manager`. It plans with the user and, after a yes, sends work. hyperbeam never starts Claude work by itself.
- **Workers and reports.** `hyperbeam work NAME FILE` starts a fresh Claude (tmux session `claude-NAME`, WORKER.md plus the task as its first message, no services); `wait NAME` returns with the path of its report; `close NAME` ends it. Onboarding (ONBOARDING.md) and aligning (ALIGN.md) are worker tasks like any other. A Claude that stops writes a report to the project's data folder.
- **Sessions and services.** One tmux session per project, window `work` (Claude left, shell right) plus one window per service from the manifest (`projects/<name>.toml`, in this repo), started in order, each waiting for the previous one's port. Open attaches if the session runs; otherwise it restores the saved layout (panes and their programs come back), starts the services, runs the start check (git state, drift, a crash: notes, nothing sent to Claude) and types `claude --continue || claude`. Dots: green running, blue waiting for you, cyan working, red only for something real (a service down, secrets in unpushed commits, a conflicted merge); everything else is a quiet note. Layouts are saved on detach, on Stop and every 5 minutes.
- **Lab.** A separate Linux user `hblab` with its own disk image at `/srv/hblab`, where every test and risky command runs (`hyperbeam lab run`), so nothing can signal your sessions. Own tmux server and display per run, ports in a reserved range, runs logged to `lab-runs.jsonl`; the digest turns repeated work into `tools/`. The setup is the user's: agents never run it.
- **Verbs.** `hyperbeam NAME install|update|test|version|help|restart` works in every project (the project's own script, Makefile target or manifest `[commands]`, else a default from the lockfile). `test` always runs in the lab. `kk` (`hyperbeam info`) lists a project's URLs.
- **Merge.** One button: every open PR of the project, oldest first; it checks each against main (behind, overlapping files, conflicts), hands a conflict to Claude and stops, then runs the project's `update` (for hyperbeam itself: the installed copy).
- **Guard.** A PreToolUse hook (`guard.py`) refuses dangerous shell commands in Claude sessions inside hyperbeam: tmux kills on the real server, `kill`/`pkill`, GUI apps with a display set, the lab's setup, `sudo`, running a dev folder's `hyperbeam` as the user. Textual: a command that only mentions a blocked word is blocked too.
- **Sidebar.** The Textual menu (35 columns on the laptop, about 42 on the phone, mouse first): rows with dot, branch and port; buttons Open, Stop, Done, Update, Merge, More (the Project screen); a usage line on top. Phone over SSH attaches to the same tmux sessions.
- **Memory.** The repo is the memory: CLAUDE.md says how a project works now, `docs/decisions/` has one file per decision, RULES.md is what every project follows, IDEAS.md is the roadmap.

## Where state lives
| What | Where |
|---|---|
| Settings | `~/.config/hyperbeam/config.toml` over `config.default.toml` |
| Per project | `~/.local/share/hyperbeam/projects/<name>-<hash>/` (linked into the project as `.hyperbeam`): layout, status, notes, reports, prs.json, fingerprint |
| Global | same root: `journal.json` (what Done checks), `state.json` (last opened), `rate-limits.json`, `lab-runs.jsonl`, `outbox/` |
| Manifests | `projects/<name>.toml` in the repo (the installed copy is on main) |
| Claude's own | `~/.claude/` (hooks in settings.json, conversations) |
