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
    (wd / "started.json").write_text(json.dumps({"time": time.time(), "head": git_out(path, "rev-parse", "HEAD"), "refs": git_refs(path), "task": task, "prompt": str(pf), "path": str(path)}))
    prompt = write_prompt(sess, worker_prompt_text(pf, findings), plan=False)
    envargs = project_envargs(name, man, path, {"HB_WORKER": "1", "HB_STATE": str(wd), "HB_REPORTS": str(reports_dir(name))})
    pane = new_pane(["new-session", "-d", "-s", wsess, "-n", "claude", "-x", "200", "-y", "50", "-c", str(path), *envargs])
    tmux("set-option", "-t", f"={wsess}", "detach-on-destroy", "off", check=False)
    send_line(pane, f'{claude_base()}{worker_flags()} "$(cat {shlex.quote(str(prompt))})"')
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
    try:                                                    # the worker's merged, clean worktrees go with it; quietly, never a reason to fail
        path = known_path(a.name)
        if (Path(path) / ".git").exists():
            tidy_apply(path, tidy_plan(path, worktrees_only=True), lambda s: None)
    except Exception:
        pass
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


def git_refs(path):
    """{ref: sha} of every local branch and remote-tracking branch: taken when a worker starts, so its report lists only what it changed."""
    out = git_out(path, "for-each-ref", "--format=%(objectname) %(refname)", "refs/heads", "refs/remotes")
    return {l.split(" ", 1)[1]: l.split(" ", 1)[0] for l in out.splitlines() if " " in l}


def worker_commits(path, rec):
    """Commits on the branches the worker created or moved since it started (refs at the start against now), not what others merged meanwhile."""
    old = rec.get("refs")
    if old is None:                                         # started before refs were recorded
        return git_out(path, "log", "--oneline", "-n", "30", f"{rec['head']}..HEAD") if rec.get("head") else ""
    now = git_refs(path)
    lines = []
    for ref, sha in now.items():
        if ref.startswith("refs/heads/") and old.get(ref) != sha:
            lines += git_out(path, "log", sha, "-n", "30", "--format=%h %s [" + ref[len("refs/heads/"):] + "]", "--not", *old.values()).splitlines()
    return "\n".join(lines[:30])


def section(text, title):
    """The body of the `## title` section of a report, or ''."""
    m = re.search(r"^## " + re.escape(title) + r"\n\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else ""


def cmd_worker_report(_):
    """The Stop hook of a worker (HB_WORKER=1): <HB_REPORTS>/<date-time>-<slug>.md with the task, Claude's final message, branch, commits on the branches the
    worker created or moved, the PR URL and the transcript path. One report per worker run: a later Stop (after `send`) rewrites it, keeping the earlier final
    messages under "Earlier rounds". Reads the hook input (JSON) on stdin."""
    try:
        hook = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        hook = {}
    d = os.environ.get("HB_REPORTS")
    if not d:
        return 0
    sf = Path(os.environ.get("HB_STATE", "")) / "started.json"
    try:
        rec = json.loads(sf.read_text())
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
    commits = worker_commits(path, rec)
    pr = next(iter(re.findall(r"https://github\.com/[\w.-]+/[\w.-]+/pull/\d+", msg)), "none")
    task = rec.get("task") or "worker task"
    slug = re.sub(r"[^a-z0-9]+", "-", task.lower()).strip("-")[:40] or "report"
    Path(d).mkdir(parents=True, exist_ok=True)
    f = Path(d) / (rec.get("report") or f"{time.strftime('%Y-%m-%d-%H%M%S')}-{slug}.md")
    earlier = ""
    if f.is_file():                                         # this run's report exists: a send round pushes the old final message down, a repeated Stop replaces it
        old = f.read_text()
        earlier = section(old, "Earlier rounds")
        if rec.get("sent", 0) > rec.get("reported", 0):
            earlier = (section(old, "Claude's final message") + ("\n\n---\n\n" + earlier if earlier else "")).strip()
    started = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(rec["time"])) if rec.get("time") else "-"
    f.write_text(f"# {task}\n\n- project: {os.environ.get('HB_PROJECT', '-')}\n- started: {started}\n- finished: {time.strftime('%Y-%m-%d %H:%M:%S')}\n- branch: {branch}\n- PR: {pr}\n"
                 f"- transcript (the long form): {tp or '-'}\n\n## Claude's final message\n\n{msg.strip()}\n\n"
                 + (f"## Earlier rounds\n\n{earlier}\n\n" if earlier else "") + "## Commits since the worker started\n\n" + (commits or "none") + "\n")
    if rec:
        rec.update(report=f.name, reported=time.time())
        try:
            sf.write_text(json.dumps(rec))
        except OSError:
            pass
    return 0


# ---------- `hyperbeam reports`: what the workers did and what it cost ----------
def transcript_stats(tp):
    """(input+cache creation tokens, cache read tokens, output tokens, API calls, active minutes) of a conversation file. One API message is several
    records sharing an id: counted once. Active time: the gaps between records, those over 10 minutes (waiting for the user) removed."""
    msgs, stamps = {}, []
    try:
        lines = Path(tp).read_text(errors="replace").splitlines()
    except OSError:
        return None
    for line in lines:
        try:
            o = json.loads(line)
        except ValueError:
            continue
        ts = o.get("timestamp")
        if isinstance(ts, str):
            try:
                stamps.append(datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())
            except ValueError:
                pass
        m = o.get("message") or {}
        if o.get("type") == "assistant" and isinstance(m, dict) and m.get("usage"):
            msgs[m.get("id") or f"anon{len(msgs)}"] = m["usage"]
    u = list(msgs.values())
    stamps.sort()
    active = sum(b - a for a, b in zip(stamps, stamps[1:]) if b - a <= 600)
    return (sum(x.get("input_tokens", 0) + x.get("cache_creation_input_tokens", 0) for x in u), sum(x.get("cache_read_input_tokens", 0) for x in u),
            sum(x.get("output_tokens", 0) for x in u), len(u), active / 60)


def parse_report(f):
    """A report file as a dict (task, project, started, finished, branch, pr, commits, transcript: strings; commits a count), or None if it is not one."""
    text = Path(f).read_text(errors="replace")
    if not text.startswith("# "):
        return None
    field = lambda k: (re.search(r"^- " + k + r"[^:\n]*: (.*)$", text, re.M) or [None, ""])[1].strip()
    c = section(text, "Commits since the worker started")
    return dict(file=Path(f), task=text.splitlines()[0][2:].strip(), project=field("project"), started=field("started"), finished=field("finished"), branch=field("branch"),
                pr=field("PR"), transcript=field("transcript"), commits=0 if c in ("", "none") else len(c.splitlines()))


REFACTOR_WORDS = re.compile(r"refactor|cleanup|clean-up|audit", re.I)


def report_time(r):
    try:
        return datetime.datetime.strptime(r["finished"][:19], "%Y-%m-%d %H:%M:%S" if len(r["finished"]) > 16 else "%Y-%m-%d %H:%M").timestamp()
    except ValueError:
        return 0


def cmd_reports(a):
    """hyperbeam reports [--since DATE] [--since-refactor] [NAME...]: one row per worker report with what it cost, and a total. --since-refactor = reports
    after the last one whose task mentions refactor, cleanup or audit (a word match on the task's first line)."""
    names = {sanitize(n) for n in a.names}
    reps = []
    for f in (DATA_DIR / "projects").glob("*/reports/*.md"):
        try:
            r = parse_report(f)
        except OSError:
            continue
        if r and (not names or sanitize(r["project"]) in names):
            reps.append(r)
    reps.sort(key=report_time)
    if a.since_refactor:
        marks = [report_time(r) for r in reps if REFACTOR_WORDS.search(r["task"])]
        if marks:
            reps = [r for r in reps if report_time(r) > marks[-1]]
    if a.since:
        reps = [r for r in reps if r["finished"][:10] >= a.since]
    runs = read_lab_runs()
    for r in reps:
        r["stats"] = transcript_stats(r["transcript"]) if r["transcript"] not in ("", "-") else None
        try:
            t0 = datetime.datetime.strptime(r["started"], "%Y-%m-%d %H:%M:%S").isoformat() if r["started"] != "-" else None
        except ValueError:
            t0 = None
        t1 = datetime.datetime.fromtimestamp(report_time(r)).isoformat()
        r["lab"] = sum(x["seconds"] for x in runs if t0 and t0 <= x["time"] <= t1 and x["project"] == r["project"] and not (x.get("why") or "").startswith("tool test:"))
    k = lambda n: f"{n / 1000:.0f}k" if n >= 10000 else str(int(n))
    rows = [("date", "project", "task", "branch", "PR", "commits", "in+cc", "cache", "out", "calls", "min", "lab s")]
    tot = [0, 0, 0, 0, 0.0, 0.0, 0]
    for r in reps:
        s = r["stats"] or (0, 0, 0, 0, 0.0)
        pr = "#" + r["pr"].rsplit("/", 1)[-1] if r["pr"].startswith("http") else "-"
        rows.append((r["finished"][:16], r["project"], first_line(r["task"], 38), r["branch"][:24], pr, str(r["commits"]), k(s[0]), k(s[1]), k(s[2]), str(s[3]), f"{s[4]:.0f}", f"{r['lab']:.0f}"))
        for i in range(4):
            tot[i] += s[i]
        tot[4] += s[4]
        tot[5] += r["lab"]
        tot[6] += r["commits"]
    rows.append(("total", f"{len(reps)} reports", "", "", "", str(tot[6]), k(tot[0]), k(tot[1]), k(tot[2]), str(tot[3]), f"{tot[4]:.0f}", f"{tot[5]:.0f}"))
    wid = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    for r in rows:
        print("  ".join(c.ljust(w) if i in (1, 2, 3) else c.rjust(w) if i > 3 else c.ljust(w) for i, (c, w) in enumerate(zip(r, wid))).rstrip())
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




# ---------- tidy: merged branches and worktrees (`hyperbeam tidy [NAME] [--yes]`, and `close` for the worktree part) ----------
WORK_ROOT = Path.home() / ".cache" / "hyperbeam-work"       # where workers' git worktrees live


def _g(path, *a):
    r = subprocess.run(["git", "-C", str(path), *a], capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def tidy_plan(path, worktrees_only=False):
    """What can go in one repo: {"local": [...], "remote": [...], "worktrees": [(dir, branch)], "skipped": [(what, why)], "main": ref}.
    Merged means an ancestor of origin/<default branch> (squash merges are not detected, so those stay). Nothing is deleted here."""
    plan = dict(local=[], remote=[], worktrees=[], skipped=[], main=None)
    _g(path, "fetch", "-q", "--prune", "origin")
    rc, head, _ = _g(path, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    default = head.split("/", 1)[1] if rc == 0 and "/" in head else "main"
    main = f"origin/{default}"
    if _g(path, "rev-parse", "--verify", "-q", main)[0] != 0:
        plan["skipped"].append((str(path), f"no {main}"))
        return plan
    plan["main"] = main
    merged = lambda ref: _g(path, "merge-base", "--is-ancestor", ref, main)[0] == 0
    current = _g(path, "symbolic-ref", "--short", "HEAD")[1]
    root = WORK_ROOT.resolve()
    taken = {}                                              # branch -> worktree dir, for the checked-out branches
    removing = set()
    block, d = {}, None
    for line in _g(path, "worktree", "list", "--porcelain")[1].splitlines() + [""]:
        if line.startswith("worktree "):
            block = {"dir": Path(line[9:])}
        elif line.startswith("branch "):
            block["branch"] = line[7:].removeprefix("refs/heads/")
        elif line == "detached":
            block["detached"] = True
        elif line == "" and block:
            d = block["dir"]
            b = block.get("branch")
            if b:
                taken[b] = d
            if root in d.resolve().parents:
                if not b:
                    plan["skipped"].append((str(d), "worktree on a detached HEAD"))
                elif _g(d, "status", "--porcelain")[1]:
                    plan["skipped"].append((str(d), "worktree has uncommitted changes"))
                elif not merged(b):
                    plan["skipped"].append((str(d), f"branch {b} is not merged"))
                else:
                    plan["worktrees"].append((d, b))
                    removing.add(b)
            block = {}
    if worktrees_only:
        return plan
    for b in _g(path, "for-each-ref", "--format=%(refname:short)", "refs/heads")[1].splitlines():
        if b == default:
            continue
        if b == current:
            plan["skipped"].append((b, "checked out"))
        elif b in taken and b not in removing:
            plan["skipped"].append((b, f"checked out in {taken[b]}"))
        elif not merged(b):
            plan["skipped"].append((b, "not merged"))
        else:
            plan["local"].append(b)
    for r in _g(path, "for-each-ref", "--format=%(refname:short)", "refs/remotes/origin")[1].splitlines():
        b = r.removeprefix("origin/")
        if b in ("HEAD", "origin", default):
            continue
        if merged(r):
            plan["remote"].append(b)
        else:
            plan["skipped"].append((r, "not merged"))
    return plan


def tidy_apply(path, plan, say):
    for d, b in plan["worktrees"]:
        r = _g(path, "worktree", "remove", str(d))          # never --force: git itself refuses a dirty one
        say(f"  worktree {d}: " + ("removed" if r[0] == 0 else f"kept ({r[2]})"))
        p = d.parent
        while p != WORK_ROOT.resolve() and p != WORK_ROOT and WORK_ROOT in p.parents and p.is_dir() and not any(p.iterdir()):
            p.rmdir()                                       # fix/ after fix/x
            p = p.parent
    _g(path, "worktree", "prune")
    for b in plan["local"]:
        r = _g(path, "branch", "-d", b)
        say(f"  local {b}: " + ("deleted" if r[0] == 0 else f"kept ({r[2]})"))
    for b in plan["remote"]:
        r = _g(path, "push", "origin", "--delete", b)
        say(f"  remote {b}: " + ("deleted" if r[0] == 0 else f"kept ({r[2]})"))


def empty_work_dirs():
    if not WORK_ROOT.is_dir():
        return []
    return sorted((p for p in WORK_ROOT.rglob("*") if p.is_dir() and not any(p.iterdir())), key=lambda p: -len(p.parts))


def cmd_tidy(a):
    """hyperbeam tidy [NAME] [--yes]: list (or with --yes delete) merged local and remote branches and clean merged worktrees under ~/.cache/hyperbeam-work."""
    if a.name:
        paths = [(a.name, known_path(a.name))]
    else:
        paths = [(r["name"], r["path"]) for r in scan() if r["git"] and r["remote"]]
    for name, path in paths:
        if not (Path(path) / ".git").exists():
            if a.name:
                sys.exit(f"hyperbeam tidy: {name} is not a git project")
            continue
        plan = tidy_plan(path)
        if not (plan["local"] or plan["remote"] or plan["worktrees"] or plan["skipped"]):
            continue
        print(f"{name}:")
        for d, b in plan["worktrees"]:
            print(f"  worktree {d} (merged {b})")
        for b in plan["local"]:
            print(f"  local branch {b} (merged into {plan['main']})")
        for b in plan["remote"]:
            print(f"  remote branch origin/{b} (merged)")
        for what, why in plan["skipped"]:
            print(f"  skipped {what}: {why}")
        if a.yes:
            tidy_apply(path, plan, print)
    empties = [] if a.name else empty_work_dirs()
    for p in empties:
        print(f"empty dir {p}")
        if a.yes:
            p.rmdir()
    if not a.yes:
        print("nothing deleted: add --yes to delete the lines above (not the skipped ones)")
    return 0
