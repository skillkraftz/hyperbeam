# hyperbeam, part 'session': session start/stop, status dots, drift. Runs in the namespace of the `hyperbeam` script (see its loader): no imports of its own.
# ---------- session start / stop ----------
def port_open(port):
    try:
        socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
        return True
    except OSError:
        return False


def listeners(port):
    return run("ss", "-ltnpH", f"sport = :{port}")


def wait_ready(sess, win, svc, port):
    """Wait for a service. ready_port defaults to the project port; `ready_port = false` skips the check;
    with only ready_delay it just sleeps."""
    if "ready_delay" in svc:
        time.sleep(svc["ready_delay"])
    rp = svc.get("ready_port")
    if rp is None and "ready_delay" not in svc:
        rp = port
    if rp is None or rp is False:
        return "started" if "ready_delay" not in svc else f"waited {svc['ready_delay']}s"
    deadline = time.time() + svc.get("ready_timeout", 120)
    while time.time() < deadline:
        if port_open(rp):
            return f"port {rp} open"
        pane = tmux("capture-pane", "-p", "-t", f"{sess}:{win}", check=False).stdout
        if re.search(r"\[hyperbeam\] exited: \d+", pane):
            return f"port {rp} open" if port_open(rp) else f"WARNING exited before port {rp} opened"
        time.sleep(0.5)
    return f"WARNING timeout waiting for port {rp}"


def session_env(man, name=None):
    """Environment of a project's session: HB_PROJECT, PORT and HB_PORT (only if the project has a port), HOST=0.0.0.0, then the
    manifest's [env] table. `man` may be None (no manifest)."""
    man = man or {}
    env = {"HOST": "0.0.0.0"}
    if name:
        env["HB_PROJECT"] = name
    if man.get("port"):
        env["PORT"] = env["HB_PORT"] = str(man["port"])
    env.update({k: str(v) for k, v in man.get("env", {}).items()})
    return env


def manifest_path(man):
    return Path(os.path.expanduser(man["path"]))


def session_exists(sess):
    return tmux("has-session", "-t", f"={sess}", check=False).returncode == 0


def clean_server_env():
    """A tmux server that hyperbeam (run through uv) started before this fix has uv's environment in its global environment,
    and every new session inherits it. Remove it there too."""
    for k in ("VIRTUAL_ENV", "UV", "UV_RUN_RECURSION_DEPTH"):
        tmux("set-environment", "-g", "-u", k, check=False)
    cur = tmux("show-environment", "-g", "PATH", check=False).stdout.strip()
    if cur.startswith("PATH="):
        new = clean_path(cur[5:])
        if new != cur[5:]:
            tmux("set-environment", "-g", "PATH", new, check=False)


# the status segment: red while the session option @hb_alert is set (a red problem), else a quiet yellow one for @hb_note
ALERT = "#{?@hb_alert,#[fg=white]#[bg=red]#[bold] #{@hb_alert} #[default] ,#{?@hb_note,#[fg=black]#[bg=yellow] #{@hb_note} #[default] ,}}"


def tag_session(sess):
    """Mark a session as one of hyperbeam's (the stack keys use the mark) and put the red alert segment and the key hints in its status bar."""
    tmux("set-option", "-t", sess, "@hb", "1")
    base = tmux("show-options", "-gv", "status-right", check=False).stdout.strip()
    tmux("set-option", "-t", sess, "status-right-length", "200")
    tmux("set-option", "-t", sess, "status-right", f"{ALERT}#[fg=#888888]{HINT} #[default]{base}")


def alert_text(findings, notes=()):
    """Status-bar texts: (red text with the command, quiet note text). Each is the first item, how many more."""
    def one(items, prefix, tail=""):
        if not items:
            return ""
        first = clip(items[0].replace("#", ""), 40)
        return f"{prefix}{first}{f' (+{len(items) - 1})' if len(items) > 1 else ''}{tail}"
    return one(findings, "⚠ ", ": kk"), one(notes, "note: ")


def sync_alert(name, findings, notes=()):
    """Set or clear the project's status segments: red for problems, yellow for notes (cheap when nothing changed)."""
    sess = sanitize(name)
    red, note = alert_text(findings, notes)
    cur = tmux("show-options", "-t", sess, "-v", "@hb_alert", check=False)
    if cur.returncode != 0 and not session_exists(sess):
        return
    curn = tmux("show-options", "-t", sess, "-v", "@hb_note", check=False).stdout.strip()
    if cur.stdout.strip() == red and curn == note:
        return
    if (red or note) and "@hb_alert" not in tmux("show-options", "-t", sess, "-v", "status-right", check=False).stdout:
        tag_session(sess)                     # a session made before this version: add the segment
    for opt, text in (("@hb_alert", red), ("@hb_note", note)):
        if text:
            tmux("set-option", "-t", sess, opt, text, check=False)
        else:
            tmux("set-option", "-t", sess, "-u", opt, check=False)
    tmux("refresh-client", "-S", check=False)


def pane_tail(target, n=50):
    out = tmux("capture-pane", "-p", "-J", "-S", "-", "-t", target, check=False).stdout.rstrip().splitlines()
    return "\n".join(out[-n:])


def plans_first():
    """Injected prompts start in plan mode only when the configured model is opusplan (Opus runs only in plan mode there)."""
    return cfg_get("claude_model") == "opusplan"


PLAN_FIRST = ("**Plan mode first.** If plan mode is not active, call EnterPlanMode before anything else: this step is planned by Opus, and nothing is changed "
              "until the user approves your plan.\n\n")


def write_prompt(sess, text, plan=True):
    d = project_dir(session_project(sess)) / "prompts"
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{sess}-{time.strftime('%Y%m%d-%H%M%S')}.md"
    f.write_text((PLAN_FIRST if plan and plans_first() else "") + text)
    f.chmod(0o600)
    return f


def find_claude_pane(sess):
    """The pane for Claude: the one running claude; else the left pane of window `work` in a project session, or the first non-menu pane of
    the hyperbeam session's home window. Never the menu pane: text sent to it would be keystrokes for the menu."""
    rows = [l.split("\t") for l in tmux("list-panes", "-s", "-t", f"={sess}", "-F",
                                        "#{pane_id}\t#{pane_current_command}\t#{window_name}\t#{pane_index}\t#{pane_start_command}",
                                        check=False).stdout.splitlines()]
    if sess == MENU:
        rows = [r for r in rows if r[2] in ("home", "hyperbeam") and "_menu" not in r[4]]      # "hyperbeam" = the window of the old layout
        return next((r[0] for r in rows if r[1] == "claude"), None) or (rows[0][0] if rows else None)
    return (next((r[0] for r in rows if r[1] == "claude"), None)
            or next((r[0] for r in rows if r[2] == "work"), None) or (rows[0][0] if rows else None))


def claude_json_path():
    """The file Claude Code keeps its per-folder trust in: $CLAUDE_CONFIG_DIR/.claude.json if that is set, else ~/.claude.json. Workers and project sessions
    use the same one (hyperbeam sets no config dir of its own)."""
    d = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(d).expanduser() / ".claude.json" if d else Path.home() / ".claude.json"


def trust_folder(path):
    """Set projects["<abs path>"].hasTrustDialogAccepted = true in Claude's config, so a Claude started there (a new project's first session or worker) does not stop at
    "Do you trust the files in this folder?". Only that key, only when it is not already true; written via a temp file + rename with the file's mode. Missing or
    unreadable file, or any error: skip quietly (never breaks work/open). Callers pass folders hyperbeam manages only. Returns True if it wrote."""
    tmp = None
    try:
        f = claude_json_path().resolve()               # a symlinked config stays a symlink: the rename replaces the target
        key = str(Path(path).expanduser().resolve())
        data = json.loads(f.read_text())
        if not isinstance(data, dict) or not isinstance(data.get("projects", {}), dict):
            return False
        if data.get("projects", {}).get(key, {}).get("hasTrustDialogAccepted") is True:
            return False
        data.setdefault("projects", {}).setdefault(key, {})["hasTrustDialogAccepted"] = True
        tmp = f.with_name(f".{f.name}.hb-{os.getpid()}")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)     # the file holds account data: never readable by others, not even briefly
        with os.fdopen(fd, "w") as w:
            w.write(json.dumps(data, indent=2, ensure_ascii=False))
            os.fchmod(w.fileno(), f.stat().st_mode & 0o7777)
        os.replace(tmp, f)
        return True
    except Exception:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        return False


def claude_base(plan=False):
    """Every Claude hyperbeam starts uses the configured model, effort and permissions. plan: it starts in plan mode (injected prompts), but only with the
    opusplan model (plans_first); with permissions "skip" bypass is then only allowed, so approving the plan can switch to it (both flags together would
    leave the mode unclear)."""
    plan = plan and plans_first()
    skip = cfg_get("claude_permissions") == "skip"
    mode = (" --permission-mode plan" + (" --allow-dangerously-skip-permissions" if skip else "")) if plan else (" --dangerously-skip-permissions" if skip else "")
    return f"claude --model {cfg_get('claude_model')} --effort {cfg_get('claude_effort')}{mode}"


def worker_flags():
    """What a worker's Claude does without: MCP servers, plugins (each one enabled in the user's settings is switched off) and skills. They are about 18k tokens of
    start context that every call re-reads, and workers use none of them. Bash, Read, Edit, Write, Glob, Grep and the hooks stay."""
    try:
        plugins = json.loads((Path.home() / ".claude" / "settings.json").read_text()).get("enabledPlugins", {})
    except (OSError, ValueError):
        plugins = {}
    off = json.dumps({"enabledPlugins": {k: False for k in plugins}}, separators=(",", ":"))
    return f" --strict-mcp-config --mcp-config {shlex.quote(json.dumps({"mcpServers": {}}, separators=(",", ":")))} --disable-slash-commands --settings {shlex.quote(off)}"


def claude_cmd(prompt_file=None, cont=False, add_dir=False):
    """Plain `claude`, or claude with an initial prompt read from a file. cont: `claude --continue` (the most recent conversation in this
    directory; it takes a prompt too), falling back to a fresh claude if there is none. The prompt comes first: --add-dir takes a list."""
    p = f' "$(cat {shlex.quote(str(prompt_file))})"' if prompt_file else ""
    tail = f" --add-dir {shlex.quote(str(HERE))}" if add_dir else ""
    fresh = f"{claude_base()}{p}{tail}"
    return f"{claude_base()} --continue{p}{tail} || {fresh}" if cont else fresh


def manager_cmd(cont=False):
    """The manager's Claude: the manager_model, never plan mode, never skip-permissions (the folder's settings deny edits under ~/projects), all of ~/projects readable.
    The role (manager/CLAUDE.md of the running hyperbeam, the installed copy) is read at every start with --append-system-prompt-file, so Merge + update changes it.
    cont: continue the last conversation in ~/manager, a fresh one if there is none."""
    role = shlex.quote(str(HERE / "manager" / "CLAUDE.md"))
    base = f"claude --model {cfg_get('manager_model')} --effort {cfg_get('claude_effort')} --append-system-prompt-file {role}"
    tail = f" --add-dir {shlex.quote(str(ROOT))}"
    return f"{base} --continue{tail} || {base}{tail}" if cont else f"{base}{tail}"


def ensure_manager_dir():
    """~/manager, the manager's notes: a git repo made from the template in the repo (manager/) the first time; files that exist are never overwritten.
    The role (manager/CLAUDE.md) is not copied: it comes from the installed hyperbeam at every start (manager_cmd). Migration: a ~/manager/CLAUDE.md that is a
    full copy of the role (it starts with the role's first line) is removed; one the user wrote is left alone. The notes are never touched."""
    d = MANAGER_DIR
    tpl = HERE / "manager"
    role = tpl / "CLAUDE.md"
    old = d / "CLAUDE.md"
    if old.is_file() and role.is_file() and old.read_text().splitlines()[:1] == role.read_text().splitlines()[:1]:
        old.unlink()
    for src in sorted(tpl.rglob("*")):
        if src == role:
            continue
        dst = d / src.relative_to(tpl)
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        elif not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
    if not (d / ".git").exists():
        run("git", "-C", str(d), "init", "-q")
        run("git", "-C", str(d), "-c", "user.name=manager", "-c", "user.email=manager@localhost", "add", "-A")
        run("git", "-C", str(d), "-c", "user.name=manager", "-c", "user.email=manager@localhost", "commit", "-q", "-m", "The manager's notes: template")
    return d


def pane_command(pane):
    return tmux("display-message", "-p", "-t", pane, "#{pane_current_command}", check=False).stdout.strip()


def inject_prompt(pane, f, add_dirs=()):
    """The one way a prompt file reaches Claude (only after a click: Update). In plan mode when the model is opusplan (plans_first), so Opus makes
    the proposal and Sonnet only builds after the user approves; with any other model it starts normally. Claude already running in the pane: `/plan` plus one line pointing at the file, then Enter.
    Otherwise start `claude --permission-mode plan --continue` with the prompt, falling back to a fresh `claude` if there is no conversation."""
    if pane_command(pane) == "claude":
        send_line(pane, f"{'/plan ' if plans_first() else ''}Read {f} and follow it.")
        return "injected"
    start_claude_with_prompt(pane, f, add_dirs)
    return "started"


def start_claude_with_prompt(pane, f, add_dirs=(), cont=True):
    """Type the command that starts Claude in plan mode with the prompt file as its first message. cont: `claude --continue` (the last conversation of this
    directory), falling back to a fresh one when there is none; otherwise always a fresh Claude."""
    dirs = "".join(f" --add-dir {shlex.quote(str(d))}" for d in add_dirs)
    arg = f' "$(cat {shlex.quote(str(f))})"{dirs}'
    base = claude_base(plan=True)
    send_line(pane, f"{base} --continue{arg} || {base}{arg}" if cont else f"{base}{arg}")


def send_line(target, text):
    tmux("send-keys", "-t", target, "-l", text)
    tmux("send-keys", "-t", target, "Enter")


# ---------- status dots: red (service down, start-check findings, crash), blue (Claude waits for the user), green ----------
def pfile(name, kind):
    """A per-project state file: status.json, claude (the hooks' state), layout.json."""
    return project_dir(name) / kind


def write_status(name, findings, notes=()):
    """findings = the red ones (merge/rebase with conflicts, secrets in commits); notes = the quiet git state (uncommitted, unpushed, ...)."""
    pfile(name, "status.json").write_text(json.dumps({"v": 2, "findings": list(findings), "notes": list(notes), "time": time.time()}))


def read_status(name):
    try:
        d = json.loads(pfile(name, "status.json").read_text())
    except (OSError, ValueError):
        return {}
    return d if d.get("v") == 2 else {}         # an older file mixed notes into the findings: ignore it until the next check


def clear_status(name):
    for k in ("status.json", "claude", "auto"):
        pfile(name, k).unlink(missing_ok=True)


# ---------- drift: has the project's run setup changed since it was onboarded? (no tokens: a fingerprint of the run-defining parts) ----------
def _names(deps):
    """Package names from a list/dict of dependencies (`requests>=2`, `pkg[extra]; python_version<'3'`, or a name -> version table): versions are noise."""
    items = deps.keys() if isinstance(deps, dict) else deps or []
    return sorted({re.split(r"[\s<>=!~;\[(@]", str(i), 1)[0].strip().lower() for i in items if str(i).strip()})


def _compose_parts(text):
    """service names, images and published ports of a compose file, by indentation (no YAML library: this only needs those three things)."""
    out, svc, in_services, in_ports, base = {}, None, False, False, None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        ind = len(line) - len(line.lstrip())
        t = line.strip()
        if ind == 0:
            in_services, svc, in_ports = t == "services:", None, False
            continue
        if not in_services:
            continue
        if base is None:
            base = ind
        if ind == base and t.endswith(":"):
            svc, in_ports = t[:-1].strip("\"'"), False
            out[svc] = {"image": "", "ports": []}
        elif svc and ind > base:
            if t.startswith("image:"):
                out[svc]["image"] = t[6:].strip().strip("\"'")
            elif t == "ports:":
                in_ports = True
            elif in_ports and t.startswith("- "):
                out[svc]["ports"].append(t[2:].strip().strip("\"'"))
            elif not t.startswith("-"):
                in_ports = False
    return {k: {"image": v["image"], "ports": sorted(v["ports"])} for k, v in sorted(out.items())}


def fingerprint(path):
    """{file: parts} for the run-defining files of a project: what a setup change looks like, without the noise (versions, lockfiles, names)."""
    path, out = Path(path), {}

    def add(rel, parts):
        if parts:
            out[rel] = parts
    for f in sorted(path.glob("package.json")):
        try:
            d = json.loads(f.read_text())
            add(f.name, {"scripts": d.get("scripts", {}), "dependencies": _names(d.get("dependencies")), "devDependencies": _names(d.get("devDependencies")),
                         "workspaces": d.get("workspaces", [])})
        except ValueError:
            pass
    for f in sorted([*path.glob("docker-compose*.y*ml"), *path.glob("compose*.y*ml")]):
        add(f.name, {"services": _compose_parts(f.read_text(errors="replace"))})
    pp = path / "pyproject.toml"
    if pp.is_file():
        try:
            d = tomllib.loads(pp.read_text())
            po = d.get("tool", {}).get("poetry", {})
            add(pp.name, {"scripts": {**d.get("project", {}).get("scripts", {}), **po.get("scripts", {})},
                          "dependencies": _names(d.get("project", {}).get("dependencies")) + [f"poetry:{n}" for n in _names(po.get("dependencies"))],
                          "optional": {k: _names(v) for k, v in {**d.get("project", {}).get("optional-dependencies", {}), **d.get("dependency-groups", {})}.items() if isinstance(v, list)}})
        except tomllib.TOMLDecodeError:
            pass
    for f in sorted(path.glob("requirements*.txt")):
        add(f.name, {"dependencies": _names([l for l in f.read_text(errors="replace").splitlines() if l.strip() and not l.lstrip().startswith(("#", "-"))])})
    if (path / "Procfile").is_file():
        add("Procfile", {"processes": sorted(l.strip() for l in (path / "Procfile").read_text(errors="replace").splitlines() if l.strip() and not l.startswith("#"))})
    if (path / "Makefile").is_file():
        add("Makefile", {"targets": sorted({m.group(1) for m in re.finditer(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)\s*:(?!=)", (path / "Makefile").read_text(errors="replace"), re.M)})})
    for n in (".env.example", ".env.sample", ".env.template"):
        if (path / n).is_file():
            add(n, {"variables": sorted({m.group(1) for m in re.finditer(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", (path / n).read_text(errors="replace"), re.M)})})
    if (path / "Cargo.toml").is_file():
        try:
            d = tomllib.loads((path / "Cargo.toml").read_text())
            add("Cargo.toml", {"dependencies": _names(d.get("dependencies")), "dev": _names(d.get("dev-dependencies")), "bins": sorted(b.get("name", "") for b in d.get("bin", []))})
        except tomllib.TOMLDecodeError:
            pass
    return out


def fingerprint_file(name, path):
    return project_dir(name, path) / "fingerprint.json"


def take_fingerprint(name, path):
    """Record the run setup as onboarded now (Onboard/Align wrote or confirmed the manifest, or the user pressed Mark as onboarded)."""
    man = MANIFESTS / f"{name}.toml"
    fingerprint_file(name, path).write_text(json.dumps({"date": time.strftime("%Y-%m-%d %H:%M"), "manifest_mtime": man.stat().st_mtime if man.is_file() else 0,
                                                        "parts": fingerprint(path)}, indent=1))




def drift_notes(name, path):
    """A quiet note when the run-defining files changed since the project was onboarded. Projects with a manifest but no fingerprint get a
    baseline now, without a note; a manifest written since the fingerprint counts as onboarding done (new fingerprint, no note). Never red."""
    man = MANIFESTS / f"{name}.toml"
    if not man.is_file() or not Path(path).is_dir():
        return []
    f = fingerprint_file(name, path)
    try:
        old = json.loads(f.read_text())
    except (OSError, ValueError):
        take_fingerprint(name, path)
        return []
    if man.stat().st_mtime > old.get("manifest_mtime", 0) + 0.5:
        take_fingerprint(name, path)
        return []
    now = fingerprint(path)
    changed = []
    for fn in sorted(set(now) | set(old.get("parts", {}))):
        a, b = old.get("parts", {}).get(fn), now.get(fn)
        if a != b:
            what = sorted(k for k in set(a or {}) | set(b or {}) if (a or {}).get(k) != (b or {}).get(k)) if a and b else ["added" if b else "removed"]
            changed.append(f"{fn} ({', '.join(what)})")
    return [f"setup changed since onboarding: {'; '.join(changed)} (send ONBOARDING.md to update)"] if changed else []


def onboarded_on(name, path):
    try:
        return json.loads(fingerprint_file(name, path).read_text()).get("date", "")
    except (OSError, ValueError):
        return ""

