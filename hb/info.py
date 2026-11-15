# hyperbeam, part 'info': sessions, URLs, list, phone, info (kk), scan/open/stop commands. Runs in the namespace of the `hyperbeam` script (see its loader): no imports of its own.
# ---------- sessions, URLs, list, phone ----------
_tailnet = []


def tailnet_host():
    """This machine's MagicDNS name (or its Tailscale IP), from `tailscale status --json`; None if unavailable."""
    if not _tailnet:
        host = None
        try:
            me = json.loads(run("tailscale", "status", "--json")).get("Self", {})
            host = (me.get("DNSName") or "").rstrip(".") or next(iter(me.get("TailscaleIPs", [])), None)
        except ValueError:
            pass
        _tailnet.append(host)
    return _tailnet[0]


def live_sessions():
    """Running sessions of hyperbeam projects (tagged @hb, or with a manifest), most recently used first. The port is None without a
    manifest or without a port. session_last_attached is empty until a session's first attach (it updates on every attach and
    switch-client), so session_created is the fallback."""
    by_sess = {sanitize(n): (n, m) for n, m in load_manifests().items()}
    out, here = [], own_session()
    fmt = "#{session_name}\t#{session_last_attached}\t#{session_created}\t#{session_attached}\t#{@hb}"
    for line in tmux("list-sessions", "-F", fmt, check=False).stdout.splitlines():
        sess, last, created, attached, tag = line.split("\t")
        if sess == MENU or (sess not in by_sess and tag != "1"):
            continue
        name, man = by_sess.get(sess, (sess, {}))
        out.append(dict(name=name, sess=sess, port=man.get("port"), here=sess == here,
                        ts=int(last or created or 0), attached=int(attached or 0)))
    return sorted(out, key=lambda s: -s["ts"])


def project_url(port):
    host = tailnet_host()
    return f"http://{host}:{port}" if host and port else None


def print_sessions(sessions, numbered):
    remote = is_remote()
    width = max(len(s["name"]) for s in sessions)
    for i, s in enumerate(sessions, 1):
        port = s["port"]
        cols = [f"{i}" if numbered else "-", s["name"].ljust(width)]
        if port:
            cols += [f"{port:<5}", "up  " if port_open(port) else "down", project_url(port) or "(no tailscale)"]
            if not remote:
                cols.append(f"local http://localhost:{port}")
        else:
            cols.append("no port")
        if s["here"]:
            cols.append("(here)")
        print("  ".join(cols))


def read_choice(n):
    """A number from 1..n, or None for quit. Up to 9 sessions it takes a single keypress."""
    import termios, tty
    while True:
        sys.stdout.write(f"\nNumber to switch to (1-{n}), q to quit: ")
        sys.stdout.flush()
        if n <= 9:
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
            print(ch if ch.isprintable() else "")
            if ch in ("q", "Q", "\x03", "\x04", "\x1b", ""):
                return None
            if ch.isdigit() and 1 <= int(ch) <= n:
                return int(ch)
        else:
            try:
                line = input().strip()
            except (EOFError, KeyboardInterrupt):
                return None
            if line.lower() == "q":
                return None
            if line.isdigit() and 1 <= int(line) <= n:
                return int(line)


def go_to(session):
    touch_opened(session["name"])
    return attach_here(session["sess"])


def cmd_list(_):
    sessions = live_sessions()
    if not sessions:
        print("No sessions running. Run `hyperbeam` for the menu.")
        return 1
    print_sessions(sessions, numbered=True)
    if not sys.stdin.isatty():
        return 0
    choice = read_choice(len(sessions))
    return 0 if choice is None else go_to(sessions[choice - 1])


def cmd_phone(_):
    sessions = live_sessions()
    if not sessions:
        print("Nothing is running. Try `hyperbeam list` or `hyperbeam` (the menu) to start something.")
        return 1
    print("Open projects (most recent first):")
    print_sessions(sessions, numbered=False)
    target = next((x for x in sessions if not x["here"]), None)
    if target is None:
        print("\nYou are already in the only running session.")
        return 0
    print(f"\nAttaching to {target['name']}...")
    return go_to(target)


def cmd_save(a):
    """tmux hooks: save every layout; with a session name (client-session-changed) also record that project in the session record."""
    save_all()
    if a.session and a.session != MENU and tmux("show-options", "-t", f"={a.session}", "-v", "@hb", check=False).stdout.strip() == "1":
        journal_record(session_project(a.session))


def cmd_wrapup(a):
    if a.counts:
        hits = []
        for rel in git_out(a.path, "ls-files").splitlines():
            hits += scan_file(a.path, rel)
        from collections import Counter
        c = Counter(h[2] for h in hits)
        print(f"{Path(a.path).name}: {len(hits)} hits " + ", ".join(f"{k}={v}" for k, v in sorted(c.items())))
        return
    r = wrapup_check(Path(a.path).name, a.path, a.since)
    if a.all:
        r["secrets"] += [f"{f}:{l} {p}" for f, l, p, _ in (h for rel in git_out(a.path, "ls-files").splitlines() for h in scan_file(a.path, rel))]
    print(format_wrapup(r))


# ---------- info (kk) ----------
URL_RE = re.compile(r"^(https?|postgres(?:ql)?|redis|mysql|mongodb(?:\+srv)?|amqp|nats)://[^\s'\"]+$")
LOOPBACK = ("127.", "[::1]", "localhost")


def local_to_tailnet(url, host):
    return re.sub(r"//([^/@]*@)?(127\.0\.0\.1|localhost)", lambda m: f"//{m.group(1) or ''}{host}", url, count=1)


def mask_password(url):
    """URLs from .env files: hide a password unless the host is this machine."""
    m = re.match(r"^([a-z+]+://[^:/@]+:)([^@/]+)(@.*)$", url)
    if m and not re.match(r"^[a-z+]+://[^@]*@(127\.|localhost|\[::1\])", url):
        return f"{m.group(1)}***{m.group(3)}"
    return url


def session_pids(sess):
    """pids of everything running in a tmux session's panes (the pane processes and all their descendants)."""
    roots = tmux("list-panes", "-s", "-t", f"={sess}", "-F", "#{pane_pid}", check=False).stdout.split()
    kids = {}
    for d in Path("/proc").iterdir():
        if d.name.isdigit():
            try:
                st = (d / "stat").read_text()
                kids.setdefault(int(st[st.rindex(")") + 2:].split()[1]), []).append(int(d.name))
            except (OSError, ValueError):
                pass
    seen, todo = set(), [int(r) for r in roots]
    while todo:
        p = todo.pop()
        if p not in seen:
            seen.add(p)
            todo += kids.get(p, [])
    return seen


def session_listeners(sess):
    """[(port, process name, loopback_only)] for TCP ports listened on by processes inside the session."""
    if not sess or not session_exists(sess):
        return []
    pids, out = session_pids(sess), {}
    for line in run("ss", "-ltnpH").splitlines():
        f = line.split()
        m = re.search(r'\(\("([^"]+)",pid=(\d+)', line)
        if len(f) < 4 or not m or int(m.group(2)) not in pids:
            continue
        addr, port = f[3].rsplit(":", 1)
        lo = addr.startswith(LOOPBACK)
        key = int(port)
        out[key] = (key, m.group(1), lo and out.get(key, (0, 0, True))[2])
    return sorted(out.values())


def docker_containers(path):
    """Containers that belong to the project, matched by the compose working_dir label or the supabase CLI workdir label:
    [(name, [published host ports])]."""
    if not shutil.which("docker"):
        return []
    fmt = '{{.Names}}\t{{.Ports}}\t{{.Label "com.docker.compose.project.working_dir"}}\t{{.Label "com.supabase.cli.workdir"}}'
    out = []
    for line in run("docker", "ps", "--format", fmt).splitlines():
        f = (line.split("\t") + ["", "", "", ""])[:4]
        if str(path) in (f[2], f[3]):
            ports = sorted({int(x) for x in re.findall(r":(\d+)->", f[1])})
            out.append((f[0], ports))
    return out


def supabase_urls(path):
    """URL values of `supabase status -o json` (never the keys). Only asked when supabase containers of this project run."""
    if not shutil.which("supabase") or not (path / "supabase").is_dir():
        return {}
    r = subprocess.run(["supabase", "status", "-o", "json"], cwd=path, capture_output=True, text=True, timeout=10)
    try:
        d = json.loads(r.stdout)
    except ValueError:
        return {}
    urls = {k: v for k, v in d.items() if isinstance(v, str) and URL_RE.match(v)}
    ref = (d.get("linked_project") or {}).get("project_ref")
    if ref:
        urls["LINKED_DASHBOARD"] = f"https://supabase.com/dashboard/project/{ref}"
    return urls


def git_web_url(path):
    url = run("git", "-C", str(path), "remote", "get-url", "origin")
    m = re.match(r"^(?:git@|ssh://git@)?([^:/]+)[:/](.+?)(?:\.git)?/?$", url) if url and not url.startswith("http") else None
    if m:
        host = "github.com" if m.group(1).startswith("github") else m.group(1)
        return f"https://{host}/{m.group(2)}"
    return re.sub(r"\.git$", "", url) if url.startswith("http") else ""


def vercel_projects(path):
    """Linked Vercel project names from .vercel/project.json or repo.json (no login needed; the URL itself needs one)."""
    names = []
    for f, key in ((path / ".vercel/project.json", None), (path / ".vercel/repo.json", "projects")):
        try:
            d = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        for p in (d.get(key, []) if key else [d]):
            if p.get("name") or p.get("projectName"):
                names.append(p.get("name") or p.get("projectName"))
    return names


def env_urls(path):
    out = []
    for f in sorted(path.glob(".env*")):
        if f.name.endswith((".example", ".sample", ".template")) or not f.is_file():
            continue
        try:
            lines = f.read_text().splitlines()
        except OSError:
            continue
        for line in lines:
            m = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$", line)
            if m:
                v = m.group(2).strip("'\"")
                if URL_RE.match(v):
                    out.append((m.group(1), mask_password(v), f.name))
    return out


def service_states(sess, man, host_ports):
    """[(service, 'up'/'down'/'running'/'exited', detail)] for the manifest's services."""
    out = []
    for svc in (man or {}).get("service", []):
        rp = svc.get("ready_port", man.get("port") if "ready_delay" not in svc else None)
        if isinstance(rp, int) and not isinstance(rp, bool):
            out.append((svc["name"], "up" if port_open(rp) else "down", f"port {rp}"))
        else:
            pane = tmux("capture-pane", "-p", "-t", f"={sess}:{svc['name']}", check=False).stdout
            out.append((svc["name"], "exited" if re.search(r"\[hyperbeam\] exited: \d+", pane) else
                        "running" if session_exists(sess) else "down", "no port"))
    return out


RED_ANSI, RESET_ANSI = "\x1b[31;1m", "\x1b[0m"


def project_info(name, rows=None, footer=True, alert=True):
    """The text `kk` prints. Discovery only; each source is skipped silently if it does not apply. `rows`: a scan() result to reuse."""
    from concurrent.futures import ThreadPoolExecutor
    mans = load_manifests()
    man = mans.get(name)
    row = None if man else next((r for r in (rows if rows is not None else scan()) if r["name"] == name), None)
    path = manifest_path(man) if man else (row["path"] if row else None)
    if path is None:
        return f"hyperbeam info: no project called {name}"
    sess, host = sanitize(name), tailnet_host()
    running = session_exists(sess)
    L = []

    def section(title, lines):
        lines = [x for x in lines if x]
        if lines:
            L.extend(["", title, *[f"  {x}" for x in lines]])

    containers = docker_containers(path)
    with ThreadPoolExecutor(2) as ex:
        sb = ex.submit(supabase_urls, path) if any("supabase" in c[0] for c in containers) else None
        gh = ex.submit(lambda: run("gh", "repo", "view", "--json", "homepageUrl", "-q", ".homepageUrl")) if shutil.which("gh") and (path / ".git").exists() else None
        listeners = session_listeners(sess)
        sbu = sb.result() if sb else {}
        try:
            homepage = gh.result(timeout=3) if gh else ""
        except Exception:
            homepage = ""
    ports = {p: (proc, lo) for p, proc, lo in listeners}
    if man and man.get("port") and man["port"] not in ports and port_open(man["port"]):
        ports[man["port"]] = ("?", False)

    L.append(f"{name}   {home_rel(path)}   session: {sess if running else '(not running)'}")
    st = project_status(name, man)
    L.append(f"status: [{st[0]}] {st[1]}" if st else "status: not running")
    if alert and st and st[0] == "red":              # problems first, in red, with the fix command
        L[:0] = [RED_ANSI + "PROBLEMS" + RESET_ANSI] + [RED_ANSI + f"  - {f}" + RESET_ANSI for f in red_findings(name, man)] + [""]
    if running:
        section("Notes (quiet: they do not affect the dot; the wrap-up check at Stop/Done deals with them)", note_findings(name))
    states = service_states(sess, man, ports)
    section("Services", [f"{n:<12} {st:<7} {d}" for n, st, d in states])
    section("App", [f"http://localhost:{p}  {proc}" + ("  (this machine only)" if lo else "") for p, (proc, lo) in sorted(ports.items())])
    if host:
        tail = [f"http://{host}:{p}  {proc}" for p, (proc, lo) in sorted(ports.items()) if not lo]
        covered = {urlparse(u).port for u in sbu.values()}
        tail += [f"{host}:{p}  {c}" for c, ps in containers for p in ps if p not in covered]
        tail += [f"{local_to_tailnet(u, host)}  supabase {k}" for k, u in sbu.items() if "127.0.0.1" in u or "localhost" in u]
        section("Tailscale", tail)
    section("Docker", [f"localhost:{p}  {c}" for c, ps in containers for p in ps])
    section("Supabase", [f"{u}  {k}" for k, u in sbu.items()])
    vp = vercel_projects(path)
    section("Vercel", [f"project {n}  (production URL: needs `vercel login`)" for n in vp])
    web = git_web_url(path)
    section("Git", [f"{web}  repo" if web else "", f"{homepage}  homepage (GitHub)" if homepage else ""])
    section("Standard verbs (hyperbeam NAME VERB, or NAME VERB / hb VERB inside the session)", [verbs_summary(name, path)])
    section("Pull requests (yours, open)", [f"#{x['number']}  {x['title']}  {x['url']}" + (f"  [stale: {pr_age_days(x)} days old]" if pr_stale(x) else "") for x in open_prs(name, path)])
    section(".env", [f"{u}  {k} ({f})" for k, u, f in env_urls(path)])
    section("Extra ([links])", [f"{u}  {k}" for k, u in ((man or {}).get("links") or {}).items()])
    if footer:
        L.extend(["", f"keys: {HINT}   (drag to select and copy)"])
    return "\n".join(L)


DIVIDER = "─" * 44


def menu_overview():
    """kk in the hyperbeam session: for each open project its status line, its full kk detail, then a divider. Then notes (projects whose last session crashed)."""
    mans = load_manifests()
    open_names = [session_project(x) for x in stack() if x != MENU]
    rows = scan() if any(n not in mans for n in open_names) else []
    items = []
    for name in open_names:
        st = project_status(name, mans.get(name)) or ("none", "not running")
        items.append((["red", "blue", "cyan", "green", "none"].index(st[0]), name, st))
    L = []
    reds = [(n, st) for _, n, st in sorted(items) if st[0] == "red"]
    if reds:
        L += [RED_ANSI + "PROBLEMS" + RESET_ANSI] + [RED_ANSI + f"  {n}: {st[1]}" + RESET_ANSI for n, st in reds] + [""]
    L += ["hyperbeam: open projects", ""]
    for _, name, st in sorted(items):
        L += [f"[{st[0]}] {name}: {st[1]}", "", project_info(name, rows, footer=False, alert=False), "", DIVIDER, ""]
    if not items:
        L += ["(no project is open)", ""]
    notes = [(n, crash_note(n)) for n in sorted(mans) if crash_note(n)]
    if notes:
        L += ["Notes (cleared when the project is opened)"] + [f"  {n}: {t}" for n, t in notes] + [""]
    L += [f"keys: {HINT}   (drag to select and copy)"]
    return "\n".join(L)


def cmd_info(a):
    name = a.project or os.environ.get("HB_PROJECT")
    if not name:
        here = own_session()
        name = next((n for n in [*load_manifests(), *(r["name"] for r in scan())] if sanitize(n) == here), None)
    if not name:
        sys.exit("hyperbeam info: no project (run it in a project session, or give a name)")
    print(menu_overview() if sanitize(name) == MENU else project_info(name))


# ---------- CLI ----------
def cmd_scan(_):
    mans = load_manifests()
    rows = scan()
    hdr = ["name", "path", "owner", "uncommitted", "manifest"]
    data = [[r["name"], home_rel(r["path"]), r["owner"], "y" if r["dirty"] else "n",
             "y" if r["name"] in mans else "n"] for r in rows]
    w = [max(len(x[i]) for x in data + [hdr]) for i in range(len(hdr))]
    for line in [hdr] + data:
        print("  ".join(c.ljust(w[i]) for i, c in enumerate(line)).rstrip())


def cmd_open(args):
    sess = sanitize(args.name)
    row = next((r for r in scan() if r["name"] == args.name), None)
    man = load_manifests().get(args.name)
    if row is None and man is None and sess != MENU:
        sys.exit(f"hyperbeam: no project called {args.name} (try `hyperbeam scan`)")
    path = known_path(args.name) if (man or row) else HERE
    open_project(args.name, path, man, ask_tty, print)
    touch_opened(args.name)
    if not args.detach:
        sys.exit(attach_here(sess))


def cmd_stop(args):
    man = load_manifests().get(args.name)
    sess = sanitize(args.name)
    if man is None and not session_exists(sess):
        sys.exit(f"hyperbeam: {args.name} has no manifest and is not running")
    if not args.force:
        r = check_project(args.name)
        if r and not wrapup_clean(r):
            print(format_wrapup(r))
            sys.exit("hyperbeam: not stopped: not clean (commit or stash, or use --force)")
    try:
        sys.exit(0 if stop_project(args.name, man) else 1)
    except RuntimeError as e:
        sys.exit(f"hyperbeam: {e}")


def cmd_warn(args):
    p = Path(args.path)
    warns = []
    if not run("git", "-C", str(p), "rev-parse", "--git-dir"):
        warns.append("no git repository")
    else:
        if not run("git", "-C", str(p), "remote"):
            warns.append("no git remote (nothing is backed up)")
    if not (p / "CLAUDE.md").exists():
        warns.append("no CLAUDE.md")
    if args.findings:
        try:
            warns = Path(args.findings).read_text().splitlines() + warns
        except OSError:
            pass
    for w in warns:
        print(f"\033[33mhyperbeam: warning: {w}\033[0m")


