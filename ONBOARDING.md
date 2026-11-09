# Investigate a project for hyperbeam

You are Claude Code, running in the project's directory, in the `claude` window of the project's tmux session.
hyperbeam started you because the project has no manifest, because starting it failed, or because the user pressed Onboard.
The facts (project name, manifest, session, what failed with the last lines of the failing window) are at the bottom.
Read CLAUDE.md in ~/projects/hyperbeam first: it defines the manifest format, the Docker rule and the Tailscale notes.

Rules: never print the contents of .env files, keys or tokens (say only that such a file exists and which variable names it needs).
Do not commit anything, in the project or in hyperbeam.

## 1. Read the project
How it is set up and started (package.json scripts, Makefile, README, pyproject, Procfile...), its test command, backing services
(docker compose files, Supabase, databases, Caddy, queues) and their ports, how the app chooses its port (does the dev command read
$PORT? is one hard-coded?), and what must run first. Read the other manifests in ~/projects/hyperbeam/projects/ and run `ss -ltn`
so you know which ports are taken.

## 2. Install, start, test
- Install dependencies with the project's own package manager. (pnpm installs by itself on `pnpm dev`; that also modifies node_modules.)
- Start the project and check that it really runs, following the Docker rule in CLAUDE.md: the app's dev server runs on the host in a
  tmux window of this session (`tmux new-window -d -t "$(tmux display-message -p '#S'):" -n dev -c "$PWD" '<cmd>'`), backing
  services run through docker compose (or `supabase start`). Containerize the app itself only if the project requires it, and say why.
- Does the project serve anything? If it is a CLI, a library or a batch job with no server, give the manifest **no `port`** (and no
  service that needs one): do not reserve a port for it. hyperbeam then sets no PORT/HB_PORT in its session.
- If it does serve something: use a free port from 3100 upward that no manifest holds and nothing listens on; set PORT and HB_PORT
  to it for the commands you start. If the dev command ignores $PORT, put the override in the command (for example `--port $HB_PORT`)
  and bind all interfaces as CLAUDE.md says.
- Check it: curl the port, run the test command, read the window output. If the status below lists a failure, find its cause first.
- Leave what you started running if it works; stop what does not.

## 3. Propose the manifest, then wait
Show the user the full `projects/<name>.toml` you propose (format in CLAUDE.md: `port` only if something serves, ordered services, `ready_port`, `stop` for every backing
service, `[env]` if needed; no URLs: `kk` discovers links itself, `[links]` is only for extras it cannot find) with one line per service saying what you checked. **Then stop and wait for the user to approve.**
Only after approval write it to the manifest path given below in ~/projects/hyperbeam (this directory is added to your session).
If a manifest already exists, change only what is wrong.

## 4. Reply with
1. What you wrote (or propose) and why.
2. A list "Changes to make in the project to fit hyperbeam" as plain text (make the dev server read $PORT, add a CLAUDE.md, add a
   `compose.yml`, document the start order...). Do not edit the project's source files yourself.
3. Anything you could not determine or could not get running.
