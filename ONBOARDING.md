# Investigate a project for hyperbeam

This is a worker task: the manager sends it with `hyperbeam work NAME ~/.local/lib/hyperbeam/ONBOARDING.md`, after the user said yes. hyperbeam never sends it by itself.
You run in the project's directory. The project's name is the folder name; its manifest is `~/projects/hyperbeam/projects/<name>.toml` (it may not exist yet).
The tmux session of this worker is `claude-<name>`: start what you need in new windows of it.
Read docs/REFERENCE.md in ~/projects/hyperbeam first (the sections "Manifest format" and "Reachable over Tailscale"): it defines the manifest format, the Docker rule and the Tailscale notes.

Rules: never print the contents of .env files, keys or tokens (say only that such a file exists and which variable names it needs).
Do not commit anything in the project. The one exception is the manifest in hyperbeam (step 3).
**Steno files:** `steno-YYYY-MM-DD.txt` files whose first line starts with `stenographr` are the user's personal dictation notes, not project files.
Never read them for the project, never `git add` them, never commit them. If one is not covered by .gitignore, list "add `steno-*.txt` to .gitignore"
among the project changes you recommend.

## 1. Read the project
How it is set up and started (package.json scripts, Makefile, README, pyproject, Procfile...), its test command, backing services
(docker compose files, Supabase, databases, Caddy, queues) and their ports, how the app chooses its port (does the dev command read
$PORT? is one hard-coded?), and what must run first. Read the other manifests in ~/projects/hyperbeam/projects/ and run `ss -ltn`
so you know which ports are taken.

## 2. Install, start, test
- Install dependencies with the project's own package manager. (pnpm installs by itself on `pnpm dev`; that also modifies node_modules.)
- Start the project and check that it really runs, following the Docker rule in docs/REFERENCE.md (Manifest format): the app's dev server runs on the host in a
  tmux window of this session (`tmux new-window -d -t "$(tmux display-message -p '#S'):" -n dev -c "$PWD" '<cmd>'`), backing
  services run through docker compose (or `supabase start`). Containerize the app itself only if the project requires it, and say why.
- Does the project serve anything? If it is a CLI, a library or a batch job with no server, give the manifest **no `port`** (and no
  service that needs one): do not reserve a port for it. hyperbeam then sets no PORT/HB_PORT in its session.
- If it does serve something: use a free port from 3100 upward that no manifest holds and nothing listens on; set PORT and HB_PORT
  to it for the commands you start. If the dev command ignores $PORT, put the override in the command (for example `--port $HB_PORT`)
  and bind all interfaces as docs/REFERENCE.md says (Reachable over Tailscale).
- Check it: curl the port, run the test command, read the window output. If a service fails, find its cause first.
- Leave what you started running if it works; stop what does not.

## 3. Write the manifest
Write `projects/<name>.toml` (format in docs/REFERENCE.md: `port` only if something serves, ordered services, `ready_port`, `stop` for every backing
service, `[env]` if needed; no URLs: `kk` discovers links itself, `[links]` is only for extras it cannot find), with one line per service in your report saying what you checked, and
**commit it straight to hyperbeam's main and push**, no branch and no PR: `git add projects/<name>.toml` (only that file), commit with a message such as
"Add <name> manifest", `git push origin main`. If ~/projects/hyperbeam is not on main or has other uncommitted work, do not switch branches: write the file,
stop and say so in your report.
If a manifest already exists, change only what is wrong and commit it the same way.

## 4. Reply with
1. What you wrote (or propose) and why.
2. A list "Changes to make in the project to fit hyperbeam" as plain text (make the dev server read $PORT, add a CLAUDE.md, add a
   `compose.yml`, document the start order...). Do not edit the project's source files yourself.
3. Anything you could not determine or could not get running.

If the project needs a non-default way to install, update, test or restart (the defaults come from its lockfile), add a `[commands]` table to the manifest (`install = "..."`, `update = "..."`, `test = "..."`); `hyperbeam NAME help` shows what each verb will run.

## 5. Aligning is a separate task
Do not align the project here. If it needs it, say so in your report: the manager sends ALIGN.md as its own task (`hyperbeam work NAME ~/.local/lib/hyperbeam/ALIGN.md`).
