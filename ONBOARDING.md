# Onboard a project into hyperbeam

You are running in ~/projects/hyperbeam. The project to onboard is named at the bottom (name and path).
Read CLAUDE.md here first: it defines the manifest format and the rules.

## 1. Read the project (read-only)
Read the project at the given path. Do NOT edit, install, start, build or run anything in it, and do not commit.
Never print the contents of .env files, keys or tokens; only note that such files exist and which variable names are needed.
Work out what it actually needs to run:
- how it is set up and started (package.json scripts, Makefile, README, pyproject, Procfile...), and its test command;
- backing services (docker compose files, Supabase, databases, Caddy, queues) and the ports they use;
- how the app chooses its port (does the dev command read $PORT? is a port hard-coded?);
- anything that must be running first, and in what order.
Also read the other manifests in projects/ and run `ss -ltn` so you know which ports are taken.

## 2. Write projects/<name>.toml
Follow the format in CLAUDE.md. Rules:
- **Docker rule:** app dev servers run on the host, in a tmux window. Backing services (databases, Supabase, Caddy...) run through docker compose (or `supabase start`). Only containerize the app itself if the project specifically requires it, and say why.
- `port`: the next free port from 3100 upward that no other manifest holds and nothing is listening on. The app must listen on it (hyperbeam sets $PORT and $HB_PORT in the session). If the dev command does not read $PORT, put the override in `cmd` (for example `--port $HB_PORT`).
- Services in start order, backing services first. A service's `ready_port` defaults to the project port, so set `ready_port` explicitly for backing services (e.g. a database port), `ready_port = false` for services that open no port, or use `ready_delay`.
- Give every backing service a `stop` command (e.g. `docker compose down`, `supabase stop`). The app's dev server does not need one: Stop kills its tmux session.
- If projects/<name>.toml already exists, read it and change only what is wrong.
- Do not commit anything.

## 3. Reply with
1. What you wrote and why (one line per service, including the port and what you checked).
2. A list "Changes to make in the project to fit hyperbeam" as plain text. Examples: make the dev server read $PORT, add a CLAUDE.md, add a `compose.yml` for the database, document the start order. Do not make these changes yourself.
3. Anything you could not determine.
