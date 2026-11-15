# How hyperbeam works, in enough detail to check the design

Written to be read, not skimmed. `docs/SYSTEM.md` is the one-page map; this is the walk through it. `docs/REFERENCE.md` has every detail and flag, `docs/decisions/` the reasons.
It describes the system with PRs #52 (the start/end choice of a piece of work) and #53 (the lab refuses nesting) merged.
Wherever the design may not be what you meant, it says **[check]**. The last section lists them all.

## 1. A day in the life
What happens, in order, and what does it. Names in `code` are what to search for in the `hyperbeam` script.

1. **You press the hotkey.** `hyperbeam` opens one kitty window split in two: the menu on the left (`Menu`, a Textual app, always running), a tmux client on the right. Pressing it again says it is already open. (`launch_sidebar`)
2. **The `hyperbeam` session is there.** It is the first row and the "home" of the right side: window `home` (Claude in `~/projects/hyperbeam`, shells) and window `menu`. After a reboot it is rebuilt from its saved layout, panes and the programs that ran in them included; Claude continues the last conversation **[check: it does not ask yet; planned]**. (`ensure_menu`, `restore_layout`)
3. **You double-click a project.** Open (`open_project`) does, in order: link the project's data folder as `.hyperbeam`; if the session is not running, the start check (git state, drift, a crash: findings and notes only); then the session: tmux session `name` with window `work` (Claude left, shell right), one window per service from the manifest, started in order, each waiting for the previous one to be ready. A saved layout comes back without asking.
4. **Claude starts.** Always plain: Claude continues its last conversation in the folder (`--continue`, a fresh one if there is none). Nothing is asked. (`start_session`, `claude_cmd`)
5. **You work.** You and Claude talk; Claude plans (Opus), builds (Sonnet), works on a branch, runs all tests in the lab, opens a PR. The row's dot shows what Claude is doing: cyan working, blue waiting for you, green running, red only for something real. Claude's every shell command first passes the guard.
6. **PRs appear.** After any `gh pr create|merge|close` a hook refreshes the PR list; the row turns magenta and a **Merge** button appears.
7. **You press Merge.** All of your open PRs of that project, oldest first, one confirmation. Before each: is it behind main, did main change the same files, would it conflict? No overlap merges at once; overlap asks (Claude updates and re-tests, or merge anyway); a conflict is handed to Claude to rebase and the run stops. After the last merge the project's own `update` runs (install, restart services). For hyperbeam itself the installed copy is updated. (`_merge_all`, `_merge_one`, `pr_state`, `merge_pr`)
8. **The piece of work ends.** A Merge run ends at its summary and the project's update. Nothing is asked: the manager plans the next piece of work.
9. **You stop for now.** Stop (one project) and Done (the day) run the wrap-up check: uncommitted or unpushed work, stashes, secrets in changes, steno files. Clean: sessions stop. Not clean: it says what is unclean and stops nothing (Stop in the menu may stop anyway; `hyperbeam stop` refuses without `--force`). Layouts are saved on Stop and every 5 minutes. (`wrapup_check`, `_done`)

## 2. Words used here
- **Project**: a folder in `~/projects`. **Manifest**: `projects/<name>.toml` in hyperbeam's own repo, saying how the project starts (services, port, env). Never inside the project.
- **Session / window / pane**: tmux's three levels. One session per project; a window per service plus `work`; panes are the split areas (Claude, shell).
- **Sidebar**: the kitty window; **menu**: the Textual app on its left; **right side**: the tmux client that shows the selected session.
- **`.hyperbeam`**: a link inside each project to its data folder `~/.local/share/hyperbeam/projects/<name>-<hash>/` (status, layout, notes, prompts). Not in git.
- **Fingerprint**: a snapshot of the parts of a project that define how it runs (scripts, dependency names, compose files...), taken when it was onboarded. A change later is the "setup changed" note (**drift**).
- **Sonnet by default, planning in the manager**: project Claudes run on Sonnet; the plan is made in the manager conversation (Opus). With the `opusplan` setting every prompt hyperbeam injects starts in plan mode. Workers: the manager starts, waits for and closes a Claude per project (`work`, `wait`, `close`).
- **Lab**: a separate Linux user `hblab` with its own disk image, where every test and risky command runs, so nothing can touch your live sessions. **Run**: one `hyperbeam lab run`.
- **Guard**: a hook that looks at every shell command Claude is about to run in a hyperbeam session and refuses the dangerous ones.
- **Decision record**: `docs/decisions/<date>-<slug>.md`, one file per decision (Decision / Why / Rejected); newer ones can supersede older ones. Old review records stay in `docs/reviews/` as history.
- **Tool**: a small tested script in `tools/`, built when the lab digest shows the same lab work repeated.

## 3. The parts

### 3.1 The sidebar and the sessions
- *What:* the menu lists every project, with a dot, branch, port. Selecting and opening switches the right side to that project's tmux session. Sessions are real tmux, so the phone can attach over SSH to the same ones.
- *Why:* one place to see everything and one habit (open, work, merge, done), the same for every project.
- *How:* the menu polls: running sessions every 3 s, status every 5 s, PRs every 60 s (cache read every 5 s), a recheck of notes every minute, the repo for "behind" every 10 min. A layout save every 5 min and when you leave a session.
- *Can go wrong:* a stopped project's right side closes unless it is moved to the hyperbeam session first (done, PR #45). A half-open window is closed and reopened by the hotkey.
- *Code:* `Menu`, `launch_sidebar`, `show_session`, `save_all`, `snapshot`, `restore_layout`, `hyperbeam.conf` (tmux keys and hooks).

### 3.2 Open and how Claude starts
```
Open ─ running? ──yes──> just show it
          │no
   start check (git, drift, crash) ──> findings and notes only
          │
   session: saved layout restored (panes, programs), services in order
          │
   Claude: always claude --continue (fresh if none); a failed service = red dot + a note
```
- *Why:* the manager decides when work is done and starts workers fresh; Open only has to get back to where the user was.
- *Can go wrong:* a service that fails does not change what Claude does, only the dot and a note; a very long conversation keeps growing (the context size note warns).
- *Code:* `open_project`, `start_session`, `claude_cmd`, `inject_prompt`.

### 3.3 Claude's state: dots and hooks
- *What:* hooks in `~/.claude/settings.json` write `working` / `waiting` into the project's data folder on Claude's own events; the menu turns that into cyan / blue. Green means the services are up. Red is rare on purpose: a service down, secrets in unpushed commits, a stuck merge with conflicts. Everything else (uncommitted work, behind, drift, stale docs, review due) is a quiet note, never a red dot.
- *Why:* one glance shows which project needs you, without noise.
- *Can go wrong:* a Claude that started before the hooks were installed needs a restart.
- *Code:* `_hooks`, `claude_state`, `recheck`, `write_status`, `git_red_notes`, `drift_notes`, `stale_doc_notes`.

### 3.4 Merge, and the end of a piece of work
```
Merge ─ confirm ─> for each open PR, oldest first:
                     behind? overlap? conflict?
                     none ─> merge        overlap ─> ask (update+retest / merge anyway)
                                          conflict ─> Claude rebases, run stops
        after the last merge: project `update` (hyperbeam: installed copy updates)
```
- *Why:* one click ships work and keeps the installed copy current; the check against main exists because the PR's tests ran without what main gained.
- *Can go wrong:* GitHub lags a few seconds listing a just-merged PR (handled by dropping it from the list). A fork or offline state merges without the check and says so.
- *Code:* `_merge_all`, `_merge_one`, `pr_state`, `merge_pr`, `refresh-prs` and the `pr-refresh` hook.

### 3.5 Onboarding and aligning
- *What:* the manager sends ONBOARDING.md as a worker task (after your yes): it reads the project, starts it and commits the manifest; ALIGN.md, another task, compares the project's CLAUDE.md, README and docs with RULES.md and opens a PR to bring it in line. Projects follow the system; differences are allowed only where the project's CLAUDE.md lists them as approved exceptions. Manifests are committed straight to hyperbeam's main; everything else goes through a branch and PR.
- *Why:* every project then has the same verbs (`install`, `update`, `test`, `version`, `help`, `restart`), the same rules and the same memory layout.
- *Code:* `align_facts`, `fingerprint`, `take_fingerprint`, ONBOARDING.md, ALIGN.md, RULES.md, `VERBS`, `verb_command`.

### 3.6 The lab
- *What:* `hyperbeam lab run` copies the project (no secrets, no `.git`) to `/srv/hblab` and runs the command there as the user `hblab`, which cannot signal your processes. Own tmux server and display per run, ports in a reserved range, logs in `lab-runs.jsonl`. `NAME test`, `tool` and `shot` use it by themselves. Inside the lab (`HB_LAB=1`) any lab command refuses at once and says why; nothing needs changing.
- *Why:* agents testing on your machine once took down every session. A different uid makes that impossible rather than discouraged.
- *The lab's setup (`lab/setup.sh` and friends) is yours;* agents never run it or suggest it because of an error.
- *Code:* `cmd_lab`, `lab_ready`, `LAB_NESTED`, `lab_runs`, `lab_digest`, `lab/`.

### 3.7 The guard
- *What:* a `PreToolUse` hook on the shell tool, in `guard.py`, run before every command of a Claude started inside hyperbeam. It refuses: tmux kill commands aimed at the real server, `kill`/`pkill`/`killall` outside the lab, GUI apps while a display variable is set, `lab reset`, `git worktree remove --force`, deleting a dirty worktree, the lab's setup scripts, any `sudo` but `sudo -n -l`, and running a dev folder's `hyperbeam` script as you. A refusal comes with what to do instead.
- *How:* it **searches the command text**, so a command that only mentions a blocked word is blocked too (write such text with the Write tool and pass `--body-file`). Lab nesting is no longer judged here: the lab refuses it (#53).
- *Why:* CLAUDE.md text did not stop a `tmux kill-server`; a hook does.
- *Can go wrong:* false blocks on text. **[check: the rules are stacked in four layers and parse commands in five ways; an audit would look at it]**
- *Code:* `guard.py` (`RULES`, `check`, `parse`, `head`), installed by `hyperbeam _hooks` into `~/.claude/settings.json`.

### 3.8 Where state lives
| What | Where |
|---|---|
| Settings | `~/.config/hyperbeam/config.toml` (laid over `config.default.toml`) |
| Per-project data | `~/.local/share/hyperbeam/projects/<name>-<hash>/`: `layout.json`, `status.json`, `claude` (hook state), `fingerprint.json`, `prs.json`, `prompts/`, `notes/` |
| Global data | same folder: `journal.json` (what Done checks), `state.json`, `daily.json` (offers once a day), `lab-runs.jsonl`, `rate-limits.json`, `menus/` (pids) |
| Manifests | `projects/<name>.toml` in the repo |
| The app itself | `~/.local/lib/hyperbeam` (installed copy, always on main); development in `~/projects/hyperbeam` on branches |
| Claude's own files | `~/.claude/` (settings with hooks, conversations under `projects/<folder>/`) |

### 3.9 The memory: docs and decisions
- *What:* each project's CLAUDE.md says how it works now and is changed in the same PR as the behaviour; every design decision is its own file with a status; superseded ones point to what absorbed them. `docs/DECISIONS.md` is a generated index, regenerated only by reviews. README says why and what to use; IDEAS.md holds Open and Done; review records say when code was last cleaned.
- *Why:* chat history is lost; the repo is the memory a fresh Claude starts from.
- *Can go wrong:* the same thing described in several places drifts. **[check: README, CLAUDE.md, REFERENCE.md, SYSTEM.md and this file overlap; an audit decides what is kept where]**
- *Code:* `context_bundle`, `hyperbeam context`, `tools/decisions`, `stale_doc_items`.

### 3.10 Done, Stop and the digest
- *What:* **Stop** checks one project and stops it. **Done** works through everything touched today: the wrap-up check on every project; clean ones are stopped, others are listed and nothing is stopped. Done never stops a Claude that is working or waiting for you.
- *Code:* `_done`, `wrapup_check`, `stop_project`, `lab_digest`.

## 4. Where this may not be what you meant
1. Nothing ends a conversation any more: the manager decides when work is done and starts workers fresh. **[check]**
2. The hyperbeam session continues silently after a reboot; every project asks. **[check: planned]**
3. Open continues the last conversation without asking; a fresh one is the user's to start (`/clear` in Claude, or a worker).
4. Layouts always restore; a pane's program is typed again (not `sudo`, not a shell, not Claude). A program with side effects would run again. **[check]**
5. Red is rare, notes are quiet. Is anything quiet that should be loud? **[check]**
6. The guard's remaining rules are cautious text matches..

## 5. Known overlaps
Seeds for an audit (the manager asks for one as a worker task): the guard's stacked rules and parsers, the process-stopping checks in three places, `ask`/`choose` helpers and the two modals, a large script, and five documents describing the same system.
