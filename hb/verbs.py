# hyperbeam, part 'verbs': NAME VERB conventions, usage, shims, hb. Runs in the namespace of the `hyperbeam` script (see its loader): no imports of its own.
# ---------- conventions: the same verbs in every project (install, update, test, version, help, restart) ----------
VERBS = ("install", "update", "test", "version", "help", "restart")
LOCKFILES = ("package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "uv.lock", "pyproject.toml", "requirements.txt", "Cargo.toml", "Cargo.lock")


def detect_pm(path):
    """The project's package manager: pnpm / yarn / npm / uv / pip / cargo, or None."""
    path = Path(path)
    for f, pm in (("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"), ("package-lock.json", "npm"), ("uv.lock", "uv"), ("Cargo.toml", "cargo")):
        if (path / f).exists():
            return pm
    if (path / "package.json").exists():
        return "npm"
    if (path / "pyproject.toml").exists():
        return "uv"
    if (path / "requirements.txt").exists():
        return "pip"
    return None


def _pkg_scripts(path):
    try:
        return json.loads((Path(path) / "package.json").read_text()).get("scripts", {})
    except (OSError, ValueError):
        return {}


def verb_command(name, path, verb):
    """-> (shell command or None, where it comes from). The project's own wins: the manifest's [commands] table, then a package.json script or a Makefile
    target of that name, then a default derived from what is in the folder. None = hyperbeam does it itself (update, version, help, restart)."""
    path = Path(path)
    man = load_manifests().get(name) or {}
    own = (man.get("commands") or {}).get(verb)
    if own:
        return own, "manifest [commands]"
    pm = detect_pm(path)
    scripts = _pkg_scripts(path)
    if verb in scripts and verb not in ("install",):
        return (f"{pm or 'npm'} run {verb}" if pm in ("pnpm", "yarn", "npm", None) else f"npm run {verb}"), f"package.json script {verb}"
    if (path / "Makefile").is_file() and verb in fingerprint(path).get("Makefile", {}).get("targets", []):
        return f"make {verb}", f"Makefile target {verb}"
    if verb == "install":
        cmd = {"pnpm": "pnpm install", "yarn": "yarn install", "npm": "npm install", "uv": "uv sync", "pip": "python3 -m pip install -r requirements.txt", "cargo": "cargo fetch"}.get(pm)
        return cmd, f"default ({pm})" if cmd else "none: no package manager found"
    if verb == "test":
        if "test" in scripts:
            return f"{pm} test", "default (package.json test script)"
        if pm == "uv" or (path / "tests").is_dir():
            return ("uv run pytest -q" if pm == "uv" else "python3 -m pytest -q"), "default (pytest)"
        if pm == "cargo":
            return "cargo test", "default (cargo)"
        return None, "none: no tests found"
    return None, "hyperbeam"


def run_cmd_stream(cmd, cwd, say):
    p = subprocess.Popen(cmd, shell=True, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True, errors="replace")
    for line in p.stdout:
        say(line.rstrip("\n"))
    return p.wait()


def restart_services(name, say):
    """Re-run each service of the manifest in its window of the running session (C-c, then the command again). -> number restarted."""
    man = load_manifests().get(name) or {}
    sess, n = sanitize(name), 0
    if not session_exists(sess):
        return 0
    for svc in man.get("service", []):
        if tmux("list-windows", "-t", f"={sess}", "-F", "#{window_name}", check=False).stdout.split().count(svc["name"]):
            target = f"={sess}:={svc['name']}"
            tmux("send-keys", "-t", target, "C-c", check=False)
            time.sleep(0.8)
            send_line(target, f'{svc["cmd"]}; echo "[hyperbeam] exited: $?"')
            n += 1
    if n:
        say(f"restarted {n} service window{'s' * (n != 1)}")
    return n


def _recorded_commit(name, path):
    """The commit hyperbeam last updated or installed this project at, or None."""
    try:
        c = (project_dir(name, path, create=False) / "updated-commit").read_text().strip()
    except OSError:
        return None
    return c if c and git_out(path, "cat-file", "-t", c) == "commit" else None


def _record_commit(name, path):
    """After a successful update or install: remember the commit the checkout is at."""
    try:
        head = git_out(path, "rev-parse", "HEAD")
        if head:
            (project_dir(name, path) / "updated-commit").write_text(head + "\n")
    except OSError:
        pass


def verb_update(name, path, say, since=None):
    """Pull the project's default branch and bring it up to date: refuse on uncommitted tracked changes; fetch; check out the default branch;
    `pull --ff-only`; changes are measured from the commit hyperbeam last updated/installed (recorded per project), else `since` (the commit before
    Merge pulled), else the HEAD before this pull. If the project has its own `update` (manifest, package.json, Makefile) it runs when anything changed;
    otherwise install runs only if a lockfile changed. Restarts the services of a running session. Says what it did. -> exit code."""
    path = Path(path)
    if name == "hyperbeam":
        return run_cmd_stream(f"{SELF} update --yes", path, say)
    if not (path / ".git").exists():
        say("not a git project: nothing to update")
        return 1
    dirty = git_out(path, "status", "--porcelain", "--untracked-files=no").splitlines()
    if dirty:
        say(f"refused: {len(dirty)} uncommitted change{'s' * (len(dirty) != 1)} ({', '.join(l[3:] for l in dirty[:3])}); commit or stash first")
        return 1
    git_fetch(path)
    base = default_branch(path)
    before_branch, old = branch_of(path), _recorded_commit(name, path) or since or git_out(path, "rev-parse", "HEAD")
    if before_branch != base:
        co = subprocess.run(["git", "-C", str(path), "checkout", "-q", base], capture_output=True, text=True)
        if co.returncode:
            say(f"could not check out {base}: {co.stderr.strip()[:120]}")
            return 1
    pull = subprocess.run(["git", "-C", str(path), "pull", "-q", "--ff-only"], capture_output=True, text=True, timeout=120,
                          env=dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=5"))
    if pull.returncode:
        say(f"pull failed: {pull.stderr.strip()[:160]}")
        return 1
    new = git_out(path, "rev-parse", "HEAD")
    changed = git_out(path, "diff", "--name-only", f"{old}..{new}").splitlines() if old != new else []
    if old == new and before_branch == base:
        say(f"{base} is already up to date")
    else:
        say(f"{base}: {old[:7]} -> {new[:7]} ({len(changed)} file{'s' * (len(changed) != 1)} changed)")
    own, own_src = verb_command(name, path, "update")
    if own and not own_src.startswith(("manifest", "package.json", "Makefile")):
        own = None
    if changed and own:
        say(f"update: {own}   [{own_src}]")
        if run_cmd_stream(own, path, say):
            say(f"the project's own update failed: {own}")
            return 1
    elif changed and not any(Path(f).name in LOCKFILES for f in changed):
        say("no lockfile changed: nothing to install")
    elif changed:
        cmd, src = verb_command(name, path, "install")
        if cmd:
            say(f"dependencies changed: {cmd}")
            if run_cmd_stream(cmd, path, say):
                say("install failed")
                return 1
    if changed:
        if not restart_services(name, say):
            say("no running service windows to restart")
    else:
        say("nothing changed: nothing installed, no services restarted")
    _record_commit(name, path)
    return 0


def verb_version(name, path, say):
    path = Path(path)
    parts = []
    try:
        v = json.loads((path / "package.json").read_text()).get("version")
        if v:
            parts.append(f"package.json {v}")
    except (OSError, ValueError):
        pass
    for fn, keys in (("pyproject.toml", ("project", "version")), ("Cargo.toml", ("package", "version"))):
        try:
            d = tomllib.loads((path / fn).read_text())
            v = d.get(keys[0], {}).get(keys[1])
            if v:
                parts.append(f"{fn} {v}")
        except (OSError, tomllib.TOMLDecodeError):
            pass
    desc = git_out(path, "describe", "--tags", "--always", "--dirty") if (path / ".git").exists() else ""
    when = git_out(path, "log", "-1", "--format=%cs") if desc else ""
    say(f"{name} " + (" / ".join(parts) or "(no version file)") + (f"  git {desc}" if desc else "") + (f"  last commit {when}" if when else ""))
    return 0


def verb_help(name, path, say):
    say(f"{name}: hyperbeam {name} VERB   (hyperbeam {name} alone opens it)")
    for v in VERBS:
        cmd, src = verb_command(name, path, v)
        what = {"update": "pull the default branch, install if dependencies changed (or run its own update), restart services",
                "version": "version, git describe, last commit", "help": "this list",
                "restart": "re-run the project's services in its session"}.get(v)
        say(f"  {v:<8} {cmd if cmd else (what or 'unavailable')}   [{src}]")
    mp = MANIFESTS / f"{name}.toml"
    say(f"  manifest {home_rel(mp) if mp.is_file() else 'none yet (send ONBOARDING.md)'}   data {home_rel(project_dir(name, path))}   (.hyperbeam in the project)")
    return 0


def run_verb(name, verb, path=None, say=print, since=None):
    """One of the standard verbs for a project, with its output through `say`. `test` always runs in the lab. -> exit code."""
    path = Path(path) if path else known_path(name)
    if verb not in VERBS:
        say(f"unknown verb {verb}; verbs: {', '.join(VERBS)}")
        return 2
    if not path.is_dir():
        say(f"{path} does not exist")
        return 1
    if verb == "update":
        return verb_update(name, path, say, since=since)
    if verb == "version":
        return verb_version(name, path, say)
    if verb == "help":
        return verb_help(name, path, say)
    if verb == "restart":
        return 0 if restart_services(name, say) else (say("no running service windows to restart") or 1)
    cmd, src = verb_command(name, path, verb)
    if not cmd:
        say(f"{verb}: {src}")
        return 1
    if verb == "test":
        msg = lab_ready()                      # cmd_lab prints this; inside the menu stdout is Textual's, so say it here
        if msg:
            say(msg)
            return 2
        say(f"test: {cmd}   [{src}]   (in the lab)")
        ns = types.SimpleNamespace(action="run", dir=str(path), name=None, why=f"{name} test", fresh=False, timeout=900, cmd=["--", cmd], quiet=False, collect=None, say=say)
        rc = cmd_lab(ns)
        log = home_rel(project_dir(name, path) / "verb-test.txt")
        say(f"test ok (full output: {log})" if rc == 0 else f"test FAILED (exit {rc}); full output: {log}; hyperbeam lab log has the run")
        return rc
    say(f"{verb}: {cmd}   [{src}]")
    rc = run_cmd_stream(cmd, path, say)
    if verb == "install" and rc == 0 and (path / ".git").exists():
        _record_commit(name, path)
    return rc


def cmd_project_verb(name, verb):
    return run_verb(name, verb, say=print)


def project_exists(name):
    return (MANIFESTS / f"{name}.toml").is_file() or (ROOT / name).is_dir()


def verbs_facts(path, name):
    """For align-facts: which verbs the project provides itself and which hyperbeam only defaults."""
    out = []
    for v in VERBS[:-1]:
        cmd, src = verb_command(name, path, v)
        out.append(f"{v}: {src.split(' (')[0] if src.startswith(('manifest', 'package', 'Makefile')) else 'default only (' + (cmd or src) + ')'}")
    return "; ".join(out)


# ---------- usage: the numbers claude.ai shows (from Claude Code's status line) plus what the local conversation files can honestly tell ----------
RATE_FILE = lambda: DATA_DIR / "rate-limits.json"
STATUSLINE_MARK = "# hyperbeam: rate limits"
STATUSLINE_SNIPPET = STATUSLINE_MARK + r""" (added by `hyperbeam _hooks`: writes the status line's rate_limits to ~/.local/share/hyperbeam/rate-limits.json)
{ d="${XDG_DATA_HOME:-$HOME/.local/share}/hyperbeam"; mkdir -p "$d"; printf '%s' "$input" | jq -c '{at: now, five_hour: .rate_limits.five_hour, seven_day: .rate_limits.seven_day} | select(.five_hour != null or .seven_day != null)' > "$d/.rl.tmp" 2>/dev/null && [ -s "$d/.rl.tmp" ] && mv "$d/.rl.tmp" "$d/rate-limits.json"; } 2>/dev/null
"""


def fmt_tok(n):
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}k" if n >= 1e3 else str(int(n))


def fmt_when(epoch, now=None):
    """A moment in the system's local time zone, 12-hour: `3:02am` today, `Thu 1:00am` within the week, `Nov 20 1:00am` later."""
    now = now or time.time()
    d, n = datetime.datetime.fromtimestamp(epoch), datetime.datetime.fromtimestamp(now)
    clock = d.strftime("%I:%M%p").lstrip("0").lower()
    if d.date() == n.date():
        return clock
    if 0 < (d.date() - n.date()).days < 7:
        return f"{d.strftime('%a')} {clock}"
    return f"{d.strftime('%b')} {d.day} {clock}"


def fmt_left(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 86400}d {seconds % 86400 // 3600}h" if seconds >= 86400 else f"{seconds // 3600}h {seconds % 3600 // 60:02d}m"


def rate_limits():
    """The last rate_limits Claude Code's status line gave, from rate-limits.json: {'at', 'five_hour': {used_percentage, resets_at}, 'seven_day': ...} or None."""
    try:
        d = json.loads(RATE_FILE().read_text())
    except (OSError, ValueError):
        return None
    return d if isinstance(d, dict) and (d.get("five_hour") or d.get("seven_day")) else None


def usage_window_text(w, key, at, now=None, short=False):
    """`5h 83% - resets Thu 1:00am (in 2h 41m)`, `... (as of 9:41pm)` when the data is stale, `... window over` once it has reset."""
    now = now or time.time()
    label = {"five_hour": "5h", "seven_day": "week"}[key]
    if not w:
        return ""
    r = w.get("resets_at") or 0
    if r and r <= now:
        return f"{label} window reset: run a prompt to refresh"
    pct = round(w.get("used_percentage", 0))
    s = f"{label} {pct}% - resets {fmt_when(r, now)}" if r else f"{label} {pct}%"
    if not short and r:
        s += f" (in {fmt_left(r - now)})"
    if at and now - at > 300:
        s += f" (as of {fmt_when(at, now)})"
    return s


def usage_line(short=True):
    """The title-line text: the 5-hour limit as claude.ai shows it. No data yet: says how to get it (never a guess)."""
    rl = rate_limits()
    if not rl or not rl.get("five_hour"):
        return "5h: run any Claude prompt to refresh"
    return usage_window_text(rl["five_hour"], "five_hour", rl.get("at"), short=short)


def install_statusline(settings=None):
    """Make Claude Code's status line script write rate_limits to rate-limits.json: append the marked snippet to the user's statusLine script (backup kept,
    its output unchanged); with no statusLine configured, add a minimal script of ours. Idempotent. -> a message or ''."""
    f = Path(settings or os.environ.get("HB_SETTINGS") or Path.home() / ".claude/settings.json")
    try:
        data = json.loads(f.read_text()) if f.exists() else {}
    except ValueError:
        return "settings.json unreadable"
    cmd = (data.get("statusLine") or {}).get("command", "")
    script = next((Path(os.path.expanduser(t)) for t in shlex.split(cmd) if t.endswith(".sh")), None) if cmd else None
    if script is None:
        script = DATA_DIR / "statusline.sh"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        script.write_text('#!/bin/bash\ninput=$(cat)\nprintf "%s" "$(echo "$input" | jq -r .cwd)"\n')
        script.chmod(0o755)
        data["statusLine"] = {"type": "command", "command": f"bash {script}"}
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(data, indent=2) + "\n")
    if not script.is_file():
        return f"statusLine script {script} not found"
    text = script.read_text()
    if STATUSLINE_MARK in text:
        return ""
    if "input=$(cat)" not in text:
        return f"{home_rel(script)} does not read its input into $input: add `{STATUSLINE_SNIPPET.splitlines()[1][:50]}...` yourself"
    bak = script.with_name(script.name + ".hyperbeam-backup")
    if not bak.exists():
        bak.write_text(text)
    script.write_text(text.rstrip("\n") + "\n" + STATUSLINE_SNIPPET)
    return f"added the rate-limit snippet to {home_rel(script)} (backup {bak.name})"


def conversation_sizes(path_filter=None, within=6 * 3600):
    """The conversations Claude Code wrote to recently: [(project, session id, tokens fed to its last request, requests, mtime)]. The size of a conversation is
    what each new request re-reads: cache read + cache creation + input of its latest request (read from the end of the file)."""
    out, names = [], {}
    now = time.time()
    for f in (CLAUDE_DIR / "projects").glob("*/*.jsonl"):
        try:
            st = f.stat()
            if now - st.st_mtime > within:
                continue
            with f.open("rb") as fh:
                fh.seek(max(0, st.st_size - 400_000))
                tail = fh.read().decode(errors="replace").splitlines()
        except OSError:
            continue
        size = 0
        for line in reversed(tail):
            if '"usage"' not in line:
                continue
            try:
                o = json.loads(line)
            except ValueError:
                continue
            u = (o.get("message") or {}).get("usage")
            if o.get("type") == "assistant" and u and not o.get("isSidechain"):
                size = u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("input_tokens", 0)
                break
        if size:
            folder = f.parent.name
            proj = names.setdefault(folder, usage_project_name(folder))
            out.append((proj, f.stem, size, st.st_mtime))
    return sorted(out, key=lambda r: -r[2])


def usage_project_name(folder):
    """A conversation folder (the project path with every non-alphanumeric as '-') as a project name."""
    try:
        for r in scan():
            if re.sub(r"[^A-Za-z0-9]", "-", str(r["path"])) == folder:
                return r["name"]
    except OSError:
        pass
    if "hyperbeam-work" in folder:
        return "hyperbeam (worktrees)"
    return folder.split("-projects-")[-1] if "-projects-" in folder else folder


def context_note(name, path):
    """A quiet note when the project's active conversation is huge: every request re-reads all of it (the cost driver). '' otherwise."""
    limit = cfg_get("context_warn")
    mine = [r for r in conversation_sizes(within=3 * 3600) if r[0] == name]
    if mine and mine[0][2] >= limit:
        return (f"this conversation re-reads {fmt_tok(mine[0][2])} tokens on every request: finish the task, then start a fresh Claude "
                f"(Copy context carries what matters)")
    return ""


def usage_report(span="today"):
    """The text of `hyperbeam usage`: the limits as Claude reports them, then what the local files say (Claude Code only, not claude.ai)."""
    now = time.time()
    rl = rate_limits()
    L = []
    if rl and rl.get("five_hour"):
        L += [usage_window_text(rl["five_hour"], "five_hour", rl.get("at"), now)]
        if rl.get("seven_day"):
            L += [usage_window_text(rl["seven_day"], "seven_day", rl.get("at"), now)]
        L += ["  (from Claude Code's status line: the same numbers claude.ai shows, web chats included; they update while Claude Code runs)"]
    else:
        L += ["5-hour and weekly limits: not available yet. Run `hyperbeam update` once, then any Claude Code prompt: the status line writes them to "
              + home_rel(RATE_FILE()) + " (Pro/Max only)."]
    since = {"today": now - 24 * 3600, "week": now - 7 * 86400}.get(span, 0.0)
    recs = [r for r in usage_records(since)[0] if r["t"] >= since]
    L += ["", f"Claude Code activity, last {'24 hours' if span == 'today' else '7 days' if span == 'week' else 'all time'} (this machine, Claude Code only: not claude.ai)"]
    by = {}
    for r in recs:
        by.setdefault(r["proj"], []).append(r)
    for proj, rs in sorted(by.items(), key=lambda kv: -len(kv[1]))[:8]:
        q = {k: sum(r[k] for r in rs) for k in ("in", "out", "cc", "cr")}
        L.append(f"  {proj:<24} {len(rs):>5} requests  output {fmt_tok(q['out']):>6}  new context {fmt_tok(q['cc'] + q['in']):>6}  re-read {fmt_tok(q['cr']):>6}")
    if not by:
        L.append("  none")
    big = conversation_sizes(within=24 * 3600)[:4]
    if big:
        L += ["", "conversation sizes (what every new request in that conversation re-reads; this is where tokens go: finish the task, start a fresh Claude)"]
        L += [f"  {pj:<24} {fmt_tok(sz):>6} tokens   last used {fmt_when(mt, now)}" for pj, sid, sz, mt in big]
    return L


def usage_records(since=0.0):
    """(usage records, human prompt times) from ~/.claude/projects/*/*.jsonl modified after `since`. A record: dict(t, model, proj, sid, in, out, cc, cr)."""
    recs, prompts = [], []
    names = {}
    for f in sorted((CLAUDE_DIR / "projects").glob("*/*.jsonl")):
        try:
            if f.stat().st_mtime < since:
                continue
            text = f.read_text(errors="replace")
        except OSError:
            continue
        folder = f.parent.name
        proj = names.setdefault(folder, usage_project_name(folder))
        for line in text.splitlines():
            if '"usage"' not in line and '"user"' not in line:
                continue
            try:
                o = json.loads(line)
            except ValueError:
                continue
            ts = o.get("timestamp")
            if not ts:
                continue
            try:
                t = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
            except ValueError:
                continue
            if o.get("type") == "assistant":
                u = (o.get("message") or {}).get("usage")
                if u:
                    recs.append(dict(t=t, model=(o["message"].get("model") or "?"), proj=proj, sid=f.stem, **{"in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0),
                                     "cc": u.get("cache_creation_input_tokens", 0), "cr": u.get("cache_read_input_tokens", 0)}))
            elif o.get("type") == "user" and is_human_prompt(o):
                prompts.append(t)
    recs.sort(key=lambda r: r["t"])
    return recs, sorted(prompts)


def cmd_usage(a):
    print("\n".join(usage_report("week" if a.week else "all" if a.all else "today")))
    return 0


# ---------- `NAME VERB` inside a project's session: shims on the session PATH, and `hb VERB` for the current project ----------
SHIM_MARK = "# hyperbeam shim"
RESERVED = {"hb", "hyperbeam", "kk", "update", "scan", "open", "stop", "info", "list", "phone", "context", "report", "reports", "copy-last", "verify", "shot", "usage", "lab", "tool", "new",
            "align-facts", "try", "sidebar", "test", "install", "version", "help", "restart"}


def shim_dir():
    return DATA_DIR / "bin"


def install_shims():
    """Write `hb` and one shim per project into ~/.local/share/hyperbeam/bin (first on the PATH of every session hyperbeam starts), so inside the
    dotwork session `dotwork help` and `dotwork update` work. A shim is NOT made when a real command of that name exists (stenographr is an installed
    CLI): `hb VERB` covers it. Stale shims of ours are removed. -> (names with a shim, names left to a real command)."""
    d = shim_dir()
    d.mkdir(parents=True, exist_ok=True)
    names = set(load_manifests())
    if ROOT.is_dir():
        names |= {x.name for x in ROOT.iterdir() if x.is_dir() and not x.name.startswith(".")}
    clean_path = os.pathsep.join(x for x in os.environ.get("PATH", "").split(os.pathsep) if x and Path(x) != d)
    made, real = [], []
    body_hb = (f"#!/bin/sh\n{SHIM_MARK}\n[ -n \"$HB_PROJECT\" ] || {{ echo 'hb: run it inside a hyperbeam project session'; exit 2; }}\n"
               f"if [ $# -eq 0 ]; then set -- help; fi\nexec {SELF} \"$HB_PROJECT\" \"$@\"\n")
    wanted = {"hb": body_hb}
    for n in sorted(names):
        if n in RESERVED or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", n):
            continue
        if shutil.which(n, path=clean_path):
            real.append(n)
            continue
        wanted[n] = f"#!/bin/sh\n{SHIM_MARK}\nif [ $# -eq 0 ]; then set -- help; fi\nexec {SELF} {shlex.quote(n)} \"$@\"\n"
        made.append(n)
    for n, body in wanted.items():
        f = d / n
        if not f.exists() or f.read_text() != body:
            f.write_text(body)
        f.chmod(0o755)
    for f in d.iterdir():
        try:
            if f.name not in wanted and SHIM_MARK in f.read_text():
                f.unlink()
        except (OSError, UnicodeDecodeError):
            pass
    return made, real


def session_path():
    """The PATH of a project session: the shim folder first, then what hyperbeam itself runs with."""
    return f"{shim_dir()}{os.pathsep}{os.environ.get('PATH', '')}"


def verbs_summary(name, path):
    """One line: which standard verbs the project defines itself and which are hyperbeam's defaults."""
    own, default = [], []
    for v in VERBS[:-1]:
        cmd, src = verb_command(name, path, v)
        (own if src.startswith(("manifest", "package.json", "Makefile")) else default).append(v)
    return "verbs: " + (f"own: {', '.join(own)}" if own else "none of its own") + (f"; hyperbeam's: {', '.join(default)}" if default else "")


def hook_summary_for_update():
    msgs = []
    sl = install_statusline()
    if sl:
        msgs.append(sl)
    made, real = install_shims()
    msgs.append(f"session commands: hb + {len(made)} project name{'s' * (len(made) != 1)}" + (f"; left to the real command: {', '.join(real)}" if real else ""))
    return msgs


