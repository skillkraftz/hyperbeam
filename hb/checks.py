# hyperbeam, part 'checks': stale docs, layouts, start check, wrap-up check. Runs in the namespace of the `hyperbeam` script (see its loader): no imports of its own.
# ---------- stale docs: do README.md / CLAUDE.md still match the project? (no tokens: three cheap checks) ----------
DOC_FILES = ("README.md", "CLAUDE.md")
GENERATED = ("node_modules", "dist", "build", ".venv", "venv", ".hyperbeam", ".next", "target", "__pycache__", ".git", "coverage")
PM_BUILTINS = {"install", "i", "ci", "add", "remove", "rm", "update", "up", "upgrade", "exec", "dlx", "create", "init", "publish", "link", "unlink", "import",
               "test", "start", "run", "store", "patch", "outdated", "audit", "why", "list", "ls", "env", "config", "setup", "self-update", "help", "version", "x", "cache",
               "login", "logout", "pack", "prune", "rebuild", "restart", "stop", "view", "info", "fund", "doctor", "explain", "set", "get"}
CMD_RE = re.compile(r"(?:^|[\s;&|(])(?:(?:npm|pnpm|yarn|bun)\s+run\s+([A-Za-z0-9:_.-]+)|(?:pnpm|yarn)\s+([A-Za-z][A-Za-z0-9:_-]*)|make\s+([A-Za-z][A-Za-z0-9_.-]*))")
PATH_RE = re.compile(r"^(?:\./)?[A-Za-z0-9_][A-Za-z0-9_.@-]*(?:/[A-Za-z0-9_.@-]+)*/?$")
DOC_EXT = (".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".toml", ".json", ".md", ".sh", ".yml", ".yaml", ".css", ".html")
STALE_AGE_COMMITS = 5


def stale_doc_items(path):
    """[(doc, what)] for README.md and CLAUDE.md: commands they tell you to run that don't exist (`npm run X`, `pnpm X`, `make X`: X is not a script
    or target), relative paths in backticks that aren't in the repo, and docs that were last updated 5+ commits (touching package.json, compose files,
    pyproject, Makefile... the run-defining files) ago. Needs a git repo; nothing for a doc that isn't there."""
    path = Path(path)
    if not (path / ".git").exists():
        return []
    docs = [d for d in DOC_FILES if (path / d).is_file()]
    if not docs:
        return []
    fp = fingerprint(path)
    scripts = set(fp.get("package.json", {}).get("scripts", {}))
    targets = set(fp.get("Makefile", {}).get("targets", []))
    tracked = set(git_out(path, "ls-files").splitlines())
    items = []
    for d in docs:
        text = (path / d).read_text(errors="replace")
        fenced = re.findall(r"```[^\n]*\n(.*?)```", text, re.S)
        inline = re.findall(r"`([^`\n]+)`", re.sub(r"```.*?```", "", text, flags=re.S))
        seen = set()
        for snippet in [*inline, *[l for blk in fenced for l in blk.splitlines()]]:
            for m in CMD_RE.finditer(snippet):
                run_name, pm_name, make_name = m.groups()
                if run_name and "package.json" in fp and run_name not in scripts:
                    what = f"'{snippet.strip()[:40]}' (no script {run_name})"
                elif pm_name and "package.json" in fp and pm_name not in PM_BUILTINS and pm_name not in scripts:
                    what = f"'{snippet.strip()[:40]}' (no script {pm_name})"
                elif make_name and "Makefile" in fp and make_name not in targets:
                    what = f"'make {make_name}' (no such target)"
                else:
                    continue
                if what not in seen:
                    seen.add(what)
                    items.append((d, f"mentions {what}"))
        for sp in inline:
            sp = sp.strip()
            if not PATH_RE.match(sp) or sp.startswith(("/", "~")) or sp.split("/")[0] in GENERATED or sp in seen:
                continue
            if "/" not in sp and not sp.lower().endswith(DOC_EXT):
                continue
            if sp.startswith(".") and "/" not in sp:
                continue
            q = sp[2:] if sp.startswith("./") else sp
            if q in tracked or any(f.startswith(q.rstrip("/") + "/") for f in tracked) or (path / q).exists():
                continue
            seen.add(sp)
            items.append((d, f"names {sp} (missing)"))
    files = [f for f in fp if (path / f).exists()]
    for d in docs:
        last = git_out(path, "log", "-1", "--format=%H", "--", d)
        if last and files:
            n = git_out(path, "rev-list", "--count", f"{last}..HEAD", "--", *files)
            if n.isdigit() and int(n) >= STALE_AGE_COMMITS:
                items.append((d, f"was last updated {n} commits that changed how the project runs ago"))
    return items


def stale_doc_notes(name, path):
    """One quiet note (the first three findings) when the docs look stale; [] otherwise. Never red."""
    try:
        items = stale_doc_items(path)
    except (OSError, subprocess.SubprocessError):
        return []
    if not items:
        return []
    shown = "; ".join(f"{d} {w}" for d, w in items[:3]) + (f" (+{len(items) - 3} more)" if len(items) > 3 else "")
    return [f"docs may be stale: {shown} (send ALIGN.md as a worker task)"]


def write_wrapup_note(name, r):
    """A wrap-up check that found something is kept as <project data>/notes/YYYY-MM-DD-wrapup.md (overwritten the same day): the findings, with
    secrets as file, line and pattern only. A clean check writes nothing. -> the file or None."""
    if wrapup_clean(r):
        return None
    try:
        d = project_dir(name, r["path"]) / "notes"
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"{time.strftime('%Y-%m-%d')}-wrapup.md"
        L = [f"# Wrap-up notes for {name}, {time.strftime('%Y-%m-%d %H:%M')}", "", f"branch: {branch_of(r['path'])}", ""]
        for title, key in (("git", "git"), ("steno files (personal notes: never commit)", "steno"), ("secrets (file, line, pattern; never values)", "secrets")):
            if r.get(key):
                L += [f"## {title}"] + [f"- {x}" for x in r[key]] + [""]
        f.write_text("\n".join(L))
        return f
    except OSError:
        return None


def recheck(name, path):
    """Refresh: run the git checks again and store the result, so a red dot clears when the problem is gone."""
    red, notes = git_red_notes(path, fetch=False, behind=False)
    cn = context_note(name, path) if session_exists(sanitize(name)) else ""
    tn = tool_check_findings() if name == "hyperbeam" else []                          # a failing tool test is a quiet note, never a dot
    write_status(name, red, [*tn, *drift_notes(name, path), *([cn] if cn else []), *stale_doc_notes(name, path), *notes])        # the setup note first: it is the one with a fix, and the status segment shows the first


def claude_state(name):
    """('waiting', reason) / ('working', '') from the hooks' state file; ('', '') if none or if no Claude runs in the session any more."""
    try:
        txt = pfile(name, "claude").read_text().strip()
    except OSError:
        return "", ""
    pane = find_claude_pane(sanitize(name))
    if not pane or pane_command(pane) != "claude":
        return "", ""
    kind, _, reason = txt.partition(" ")
    return (kind, reason) if kind in ("waiting", "working") else ("", "")


def note_findings(name):
    """The quiet notes of a project (stored by the start check / Refresh / the menu's minute check). They never change the dot."""
    return read_status(name).get("notes", [])


def red_findings(name, man):
    """Why a running project is red, as separate sentences: services down or exited, and the stored start-check/recheck problems."""
    sess = sanitize(name)
    return [f"service {n} {st} ({d})" for n, st, d in service_states(sess, man, {}) if st in ("down", "exited")] + read_status(name).get("findings", [])


def cmd_entered(a):
    """tmux hook (client-attached, client-session-changed): a client entered a session: the status segment is refreshed. Nothing else (no popup, no prompt)."""
    sess = a.session
    if tmux("show-options", "-t", sess, "-v", "@hb", check=False).stdout.strip() != "1":
        return 0
    name = session_project(sess)
    sync_alert(name, red_findings(name, load_manifests().get(name)), note_findings(name))
    return 0


def project_status(name, man):
    """(colour, reason) of a running project, None if it isn't running. Priority red > blue (Claude waits) > cyan (Claude works) > green."""
    sess = sanitize(name)
    if not session_exists(sess):
        return None
    red = red_findings(name, man)
    sync_alert(name, red, note_findings(name))
    if red:
        return "red", "; ".join(red)
    kind, reason = claude_state(name)
    if kind == "waiting":
        return "blue", f"Claude is waiting: {reason or 'for you'}"
    if kind == "working":
        return "cyan", "Claude is working"
    return "green", "running, services up" if man and man.get("service") else "running"


HOOK_MARKS = ("hyperbeam/waiting", "hyperbeam/claude", "$HB_STATE/claude", "hyperbeam-guard", "hyperbeam-prs")     # how our hooks are recognised (the first is PR #10's)
# (event, matcher, state written). Plain shell, no Python: fast; nothing happens outside hyperbeam sessions (no $HB_PROJECT).
HOOK_CMDS = [
    ("Stop", "", "waiting finished responding"),
    ("Notification", "", "waiting needs your input or permission"),
    ("PreToolUse", "AskUserQuestion|ExitPlanMode", "waiting asks you a question"),
    ("PostToolUse", "", "working"),
    ("PostToolUseFailure", "", "working"),               # Claude carries on after a prompt it blocked by itself (unattended)
    ("PermissionDenied", "", "working"),
    ("UserPromptSubmit", "", "working"),
]
GUARD_MATCHER = "Bash"


def hook_command(state, stop=False, notification=False, prompt=False):
    """Writes the state the menu and `wait` read. At Stop in a worker session (HB_WORKER=1) the report is written too (`_worker-report`, reads the hook input).
    The Notification hook leaves an idle notice alone (`idle_prompt`: Claude only sat waiting after Stop; the state stays "finished")."""
    idle = " && ! grep -q idle_prompt" if notification else ""
    if stop:                    # a worker's Stop goes through `_worker-report`: it checks the session first (a nested `claude -p` inherits HB_WORKER), then writes state and report
        return f'[ -n "$HB_PROJECT" ] && [ -d "$HB_STATE" ] && {{ [ -n "$HB_WORKER" ] && {SELF} _worker-report || echo "{state}" > "$HB_STATE/claude"; }}; exit 0'
    rec = f'; [ -z "$HB_WORKER" ] || {SELF} _worker-prompt' if prompt else ""     # the first prompt of a worker records its Claude's session id
    return f'[ -n "$HB_PROJECT" ] && [ -d "$HB_STATE" ]{idle} && {{ echo "{state}" > "$HB_STATE/claude"{rec}; }}; exit 0'


def guard_command():
    """The guard (guard.py next to this script): nothing outside hyperbeam sessions; otherwise a small stdlib Python reads the tool call."""
    return f': hyperbeam-guard; [ -n "$HB_PROJECT" ] || exit 0; exec /usr/bin/python3 {shlex.quote(str(HERE / "guard.py"))}'


def prs_command():
    """PostToolUse on Bash: after `gh pr create|merge|close` hooks/pr-refresh.sh runs `hyperbeam refresh-prs` in the background, so the sidebar's Merge button
    is right at once. Nothing outside hyperbeam sessions (no $HB_PROJECT)."""
    return f': hyperbeam-prs; [ -n "$HB_PROJECT" ] || exit 0; exec /bin/sh {shlex.quote(str(HERE / "hooks" / "pr-refresh.sh"))}'


def install_hooks(settings=None):
    """Merge hyperbeam's hooks into the user's Claude settings; nothing else is changed. Idempotent: ours are recognised by HOOK_MARKS and replaced
    in place (PR #10's older ones too; ones no longer wanted are removed). A backup of the file is kept next to it once. Returns the events changed."""
    f = Path(settings or os.environ.get("HB_SETTINGS") or Path.home() / ".claude/settings.json")
    data = json.loads(f.read_text()) if f.exists() else {}
    before = json.dumps(data, sort_keys=True)
    bak = f.with_name(f.name + ".hyperbeam-backup")
    if f.exists() and not bak.exists():
        bak.write_text(f.read_text())
    hooks = data.setdefault("hooks", {})
    want = [(e, m, hook_command(st, stop=e == "Stop", notification=e == "Notification", prompt=e == "UserPromptSubmit")) for e, m, st in HOOK_CMDS] + [("PreToolUse", GUARD_MATCHER, guard_command()), ("PostToolUse", "Bash", prs_command())]
    kind = lambda c: "guard" if "hyperbeam-guard" in c else "prs" if "hyperbeam-prs" in c else "state"
    claimed = set()
    for event, matcher, cmd in want:
        groups = hooks.setdefault(event, [])
        entry = {"type": "command", "command": cmd, "timeout": 20 if event == "Stop" else 5}
        for gi, g in enumerate(groups):
            hit = [i for i, h in enumerate(g.get("hooks", [])) if (event, gi, i) not in claimed and any(m in h.get("command", "") for m in HOOK_MARKS)
                   and kind(h["command"]) == kind(cmd)]
            if hit:
                g["hooks"][hit[0]] = entry
                g["matcher"] = matcher
                if not matcher:
                    g.pop("matcher")
                claimed.add((event, gi, hit[0]))
                break
        else:
            groups.append({**({"matcher": matcher} if matcher else {}), "hooks": [entry]})
            claimed.add((event, len(groups) - 1, 0))
    for event, groups in list(hooks.items()):              # ours that are no longer wanted
        for gi, g in enumerate(groups):
            g["hooks"] = [h for i, h in enumerate(g.get("hooks", [])) if (event, gi, i) in claimed or not any(m in h.get("command", "") for m in HOOK_MARKS)]
        hooks[event] = [g for g in groups if g.get("hooks")]
    # Claude's default model moved from opusplan to sonnet, once: only an opusplan is changed; the marker keeps a later manual choice (/model, settings) from being reset by every update
    marker = DATA_DIR / "claude-model-sonnet"
    if not marker.exists():
        if data.get("model") == "opusplan":
            data["model"] = "sonnet"
        try:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(time.strftime("%Y-%m-%d") + "\n")
        except OSError:
            pass
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, indent=2) + "\n")
    return [] if json.dumps(data, sort_keys=True) == before else sorted({e for e, _, _ in want})


# ---------- layouts (saved to the project data folder, layout.json) ----------
SHELLS = {"bash", "zsh", "sh", "fish", "dash"}


def layout_file(name):
    return pfile(name, "layout.json")


def load_layout(name):
    try:
        d = json.loads(layout_file(name).read_text())
    except (OSError, ValueError):
        return None
    ok = isinstance(d.get("windows"), list) and d["windows"] and all(w.get("panes") and w.get("layout") for w in d["windows"])
    return d if ok else None


def session_project(sess):
    """Project name of a session (its HB_PROJECT), else the session name."""
    v = tmux("show-environment", "-t", f"={sess}", "HB_PROJECT", check=False).stdout.strip()
    return v.split("=", 1)[1] if v.startswith("HB_PROJECT=") else sess


def pane_role(cmd, win, first_in_window, services):
    if first_in_window and win in services:
        return f"service:{win}"
    return "claude" if cmd == "claude" else "shell" if cmd in SHELLS else "other"


def pane_program(shell_pid):
    """The command line of the program running in a pane's shell (its first child process), e.g. `nvim notes.md`, `tail -f log`; '' when the shell is idle,
    the program is a shell or Claude (restored by their own rules) or `sudo` (never started again by itself)."""
    try:
        kids = Path(f"/proc/{shell_pid}/task/{shell_pid}/children").read_text().split()
        argv = [a for a in Path(f"/proc/{kids[0]}/cmdline").read_bytes().decode(errors="replace").split("\0") if a]
    except (OSError, IndexError):
        return ""
    if not argv or Path(argv[0]).name in SHELLS | {"claude", "sudo", "tmux"}:
        return ""
    return shlex.join(argv)


def snapshot(sess, man):
    """Windows (name, layout, active) and panes (cwd, role, active, prog) of a session; prog = the program running in an `other` pane."""
    services = {x["name"] for x in (man or {}).get("service", [])}
    wins = {}
    for line in tmux("list-windows", "-t", f"={sess}", "-F", "#{window_index}\t#{window_name}\t#{window_layout}\t#{window_active}",
                     check=False).stdout.splitlines():
        i, name, layout, active = line.split("\t")
        wins[i] = dict(name=name, layout=layout, active=active == "1", panes=[])
    for line in tmux("list-panes", "-s", "-t", f"={sess}", "-F",
                     "#{window_index}\t#{pane_index}\t#{pane_current_path}\t#{pane_active}\t#{pane_current_command}\t#{pane_pid}",
                     check=False).stdout.splitlines():
        wi, pi, cwd, active, cmd, pid = line.split("\t")
        w = wins.get(wi)
        if w is not None:
            role = pane_role(cmd, w["name"], not w["panes"], services)
            pane = dict(cwd=cwd, role=role, active=active == "1")
            prog = pane_program(pid) if role == "other" else ""
            if prog:
                pane["prog"] = prog
            w["panes"].append(pane)
    return [w for _, w in sorted(wins.items(), key=lambda kv: int(kv[0])) if w["panes"]]


def save_layout(name, clean=False):
    """Write the session's layout. clean=True is Stop: it records 'stopped cleanly'."""
    sess = sanitize(name)
    if not session_exists(sess):
        return False
    wins = snapshot(sess, load_manifests().get(name))
    if sess == MENU:
        wins = [w for w in wins if w["name"] != "menu"]        # the menu window is always rebuilt by ensure_menu
    if not wins:
        return False
    d = layout_file(name)
    d.parent.mkdir(parents=True, exist_ok=True)
    tmp = d.with_suffix(".tmp")
    tmp.write_text(json.dumps(dict(version=1, saved=time.time(), clean=clean, session=sess, windows=wins), indent=1))
    tmp.replace(d)
    return True


def save_all():
    """Save every hyperbeam project session (the menu's 5-minute timer and the tmux detach hook call this)."""
    fmt = "#{session_name}\t#{@hb}"
    n = 0
    for line in tmux("list-sessions", "-F", fmt, check=False).stdout.splitlines():
        sess, tag = (line.split("\t") + [""])[:2]
        if tag == "1":
            refresh_claude_pane(sess)       # HB_CLAUDE_PANE stays right (a no-op while the pane it names exists)
        if tag == "1":
            n += save_layout(session_project(sess))
    return n


def ago_text(ts):
    a = ago(ts)
    return "just now" if a == "now" else f"{a} ago"


def describe_layout(lay):
    panes = sum(len(w["panes"]) for w in lay["windows"])
    return f"{len(lay['windows'])} windows, {panes} panes, saved {ago_text(lay['saved'])}"


# ---------- start check: git state and signs of a bad shutdown (the wrap-up check will reuse git_problems) ----------
STENO_RE = re.compile(r"^steno-\d{4}-\d{2}-\d{2}\.txt$")


def is_steno(path, rel):
    """Dictation notes from `steno`: steno-YYYY-MM-DD.txt whose first line starts with `stenographr`."""
    if not STENO_RE.match(Path(rel).name):
        return False
    try:
        with open(Path(path) / rel, errors="replace") as f:
            return f.readline().startswith("stenographr")
    except OSError:
        return True      # tracked but deleted, or unreadable: the name is enough


def git_out(path, *a):
    return subprocess.run(["git", "-C", str(path), *a], capture_output=True, text=True).stdout.strip()


def git_fetch(path):
    """Quiet, short, never prompts; failure (offline, no remote) is ignored."""
    if not git_out(path, "remote"):
        return
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=3")
    try:
        subprocess.run(["git", "-C", str(path), "fetch", "--quiet"], env=env, capture_output=True, timeout=6)
    except (subprocess.TimeoutExpired, OSError):
        pass


def git_problems(path, fetch=False, behind=True):
    """Things worth sorting out in a repo, as short sentences. steno-*.txt files are left out of the counts; one that git
    could commit (not ignored: untracked, or tracked) is reported as a warning instead. No repo: []."""
    path = Path(path)
    if not git_out(path, "rev-parse", "--git-dir"):
        return []
    if fetch:
        git_fetch(path)
    out, steno = [], []
    dirty = 0
    for line in git_out(path, "status", "--porcelain=v1", "-uall").splitlines():
        rel = line[3:].split(" -> ")[-1].strip('"')
        if is_steno(path, rel):
            steno.append(rel)
        else:
            dirty += 1
    steno += [f for f in git_out(path, "ls-files").splitlines() if STENO_RE.match(Path(f).name) and is_steno(path, f) and f not in steno]
    if dirty:
        out.append(f"{dirty} uncommitted change{'s' if dirty != 1 else ''}")
    branch = git_out(path, "symbolic-ref", "-q", "--short", "HEAD")
    if not branch:
        out.append(f"detached HEAD at {git_out(path, 'rev-parse', '--short', 'HEAD')}")
    for marker, what in (("MERGE_HEAD", "merge"), ("rebase-merge", "rebase"), ("rebase-apply", "rebase"),
                         ("CHERRY_PICK_HEAD", "cherry-pick"), ("REVERT_HEAD", "revert")):
        if Path(git_out(path, "rev-parse", "--path-format=absolute", "--git-path", marker)).exists():
            out.append(f"{what} in progress")
    up = git_out(path, "rev-parse", "--abbrev-ref", "@{u}") if branch else ""
    if up:
        ahead, nbehind = (git_out(path, "rev-list", "--left-right", "--count", "HEAD...@{u}") or "0 0").split()
        if int(ahead):
            out.append(f"{ahead} unpushed commit{'s' if ahead != '1' else ''} on {branch}")
        if int(nbehind) and behind:
            out.append(f"behind {up} by {nbehind} commit{'s' if nbehind != '1' else ''}")
    elif git_out(path, "remote"):
        n = git_out(path, "rev-list", "--count", "HEAD", "--not", "--remotes")
        if n and n != "0":
            out.append(f"{n} commit{'s' if n != '1' else ''} not on any remote" + (f" ({branch} has no upstream)" if branch else ""))
    n = len(git_out(path, "stash", "list").splitlines())
    if n:
        out.append(f"{n} stash{'es' if n != 1 else ''}")
    if steno:
        out.append("steno file(s) not ignored by git: " + ", ".join(sorted(set(steno))) + " (personal notes: never commit; add `steno-*.txt` to .gitignore)")
    return out


def crash_note(name):
    """A saved layout with no clean-stop record and no running session: the last session crashed, was killed, or the machine went down.
    Alone it is only a note (kk shows it until the project is opened); it is not a problem."""
    lay = load_layout(name)
    if lay and sanitize(name) != MENU and not lay.get("clean") and not session_exists(sanitize(name)):
        return f"last session did not stop cleanly (layout saved {ago_text(lay['saved'])}: crash, reboot or killed session)"
    return ""


def commit_secrets(path):
    """Obvious secrets in commits that are on no remote yet (the last 50): file, line, pattern, commit; never a value."""
    if not git_out(path, "rev-parse", "--git-dir"):
        return []
    log = git_out(path, "log", "--no-merges", "-p", "-U0", "--no-color", "--no-ext-diff", "-n", "50", "--format=@@commit%h", "HEAD", "--not", "--remotes")
    out, seen = [], set()
    for fname, ln, pat, commit in scan_diff(log):
        if (fname, ln, pat) not in seen:
            seen.add((fname, ln, pat))
            out.append(f"secret in commit {commit}: {fname}:{ln} {pat}")
    return out


def git_red_notes(path, fetch=False, behind=True):
    """(red, notes) of a repo. Red is rare: a merge/rebase/cherry-pick/revert stuck with conflicts, or secrets in commits. Everything else
    git_problems finds (uncommitted, unpushed, stash, behind, detached HEAD, a merge without conflicts) is a quiet note."""
    path = Path(path)
    conflicts = git_out(path, "diff", "--name-only", "--diff-filter=U").splitlines() if git_out(path, "rev-parse", "--git-dir") else []
    red, notes = [], []
    for p in git_problems(path, fetch, behind):
        if conflicts and p.endswith(" in progress"):
            red.append(f"{p} with conflicts ({len(conflicts)} file{'s' * (len(conflicts) != 1)})")
        else:
            notes.append(p)
    return red + commit_secrets(path), notes


def start_check(name, path, fetch=True):
    """(red, notes) on Open. Only red problems make Open offer Claude; a crash (saved layout not clean) is a note, like the git state."""
    red, notes = git_red_notes(path, fetch)
    crash = crash_note(name)
    return red, drift_notes(name, path) + stale_doc_notes(name, path) + ([crash] if crash else []) + notes


# ---------- wrap-up check: git state, obvious secrets, steno files. Reports file, line and pattern name, never a value. ----------
SECRET_PATTERNS = [
    ("private key header", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY(?: BLOCK)?-----")),
    ("AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Stripe live key", re.compile(r"\b[sr]k_live_[A-Za-z0-9]{16,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Anthropic/OpenAI key", re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{32,}")),
    ("URL with password", re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:/@'\"]+:([^\s@/'\"]{6,})@(?!localhost|127\.|0\.0\.0\.0|\[::1\]|\$|\{|<)[^\s'\"]+", re.I)),
]
KEYWORD = r"(?:password|passwd|pwd|secret|token|api[_-]?key|apikey|private[_-]?key|access[_-]?key|auth[_-]?key)"
ASSIGN_QUOTED = re.compile(rf"""\b[\w.-]*{KEYWORD}[\w.-]*["']?\s*[:=]\s*(["'])([^"'\s]{{8,}})\1""", re.I)
ASSIGN_BARE = re.compile(rf"""^\s*(?:export\s+)?[A-Za-z0-9_.-]*{KEYWORD}[A-Za-z0-9_.-]*\s*[:=]\s*([^\s#'"]{{8,}})\s*$""", re.I)
BARE_FILES = re.compile(r"(^|/)\.env[^/]*$|\.(ini|cfg|conf|properties|ya?ml|toml)$", re.I)
PLACEHOLDER = re.compile(r"""(?ix)^(your|change|example|sample|dummy|fake|test|todo|placeholder|xxx|\.\.\.|<|\$|\{|%|\*|null|none|true|false|undefined|env\b|process\.|os\.|import\.meta|getenv|secrets?\.|config\.|settings\.)
                             |\$\{|\{\{|<%|[(\[]|(?:password|secret|token|changeme|postgres|localhost)$""")
SECRET_NAMES = re.compile(r"""(?ix)(^|/)(\.env(\.[^/]+)?|id_(rsa|dsa|ecdsa|ed25519)|[^/]+\.(pem|key|p12|pfx|jks|keystore)|
                          credentials(\.(json|ya?ml|csv|txt|xml|toml|ini))?|\.pgpass|\.netrc)$""")
SAFE_NAMES = re.compile(r"\.(example|sample|template|dist|tpl|pub)$", re.I)
SKIP_CONTENT = re.compile(r"(^|/)(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|poetry\.lock|uv\.lock|Cargo\.lock)$|\.(lock|min\.js|map|svg)$", re.I)


TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|fixtures?|mocks?)/|\.(test|spec)\.[a-z]+$", re.I)


def looks_secret(v):
    """A literal that could be a real secret: not a placeholder, some variety (>= 6 distinct characters, and a digit or mixed case/symbol)."""
    if PLACEHOLDER.search(v) or len(set(v)) < 6:
        return False
    return any(c.isdigit() for c in v) or (any(c.islower() for c in v) and any(c.isupper() for c in v)) or any(not c.isalnum() for c in v)


def scan_line(fname, line):
    """Pattern names that match one line of a file. The line itself is never returned."""
    hits = [n for n, rx in SECRET_PATTERNS if rx.search(line)]
    if "URL with password" in hits:
        m = SECRET_PATTERNS[-1][1].search(line)
        if m and not looks_secret(m.group(1)):
            hits.remove("URL with password")
    if not TEST_PATH.search(fname):         # fixtures and tests are full of fake literals; provider-specific patterns above still apply
        m = ASSIGN_QUOTED.search(line)
        if m and looks_secret(m.group(2)):
            hits.append("secret-like assignment")
        elif BARE_FILES.search(fname) and (m := ASSIGN_BARE.match(line)) and looks_secret(m.group(1)):
            hits.append("secret-like assignment")
    return hits


def scan_diff(text):
    """Added lines of a unified diff (-U0, optionally `git log -p` with @@commit markers) -> [(file, line, pattern, commit)]."""
    out, fname, ln, commit = [], None, 0, ""
    for l in text.splitlines():
        if l.startswith("@@commit"):
            commit = l[8:]
        elif l.startswith("+++ "):
            fname = l[4:].removeprefix("b/") if l != "+++ /dev/null" else None
        elif l.startswith("@@") and fname:
            m = re.search(r"\+(\d+)", l)
            ln = int(m.group(1)) if m else 0
        elif l.startswith("+") and fname and not SKIP_CONTENT.search(fname) and not STENO_RE.match(Path(fname).name):
            for p in scan_line(fname, l[1:]):
                out.append((fname, ln, p, commit))
            ln += 1
    return out


def scan_file(path, rel):
    """Whole-file scan (untracked files, or tracked ones with --all)."""
    f = Path(path) / rel
    try:
        if f.stat().st_size > 300_000 or SKIP_CONTENT.search(rel) or STENO_RE.match(f.name):
            return []
        data = f.read_bytes()
    except OSError:
        return []
    if b"\0" in data[:8192]:
        return []
    return [(rel, i, p, "") for i, l in enumerate(data.decode(errors="replace").splitlines(), 1) for p in scan_line(rel, l)]


def secret_findings(path, since, all_tracked=False):
    """Obvious secrets in: commits since `since` (unix time), staged and unstaged changes, untracked files not ignored (contents), and
    tracked/untracked files with secret-looking names. Returns sentences with file, line, pattern (and commit); no values."""
    path = Path(path)
    hits = []
    if since:
        hits += scan_diff(git_out(path, "log", "--no-merges", "-p", "-U0", "--no-color", "--no-ext-diff", f"--since={int(since)}", "--format=@@commit%h"))
    hits += scan_diff(git_out(path, "diff", "--cached", "-U0", "--no-color", "--no-ext-diff"))
    hits += scan_diff(git_out(path, "diff", "-U0", "--no-color", "--no-ext-diff"))
    others = git_out(path, "ls-files", "--others", "--exclude-standard").splitlines()
    for rel in others:
        hits += scan_file(path, rel)
    tracked = git_out(path, "ls-files").splitlines()
    if all_tracked:
        for rel in tracked:
            hits += scan_file(path, rel)
    out, seen = [], set()
    for rel in tracked + others:
        if SECRET_NAMES.search(rel) and not SAFE_NAMES.search(rel) and not STENO_RE.match(Path(rel).name):
            out.append(f"{rel}: secret-looking file name ({'tracked' if rel in tracked else 'untracked, not ignored'})")
    for fname, ln, p, commit in hits:
        key = (fname, ln, p)
        if key not in seen:
            seen.add(key)
            out.append(f"{fname}:{ln} {p}" + (f" (commit {commit})" if commit else ""))
    return out


def wrapup_check(name, path, since=None):
    """One project's wrap-up check: git state (without 'behind', and no network), secrets, steno files. -> dict with sentences."""
    git = git_problems(path, fetch=False, behind=False)
    steno = [g for g in git if g.startswith("steno file")]
    git = [g for g in git if not g.startswith("steno file")]
    tracked = [f for f in git_out(path, "ls-files").splitlines() if STENO_RE.match(Path(f).name) and is_steno(path, f)]
    if tracked:
        steno = []          # a tracked steno file is also "not ignored": one message is enough
        steno.append("steno file(s) tracked in git: " + ", ".join(tracked) + " (personal notes: remove from the index, never commit)")
    return dict(name=name, path=str(path), git=git, secrets=secret_findings(path, since) if git_out(path, "rev-parse", "--git-dir") else [], steno=steno)


def wrapup_clean(r):
    return not (r["git"] or r["secrets"] or r["steno"])


def format_wrapup(r, cap=12):
    if wrapup_clean(r):
        return f"{r['name']}: clean"
    lines = [f"{r['name']}:"]
    lines += [f"  git: {g}" for g in r["git"]]
    lines += [f"  steno: {g}" for g in r["steno"]]
    lines += [f"  secrets: {x}" for x in r["secrets"][:cap]]
    if len(r["secrets"]) > cap:
        lines.append(f"  secrets: +{len(r['secrets']) - cap} more")
    return "\n".join(lines)


def session_since(name):
    """Start of the work to check: the session record's start, else when the project's tmux session was created, else 12 hours ago."""
    d = load_journal()
    if name in d["projects"] and d.get("started"):
        return d["started"]
    c = tmux("display-message", "-p", "-t", f"={sanitize(name)}", "#{session_created}", check=False).stdout.strip()
    return int(c) if c.isdigit() else time.time() - 12 * 3600


def check_project(name):
    p = known_path(name)
    r = wrapup_check(name, p, session_since(name)) if p.is_dir() else None
    if r:
        write_wrapup_note(name, r)          # a check that found something is kept in .hyperbeam/notes, whatever the user picks next
    return r


def ask_tty(text):
    """Ask y/n in the terminal (CLI over SSH). No terminal: no."""
    if not sys.stdin.isatty():
        return False
    print(text)
    return input("y/n: ").strip().lower().startswith("y")


def open_project(name, path, man, ask, say):
    """Everything Open does before showing the session: the session if it isn't running (the saved layout comes back; if the start check found something,
    Claude continues its last conversation, fresh if none)."""
    sess = sanitize(name)
    ensure_link(name, path)
    if sess == MENU:
        return ensure_menu()
    if session_exists(sess):
        return
    lay = load_layout(name)
    restore = lay            # layouts always come back (windows, panes, programs); the Claude choice is its own step
    say(f"{name}: checking git state...")
    findings, notes = start_check(name, path)
    start_session(name, man, say, path=path, restore=restore, findings=findings, notes=notes)


def publish_claude_pane(sess, pane, plan=()):
    """HB_CLAUDE_PANE = the tmux pane id of the session's Claude pane: in the session environment (every pane created afterwards has it, and
    `tmux show-environment -t SESSION HB_CLAUDE_PANE` answers for older ones), and exported in the panes of `plan` that already exist
    ([(pane id, role, cwd)]: their processes were started before the id was known). The integration point for tools in a pane (stenographr)."""
    if not pane:
        return
    tmux("set-environment", "-t", sess, "HB_CLAUDE_PANE", pane, check=False)
    for pid, role, _ in plan:
        if role in ("claude", "shell", "other"):
            send_line(pid, f"export HB_CLAUDE_PANE={pane}; clear")


def refresh_claude_pane(sess):
    """Keep HB_CLAUDE_PANE right if the pane it names is gone (the user closed or rebuilt it)."""
    cur = tmux("show-environment", "-t", sess, "HB_CLAUDE_PANE", check=False).stdout.strip().partition("=")[2]
    if cur and tmux("display-message", "-p", "-t", cur, "#{pane_id}", check=False).stdout.strip() == cur:
        return
    publish_claude_pane(sess, find_claude_pane(sess))


def new_pane(args, cmd=None):
    """Run a tmux command that creates a pane (new-session, split-window) and return the new pane's id."""
    return tmux(*args, "-P", "-F", "#{pane_id}", *([cmd] if cmd else [])).stdout.strip()


def menu_cmd():
    return f"{SELF} _menu; echo; echo '[hyperbeam] menu exited, press Enter'; read"


def ensure_menu():
    """The manager session, two windows: `home` (the manager's Claude in ~/manager on the left, a shell on the right; what the sidebar shows on its
    right) and `menu` (the menu, for SSH and the switch/window modes). `home` comes back as it was saved (windows, panes, the programs in them,
    Claude with --continue); without a saved layout it is the default."""
    if session_exists(MENU):
        return
    clean_server_env()
    dev = ensure_manager_dir()
    envargs = ["-e", f"HB_PROJECT={MENU}", "-e", f"HB_STATE={project_dir(MENU, dev)}", "-e", "HOST=0.0.0.0", "-e", f"PATH={session_path()}"]
    lay = load_layout(MENU)
    plan = None
    if lay:
        try:
            plan = restore_layout(MENU, dev, lay, envargs)
        except subprocess.CalledProcessError:
            tmux("kill-session", "-t", f"={MENU}", check=False)
    if plan:
        claudes = [p for p in plan if p[1] == "claude"] or plan[:1]
        publish_claude_pane(MENU, claudes[0][0], plan)
        seen = set()
        for pid, _, cwd in claudes:
            send_line(pid, manager_cmd(cont=cwd not in seen))
            seen.add(cwd)
        restart_programs(lay, plan)
    else:
        claude = new_pane(["new-session", "-d", "-s", MENU, "-n", "home", "-x", "200", "-y", "50", "-c", str(dev), *envargs])
        publish_claude_pane(MENU, claude)
        new_pane(["split-window", "-h", "-l", "40%", "-t", claude, "-c", str(dev)])
        send_line(claude, f"export HB_CLAUDE_PANE={claude}; " + manager_cmd(cont=True))
        tmux("select-pane", "-t", claude)
    new_pane(["new-window", "-d", "-t", f"={MENU}:", "-n", "menu", "-c", str(HERE)], menu_cmd())
    tag_session(MENU)


def default_layout(sess, path, envargs):
    """New session with window `work`: Claude on the left (60%), a shell on the right (40%). Returns [(pane id, role, cwd)]."""
    claude = new_pane(["new-session", "-d", "-s", sess, "-n", "work", "-x", "200", "-y", "50", "-c", str(path), *envargs])
    publish_claude_pane(sess, claude)
    shell = new_pane(["split-window", "-h", "-l", "40%", "-t", claude, "-c", str(path)])
    tmux("select-pane", "-t", claude)
    return [(claude, "claude", str(path)), (shell, "shell", str(path))]


def restore_layout(sess, path, lay, envargs):
    """Recreate the saved windows and panes (cwds, layouts, active window and pane). Returns [(pane id, role, cwd)]."""
    plan, active_pane, active_win = [], [], None
    for i, w in enumerate(lay["windows"]):
        cwds = [p["cwd"] if Path(p["cwd"]).is_dir() else str(path) for p in w["panes"]]
        if i == 0:
            first = new_pane(["new-session", "-d", "-s", sess, "-n", w["name"], "-x", "200", "-y", "50", "-c", cwds[0], *envargs])
        else:
            first = new_pane(["new-window", "-d", "-t", f"{sess}:", "-n", w["name"], "-c", cwds[0]])
        ids = [first]
        for c in cwds[1:]:
            ids.append(new_pane(["split-window", "-t", ids[-1], "-c", c]))
        if len(ids) > 1:
            tmux("select-layout", "-t", first, w["layout"])
        plan += [(pid, p["role"], c) for pid, p, c in zip(ids, w["panes"], cwds)]
        act = next((pid for pid, p in zip(ids, w["panes"]) if p.get("active")), first)
        tmux("select-pane", "-t", act)
        if w.get("active"):
            active_win = first
    if active_win:
        tmux("select-window", "-t", active_win)
    return plan


def restart_programs(lay, plan):
    """Type each `other` pane's saved program into its shell (plan and lay list the panes in the same order). Ctrl-C leaves a shell."""
    for pane, (pid, role, _) in zip([p for w in lay["windows"] for p in w["panes"]], plan):
        if role == "other" and pane.get("prog"):
            send_line(pid, pane["prog"])


def project_envargs(name, man, path, extra=None):
    """`-e K=V` tmux arguments for a project's session: session_env, HB_STATE (the project's state folder) and PATH (the shims: `NAME VERB`, `hb VERB`), then `extra`."""
    env = session_env(man, name)
    ensure_link(name, path)
    env["HB_STATE"] = str(project_dir(name, path))
    try:
        install_shims()
        env["PATH"] = session_path()
    except OSError:
        pass
    env.update(extra or {})
    clean_server_env()
    return [x for k, v in env.items() for x in ("-e", f"{k}={v}")]


def write_service_note(name, path, failures):
    """A service that failed or was slow: <project data>/notes/YYYY-MM-DD-services.md with the result and the last lines of its window. No failure: nothing."""
    if not failures:
        return None
    try:
        d = project_dir(name, path) / "notes"
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"{time.strftime('%Y-%m-%d')}-services.md"
        L = [f"# Service problems in {name}, {time.strftime('%Y-%m-%d %H:%M')}", ""]
        for x in failures:
            L += [f"## {x['name']}", x["result"], "", "```", x["tail"] or "(empty)", "```", ""]
        f.write_text("\n".join(L))
        return f
    except OSError:
        return None


def start_session(name, man, say=print, path=None, restore=None, findings=(), notes=()):
    """Create the project's session: the default layout, or `restore` (a saved layout).
    Default: window `work` (Claude left, a shell right), then one window per service. Services start in manifest order, each after the
    previous one is ready. Then the first shell pane prints the start-check findings and real warnings and runs `kk`, and Claude starts
    (`claude --continue`). A service that fails or is slow makes the dot red and writes a note; nothing is ever sent to Claude."""
    sess = sanitize(name)
    if sess == MENU:
        return ensure_menu()
    path = manifest_path(man) if man else Path(path)
    if not path.is_dir():
        raise RuntimeError(f"{path} does not exist")
    envargs = project_envargs(name, man, path)
    plan = None
    if restore:
        try:
            plan = restore_layout(sess, path, restore, envargs)
            say(f"{name}: restored layout ({describe_layout(restore)})")
        except subprocess.CalledProcessError as e:
            tmux("kill-session", "-t", f"={sess}", check=False)
            say(f"{name}: could not restore the layout ({(e.stderr or '').strip()}); using the default one")
    if plan is None:
        plan = default_layout(sess, path, envargs)
    tmux("set-option", "-t", f"={sess}", "detach-on-destroy", "off", check=False)   # if it ends any way, its clients move to another session
    tag_session(sess)
    claude_panes = [p for p in plan if p[1] == "claude"] or plan[:1]
    first_claude = claude_panes[0][0]
    publish_claude_pane(sess, first_claude, plan if restore else claude_panes[:1])      # a default layout's shell pane inherited it; its Claude pane was made before the id was known
    shell = next((p[0] for p in plan if p[1] == "shell"), None) or next((p[0] for p in plan if p[1] == "other"), None)
    services = man.get("service", []) if man else []
    if services:
        send_line(first_claude, "echo '[hyperbeam] starting services; Claude starts when they are done'")
    failures = []
    for svc in services:
        win = svc["name"]
        target = next((p[0] for p in plan if p[1] == f"service:{win}"), None)
        if target is None:
            target = new_pane(["new-window", "-d", "-t", f"{sess}:", "-n", win, "-c", str(path)])
        send_line(target, f'{svc["cmd"]}; echo "[hyperbeam] exited: $?"')
        say(f"{name}: started {win}, waiting...")
        result = wait_ready(sess, win, svc, man.get("port"))
        say(f"{name}: {win}: {result}")
        if result.startswith("WARNING"):
            failures.append(dict(name=win, result=result, tail=pane_tail(target)))
    if restore and plan:
        restart_programs(restore, plan)
    if shell:
        ff = ""
        if findings or notes:
            sc = pfile(name, "startcheck.txt")
            sc.write_text("\n".join([*findings, *[f"note: {n}" for n in notes]]) + "\n")
            ff = f" --findings {shlex.quote(str(sc))}"
        send_line(shell, f"clear; {SELF} _warn {shlex.quote(str(path))}{ff}; {SELF} info {shlex.quote(name)}")
    findings = [*findings, *[f"service {f['name']}: {f['result']}" for f in failures]]      # a failed or slow service: red dot and a note, nothing is sent to Claude
    write_status(name, list(findings), list(notes))
    write_service_note(name, path, failures)
    send_line(first_claude, claude_cmd(cont=True))
    seen = {next(c for pid, _, c in plan if pid == first_claude)}
    for pid, role, cwd in claude_panes[1:]:          # more Claude panes: continue only if the directory differs (one conversation per directory)
        send_line(pid, claude_cmd(cont=cwd not in seen))
        seen.add(cwd)
    if not restore:
        tmux("select-window", "-t", f"{sess}:work")
    save_layout(name)
    say(f"{name}: session ready" + (f" (PORT={man['port']})" if man and man.get("port") else ""))


def own_session():
    """Name of the tmux session this process runs in, or ''."""
    return run("tmux", "display-message", "-p", "#{session_name}") if os.environ.get("TMUX") else ""


def project_ports(man):
    if not man:
        return []
    ports = {man["port"]} if man.get("port") else set()
    ports.update(s["ready_port"] for s in man.get("service", [])
                 if isinstance(s.get("ready_port"), int) and not isinstance(s.get("ready_port"), bool))
    return sorted(ports)


def stop_project(name, man, say=print):
    """Run `stop` commands in reverse order, kill the session, confirm the ports are closed."""
    sess = sanitize(name)
    if sess == MENU or own_session() == sess:
        raise RuntimeError(f"{sess} is the menu session (the menu, the manager's Claude and a shell); stop it with `tmux kill-session -t {sess}`")
    path = manifest_path(man) if man else None
    env = dict(os.environ, **session_env(man, name))
    for svc in reversed(man.get("service", []) if man else []):
        if "stop" in svc:
            say(f"{name}: stop {svc['name']}: {svc['stop']}")
            try:
                r = subprocess.run(svc["stop"], shell=True, cwd=path, env=env, capture_output=True, text=True, timeout=120)
                if r.returncode:
                    say(f"{name}: WARNING stop {svc['name']} exited {r.returncode}: {(r.stderr or r.stdout).strip()[-200:]}")
            except subprocess.TimeoutExpired:
                say(f"{name}: WARNING stop {svc['name']} timed out")
    if session_exists(sess):
        save_layout(name, clean=True)
        clear_status(name)
        for tty, cs in client_sessions().items():
            if cs == sess:                                  # whoever is looking at it goes to the manager session, not away (a detached client closes kitty's right split)
                tmux("switch-client", "-c", tty, "-t", home_target(tty), check=False)
        tmux("kill-session", "-t", f"={sess}", check=False)
        say(f"{name}: session killed")
    deadline = time.time() + 6
    ports = project_ports(man)
    while time.time() < deadline and any(listeners(p) for p in ports):
        time.sleep(0.5)
    left = [(p, listeners(p)) for p in ports if listeners(p)]
    if left:
        for p, info in left:
            say(f"{name}: WARNING port {p} still listening: {info.split(chr(10))[0][:120]}")
        return False
    say(f"{name}: stopped" + (f"; ports {', '.join(map(str, ports))} are free" if ports else " (no manifest: no ports to check)"))
    return True


