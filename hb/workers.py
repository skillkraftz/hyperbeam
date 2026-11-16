# hyperbeam, part 'workers': workers: work / wait / close / status. Runs in the namespace of the `hyperbeam` script (see its loader): no imports of its own.
# ---------- workers: Claude sessions the manager starts for a project (`hyperbeam work|wait|close`) ----------
def worker_sess(name):
    """The tmux session of a project's worker: claude-NAME. Not a project, never listed as one."""
    return f"claude-{sanitize(name)}"


def worker_dir(name):
    """The worker's own state folder (the hooks' `claude` state file, started.json): apart from the project's, so a worker never changes the user's dot."""
    d = project_dir(name) / "worker"
    d.mkdir(parents=True, exist_ok=True)
    return d


def reports_dir(name):
    return project_dir(name) / "reports"


def worker_prompt_text(prompt_file, findings):
    """What the worker's Claude starts from: the start-check problems (if any), WORKER.md, then the manager's prompt."""
    top = ("The start check found problems in this project. Look at them first, and say in your final message what you did about them:\n"
           + "\n".join(f"- {f}" for f in findings) + "\n\n---\n\n") if findings else ""
    return top + (HERE / "WORKER.md").read_text().rstrip() + "\n\n---\n\n" + Path(prompt_file).read_text()


WAIT_POLL = 2             # seconds between looks at the workers' state files
BLOCKED_GRACE = 180       # a worker "needing input" this long is blocked: Claude Code blocks an unanswered prompt by itself after ~2 minutes and carries on


def worker_state(name):
    """('working'|'finished'|'blocked'|'ended'|'none', detail, started.json) from the worker's hook state file and its session."""
    try:
        rec = json.loads((project_dir(name) / "worker" / "started.json").read_text())
    except (OSError, ValueError):
        return "none", "", {}
    try:
        txt = (project_dir(name) / "worker" / "claude").read_text().strip()
    except OSError:
        txt = ""
    if txt.startswith("waiting finished responding"):
        return "finished", "", rec
    if txt.startswith("waiting"):
        return "blocked", txt[len("waiting"):].strip(), rec
    if not session_exists(worker_sess(name)):
        return "ended", "its session is gone", rec
    return "working", "", rec


def newest_report(name, since=0):
    try:
        fs = [f for f in reports_dir(name).glob("*.md") if f.stat().st_mtime >= since]
        return max(fs, key=lambda f: f.stat().st_mtime, default=None)
    except OSError:
        return None


def cmd_work(a):
    """hyperbeam work NAME PROMPT_FILE: make sure the user's session NAME runs, then start the worker `claude-NAME`: a fresh Claude (no plan mode) in the project's
    folder, with WORKER.md and the prompt. Asks nothing: start-check problems go to the top of the worker's prompt. One worker per project."""
    name = a.name
    if not project_exists(name) or sanitize(name) == MENU:
        sys.exit(f"hyperbeam work: no project called {name} (try `hyperbeam scan`)")
    pf = Path(a.prompt_file).expanduser()
    if not pf.is_file():
        sys.exit(f"hyperbeam work: {pf} is not a file")
    sess, wsess = sanitize(name), worker_sess(name)
    if session_exists(wsess):
        sys.exit(f"hyperbeam work: {name} already has a worker ({wsess}): one worker per project, because it edits the folder the services run from. "
                 f"`hyperbeam wait {name}` waits for it, `hyperbeam close {name}` ends it.")
    man = load_manifests().get(name)
    path = known_path(name)
    if not path.is_dir():
        sys.exit(f"hyperbeam work: {path} does not exist")
    findings, notes = start_check(name, path)
    if not session_exists(sess):
        start_session(name, man, print, path=path, restore=load_layout(name), findings=findings, notes=notes)
        touch_opened(name)
    wd = worker_dir(name)
    (wd / "claude").write_text("working\n")             # a stale state of an earlier worker must not look like "finished"
    task = next((l.lstrip("# ").strip() for l in pf.read_text().splitlines() if l.strip()), "worker task")
    (wd / "started.json").write_text(json.dumps({"time": time.time(), "head": git_out(path, "rev-parse", "HEAD"), "task": task, "prompt": str(pf), "path": str(path)}))
    prompt = write_prompt(sess, worker_prompt_text(pf, findings), plan=False)
    envargs = project_envargs(name, man, path, {"HB_WORKER": "1", "HB_STATE": str(wd), "HB_REPORTS": str(reports_dir(name))})
    pane = new_pane(["new-session", "-d", "-s", wsess, "-n", "claude", "-x", "200", "-y", "50", "-c", str(path), *envargs])
    tmux("set-option", "-t", f"={wsess}", "detach-on-destroy", "off", check=False)
    send_line(pane, f'{claude_base()} "$(cat {shlex.quote(str(prompt))})"')
    print(f"{name}: worker started in the tmux session {wsess} ({len(findings)} start-check problems added to its prompt)."
          f" `hyperbeam wait {name}` waits for it; the report goes to {reports_dir(name)}/")
    return 0


def cmd_wait(a):
    """hyperbeam wait NAME [NAME...] [--timeout S]: block until each worker's Claude has finished (the Stop hook's state), then print each report's path.
    Exit 0 all finished, 1 timeout, 2 a worker is blocked (a question, or a prompt unanswered for BLOCKED_GRACE seconds) or its session ended."""
    deadline = time.time() + a.timeout if a.timeout else None
    pending, code, seen, asking = list(dict.fromkeys(a.names)), 0, {}, {}
    for n in pending:
        if worker_state(n)[0] == "none":
            sys.exit(f"hyperbeam wait: {n} has no worker")
    while pending:
        for n in list(pending):
            st, detail, rec = worker_state(n)
            if st == "blocked" and detail.startswith("needs your input"):
                if time.time() - asking.setdefault(n, time.time()) < BLOCKED_GRACE:
                    continue                                # a prompt Claude Code may block by itself and move on from: keep waiting
            else:
                asking.pop(n, None)
            rep = newest_report(n, rec.get("sent", rec.get("time", 0))) if st in ("finished", "ended", "blocked") else None
            if st == "working" or (st == "finished" and not rep and time.time() - seen.setdefault(n, time.time()) < 30):
                continue                                    # the report is written just after the state: give it a moment
            pending.remove(n)
            if st in ("blocked", "ended"):
                code = max(code, 2)
            print(f"{n}: {rep or '(no report: worker ' + st + (': ' + detail if detail else '') + ')'}", flush=True)
        if pending:
            if deadline and time.time() > deadline:
                print(f"hyperbeam wait: timeout; still working: {', '.join(pending)}", file=sys.stderr)
                return 1
            time.sleep(WAIT_POLL)
    return code


def cmd_send(a):
    """hyperbeam send NAME FILE|-: paste the text (a file, or stdin for -) into the worker's Claude as one bracketed paste and Enter: the manager's review feedback.
    Only while that Claude waits (state finished); never while it works or sits at a prompt, where the paste would answer it. `wait` works after it as usual."""
    wsess = worker_sess(a.name)
    st, detail, rec = worker_state(a.name)
    if st == "none" or not session_exists(wsess):
        sys.exit(f"hyperbeam send: {a.name} has no worker")
    if st != "finished":
        sys.exit(f"hyperbeam send: the worker of {a.name} is not waiting ({st}{': ' + detail if detail else ''}); `hyperbeam wait {a.name}` first")
    text = sys.stdin.read() if a.file == "-" else Path(a.file).expanduser().read_text()
    if not text.strip():
        sys.exit("hyperbeam send: nothing to send")
    pane = f"={wsess}:"
    tmux("set-buffer", "-b", "hb-send", "--", text.strip())
    tmux("paste-buffer", "-p", "-d", "-b", "hb-send", "-t", pane)
    time.sleep(0.5)                                         # let Claude's input take the paste before Enter
    tmux("send-keys", "-t", pane, "Enter")
    rec["sent"] = time.time()                               # `wait` takes only reports written after this one
    (worker_dir(a.name) / "started.json").write_text(json.dumps(rec))
    (worker_dir(a.name) / "claude").write_text("working\n")  # until its hook says so, it is not finished
    print(f"{a.name}: sent {len(text.strip())} characters; `hyperbeam wait {a.name}` waits for the answer")
    return 0


def cmd_close(a):
    """hyperbeam close NAME: end the worker session claude-NAME. Never the user's session NAME."""
    wsess = worker_sess(a.name)
    if not session_exists(wsess):
        sys.exit(f"hyperbeam close: {a.name} has no worker")
    if tmux("show-environment", "-t", f"={wsess}", "HB_WORKER", check=False).stdout.strip() != "HB_WORKER=1":
        sys.exit(f"hyperbeam close: the session {wsess} is not a worker (no HB_WORKER); not touching it")
    tmux("kill-session", "-t", f"={wsess}", check=False)
    shutil.rmtree(project_dir(a.name) / "worker", ignore_errors=True)
    print(f"{a.name}: worker closed (reports stay in {reports_dir(a.name)}/)")
    return 0


def cmd_status(_):
    """hyperbeam status: which project sessions run, and each worker's state."""
    run_set = running_sessions()
    for r in scan():
        n = r["name"]
        w = worker_state(n)[0] if worker_sess(n) in run_set else ""
        if sanitize(n) in run_set or w:
            print(f"{n}: session running" + (f"; worker {w}" if w else ""))
    return 0


def cmd_worker_report(_):
    """The Stop hook of a worker (HB_WORKER=1): <HB_REPORTS>/<date-time>-<slug>.md with the task, Claude's final message, branch, commits since the worker
    started, the PR URL and the transcript path. Reads the hook input (JSON) on stdin."""
    try:
        hook = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        hook = {}
    d = os.environ.get("HB_REPORTS")
    if not d:
        return 0
    try:
        rec = json.loads((Path(os.environ.get("HB_STATE", "")) / "started.json").read_text())
    except (OSError, ValueError):
        rec = {}
    path = rec.get("path") or hook.get("cwd") or os.getcwd()
    tp = hook.get("transcript_path") or ""
    msg = ""
    try:
        msg = last_assistant_message(tp) if tp else ""
    except OSError:
        pass
    msg = msg or hook.get("last_assistant_message") or "(no final message found)"
    branch = git_out(path, "rev-parse", "--abbrev-ref", "HEAD") or "-"
    if rec.get("time"):                                     # any branch: a worker in a git worktree commits on a branch the project folder is not on
        commits = git_out(path, "log", "--all", "--source", f"--since=@{int(rec['time'])}", "-n", "30", "--format=%h %s [%S]").replace("refs/heads/", "").replace("refs/remotes/", "")
    else:
        commits = git_out(path, "log", "--oneline", "-n", "30", f"{rec['head']}..HEAD") if rec.get("head") else ""
    pr = next(iter(re.findall(r"https://github\.com/[\w.-]+/[\w.-]+/pull/\d+", msg)), "none")
    task = rec.get("task") or "worker task"
    slug = re.sub(r"[^a-z0-9]+", "-", task.lower()).strip("-")[:40] or "report"
    Path(d).mkdir(parents=True, exist_ok=True)
    f = Path(d) / f"{time.strftime('%Y-%m-%d-%H%M')}-{slug}.md"
    f.write_text(f"# {task}\n\n- project: {os.environ.get('HB_PROJECT', '-')}\n- finished: {time.strftime('%Y-%m-%d %H:%M')}\n- branch: {branch}\n- PR: {pr}\n"
                 f"- transcript (the long form): {tp or '-'}\n\n## Claude's final message\n\n{msg.strip()}\n\n## Commits since the worker started\n\n"
                 + (commits or "none") + "\n")
    return 0


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


