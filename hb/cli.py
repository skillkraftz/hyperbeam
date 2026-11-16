# hyperbeam, part 'cli': update / try, the argparse main(). Runs in the namespace of the `hyperbeam` script (see its loader): no imports of its own.
# ---------- update / try ----------
def repo_state():
    """(branch, commits origin/main is ahead) of the hyperbeam checkout, from what was last fetched (no network)."""
    br = git_out(HERE, "rev-parse", "--abbrev-ref", "HEAD")
    behind = git_out(HERE, "rev-list", "--count", "HEAD..origin/main") if br == "main" else ""
    return br, int(behind) if behind.isdigit() else 0


def repo_note():
    """('branch'|'behind'|'', long text) for the hyperbeam row."""
    br, behind = repo_state()
    if br and br != "main":
        return "branch", f"on branch {br}: `hyperbeam update` goes back to main"
    if behind:
        return "behind", f"origin/main is {behind} commit{'s' * (behind > 1)} ahead: press Update"
    return "", ""


def nudge_menus():
    """SIGUSR2 to every running menu that handles it: it re-reads the PR cache at once (`hyperbeam refresh-prs`)."""
    for f in sorted(MENU_PIDS.glob("*")):
        try:
            if json.loads(f.read_text()).get("usr2") and pid_alive(int(f.name), "_menu"):
                os.kill(int(f.name), signal.SIGUSR2)
        except (OSError, ValueError):
            pass


def restart_menus(say=print):
    """Restart the menu processes without touching a project session. Sidebar menus: SIGUSR1 (they exit 75, their loop starts a new one).
    The in-tmux menu: its pane is respawned; the old layout (menu, Claude, shell in one window) gets a `menu` window and loses its menu pane."""
    n = 0
    for f in sorted(MENU_PIDS.glob("*")):
        try:
            info = json.loads(f.read_text())
            pid = int(f.name)
        except (OSError, ValueError):
            continue
        if not pid_alive(pid, "_menu"):
            f.unlink(missing_ok=True)
        elif info.get("sidebar") and info.get("home") == str(HERE):
            os.kill(pid, signal.SIGUSR1)
            n += 1
    if n:
        say(f"menu: restarted {n} sidebar menu process{'es' * (n > 1)}")
    if not session_exists(MENU):
        return
    own = os.environ.get("TMUX_PANE", "")
    rows = [l.split("\t") for l in tmux("list-panes", "-s", "-t", f"={MENU}", "-F", "#{pane_id}\t#{window_name}\t#{pane_start_command}\t#{window_id}",
                                        check=False).stdout.splitlines()]
    menus = [r for r in rows if len(r) == 4 and "_menu" in r[2] and "sh -c" not in r[2]]
    if not any(r[1] == "menu" for r in rows):
        tmux("new-window", "-d", "-t", f"={MENU}:", "-n", "menu", "-c", str(HERE), menu_cmd(), check=False)
        for pane, win, _, wid in menus:
            if pane != own and sum(1 for r in rows if r[3] == wid) > 1:
                tmux("kill-pane", "-t", pane, check=False)
                tmux("rename-window", "-t", wid, "home", check=False)
        say("menu: old single-window layout converted (new `menu` window; the old window is now `home`)")
    else:
        for pane, win, _, _ in menus:
            if pane != own:
                tmux("respawn-pane", "-k", "-t", pane, menu_cmd(), check=False)
                say("menu: in-tmux menu restarted")


def claude_panes():
    """Every Claude pane in a hyperbeam session: [(pane id, session, project, cwd, state)]; state is waiting (idle, blue), working or ''."""
    out = []
    fmt = "#{pane_id}\t#{session_name}\t#{pane_current_command}\t#{pane_current_path}\t#{@hb}"
    for l in tmux("list-panes", "-a", "-F", fmt, check=False).stdout.splitlines():
        pane, sess, cmd, path, hb = (l.split("\t") + [""] * 5)[:5]
        if cmd == "claude" and hb == "1":
            proj = session_project(sess)
            out.append((pane, sess, proj, path, claude_state(proj)[0]))
    return out


def restart_claude(pane, path, manager=False):
    """Restart Claude in a pane with --continue: the pane gets a fresh shell in its directory, then the command is typed (the manager's own command for the manager)."""
    tmux("respawn-pane", "-k", "-t", pane, "-c", path, check=False)
    send_line(pane, manager_cmd(cont=True) if manager else f"{claude_base()} --continue || {claude_base()}")


def do_update(branch=None, yes=False):
    """`hyperbeam update` (main) / `hyperbeam try BRANCH`: switch the hyperbeam checkout, then (with the new code) `_update-finish`."""
    repo = HERE
    if git_out(repo, "status", "--porcelain", "--untracked-files=no"):
        print(f"{repo} has uncommitted changes: commit or stash them first (nothing was changed)")
        return 1
    old, oldb = git_out(repo, "rev-parse", "--short", "HEAD"), git_out(repo, "rev-parse", "--abbrev-ref", "HEAD")
    git_fetch(repo)
    target = branch or "main"
    if target != oldb:
        r = subprocess.run(["git", "-C", str(repo), "checkout", "-q", target], capture_output=True, text=True)
        if r.returncode:
            print(f"cannot check out {target}: {r.stderr.strip()}")
            return 1
    if git_out(repo, "rev-parse", "--verify", "-q", f"origin/{target}"):
        r = subprocess.run(["git", "-C", str(repo), "merge", "--ff-only", "-q", f"origin/{target}"], capture_output=True, text=True)
        if r.returncode:
            print(f"{target} has local commits that are not on origin/{target}; not merged: {r.stderr.strip()}")
    new, newb = git_out(repo, "rev-parse", "--short", "HEAD"), git_out(repo, "rev-parse", "--abbrev-ref", "HEAD")
    print(f"hyperbeam: {oldb} {old} -> {newb} {new}" + ("" if old != new or oldb != newb else "  (already up to date)"))
    if old != new:
        print(git_out(repo, "log", "--oneline", "-15", f"{old}..{new}") or git_out(repo, "log", "--oneline", "-5", new))
    sys.stdout.flush()
    return subprocess.run([str(repo / "hyperbeam"), "_update-finish"] + (["--yes"] if yes else [])).returncode


def link_kk():
    """~/.local/bin/kk (HB_BIN) must point at this (installed) script: relink an old link (it used to point at the dev folder); make it when missing;
    leave a real file alone. -> a message or ''."""
    kk, target = Path(os.environ.get("HB_BIN") or Path.home() / ".local/bin") / "kk", HERE / "hyperbeam"
    if kk.is_symlink():
        if os.readlink(kk) == str(target):
            return ""
        was = os.readlink(kk)
    elif kk.exists():
        return f"{kk} is not a link: left alone"
    else:
        was = None
    kk.parent.mkdir(parents=True, exist_ok=True)
    tmp = kk.with_name(".kk.new")
    tmp.unlink(missing_ok=True)
    tmp.symlink_to(target)
    tmp.replace(kk)
    return f"kk: linked to {target}" + (f" (was {was})" if was else "")


def cmd_update_finish(a):
    """The steps after the checkout, run by the new code: hooks, tmux config, menus, Claude panes."""
    print(link_kk() or "kk: link is current")
    print("hooks: " + (", ".join(install_hooks()) and "updated" or "already current"))
    for m in hook_summary_for_update():
        print(m)
    if tmux("source-file", "-q", str(HERE / "hyperbeam.conf"), check=False).returncode == 0 and tmux("has-session", check=False).returncode == 0:
        print("tmux: hyperbeam.conf reloaded")
    else:
        print("tmux: no server running, nothing to reload")
    if session_exists(MENU):
        for sess in stack():
            tag_session(sess)       # refresh the key hints in the status bars
            refresh_claude_pane(sess)
    restart_menus()
    own = os.environ.get("TMUX_PANE", "")
    panes = claude_panes()
    if not panes:
        return 0
    print(f"\nClaude panes still running from before the update ({len(panes)}; they keep the old hooks and settings until restarted):")
    for pane, sess, proj, path, state in panes:
        print(f"  {proj:<22} {'idle (blue)' if state == 'waiting' else 'working' if state == 'working' else 'unknown':<12} {pane}{'  (this one: not touched)' if pane == own else ''}")
    idle = [x for x in panes if x[4] == "waiting" and x[0] != own]
    if not idle:
        return 0
    ok = a.yes
    if not ok and sys.stdin.isatty():
        ok = input(f"Restart the {len(idle)} idle one(s) with --continue? [y/N] ").strip().lower() == "y"
    if ok:
        for pane, sess, proj, path, _ in idle:
            restart_claude(pane, path, manager=sess == MENU)
            print(f"  restarted {proj}")
    else:
        print("  not restarted (restart working ones yourself when they finish)")
    return 0


def main():
    ap = argparse.ArgumentParser(prog="hyperbeam", description=__doc__)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("scan", help="list projects").set_defaults(f=cmd_scan)
    o = sub.add_parser("open", help="start a project's session and attach in this terminal")
    o.add_argument("name")
    o.add_argument("-d", "--detach", action="store_true", help="start the session but do not attach")
    o.set_defaults(f=cmd_open)
    s = sub.add_parser("stop", help="run stop commands, kill the session, check the ports")
    s.add_argument("name")
    s.add_argument("--force", action="store_true", help="skip the wrap-up check")
    s.set_defaults(f=cmd_stop)
    sub.add_parser("list", help="numbered list of running sessions with URLs; a number switches to it").set_defaults(f=cmd_list)
    sub.add_parser("phone", help="print the URLs, then attach to the most recently used session").set_defaults(f=cmd_phone)
    i = sub.add_parser("info", help="URLs and endpoints of a project (alias: kk)")
    i.add_argument("project", nargs="?")
    i.set_defaults(f=cmd_info)
    sub.add_parser("_menu").set_defaults(f=lambda _: run_menu())
    en = sub.add_parser("_entered")
    en.add_argument("client")
    en.add_argument("session")
    en.set_defaults(f=cmd_entered)

    sub.add_parser("_right", help="the sidebar's right side: record this tty, exec tmux attach").set_defaults(f=cmd_right)
    hm = sub.add_parser("_home")
    hm.add_argument("client")
    hm.set_defaults(f=cmd_home)
    up = sub.add_parser("update", help="pull main, reinstall hooks, reload tmux, restart the menu, offer to restart idle Claude panes")
    up.add_argument("--yes", action="store_true", help="restart the idle Claude panes without asking")
    up.set_defaults(f=lambda a: do_update(None, a.yes))
    tr = sub.add_parser("try", help="like update, but check out BRANCH in the hyperbeam checkout (`hyperbeam update` returns to main)")
    tr.add_argument("branch")
    tr.add_argument("--yes", action="store_true")
    tr.set_defaults(f=lambda a: do_update(a.branch, a.yes))
    uf = sub.add_parser("_update-finish")
    uf.add_argument("--yes", action="store_true")
    uf.set_defaults(f=cmd_update_finish)
    st = sub.add_parser("_stack")
    st.add_argument("direction", choices=["next", "prev"])
    st.add_argument("client")
    st.add_argument("session")
    st.set_defaults(f=cmd_stack)
    cp = sub.add_parser("_copy-pane")
    cp.add_argument("client_pid")
    cp.add_argument("client")
    cp.add_argument("pane")
    cp.add_argument("session")
    cp.set_defaults(f=cmd_copy_pane)
    cl = sub.add_parser("_clip")
    cl.add_argument("client_pid")
    cl.set_defaults(f=cmd_clip)
    w = sub.add_parser("_warn")
    w.add_argument("path")
    w.add_argument("--findings")
    w.set_defaults(f=cmd_warn)
    ck = sub.add_parser("_check", help="print the start check's findings for a directory")
    ck.add_argument("path")
    ck.add_argument("--fetch", action="store_true")
    ck.set_defaults(f=lambda a: print("\n".join(git_problems(a.path, a.fetch)) or "(nothing found)"))
    wc = sub.add_parser("_wrapup", help="print the wrap-up check for a directory")
    wc.add_argument("path")
    wc.add_argument("--since", type=float)
    wc.add_argument("--all", action="store_true", help="scan every tracked file too (pattern testing; counts only with --counts)")
    wc.add_argument("--counts", action="store_true")
    wc.set_defaults(f=cmd_wrapup)
    hk = sub.add_parser("_hooks", help="merge hyperbeam's Claude hooks (waiting state, the Bash guard) into ~/.claude/settings.json")
    hk.add_argument("--settings")
    hk.set_defaults(f=lambda a: (print("hooks updated: " + (", ".join(install_hooks(a.settings)) or "already installed")), [print(m) for m in hook_summary_for_update()], 0)[2])
    af = sub.add_parser("align-facts", help="the facts ALIGN.md compares a project's docs against (visibility, docs layout, tests, ignores)")
    af.add_argument("path", nargs="?")
    af.set_defaults(f=cmd_align_facts)
    wk = sub.add_parser("work", help="the manager's: start a worker (a fresh Claude, session claude-NAME) in a project with WORKER.md + the prompt file; one per project")
    wk.add_argument("name")
    wk.add_argument("prompt_file")
    wk.set_defaults(f=cmd_work)
    wt = sub.add_parser("wait", help="the manager's: block until the named workers have finished, then print each one's report path (exit 1 on timeout, 2 if one is blocked)")
    wt.add_argument("names", nargs="+")
    wt.add_argument("--timeout", type=int, default=0, help="seconds (default: no limit)")
    wt.set_defaults(f=cmd_wait)
    sd = sub.add_parser("send", help="the manager's: paste a file (or - for stdin) into a finished worker's Claude and press Enter, for review feedback; refuses while it works")
    sd.add_argument("name")
    sd.add_argument("file")
    sd.set_defaults(f=cmd_send)
    cl = sub.add_parser("close", help="the manager's: end a project's worker session (claude-NAME); never the user's session")
    cl.add_argument("name")
    cl.set_defaults(f=cmd_close)
    sub.add_parser("status", help="running sessions and the state of their workers").set_defaults(f=cmd_status)
    sub.add_parser("_worker-report").set_defaults(f=cmd_worker_report)
    rf = sub.add_parser("refresh-prs", help="fetch a project's open PRs now so the sidebar's Merge button is right at once; run it after gh pr create (with the number) and after a merge; default project $HB_PROJECT")
    rf.add_argument("project", nargs="?")
    rf.add_argument("numbers", nargs="*", help="PR numbers just opened (looked up directly: GitHub's list lags a few seconds)")
    rf.add_argument("--gone", nargs="*", default=[], metavar="NUMBER", help="PR numbers just merged or closed (GitHub's list still shows them for a few seconds)")
    rf.set_defaults(f=cmd_refresh_prs)
    rp = sub.add_parser("copy-last", help="copy Claude's last message of a project's session (the PR report) to the clipboard; default project $HB_PROJECT")
    rp.add_argument("project", nargs="?")
    rp.add_argument("--print", action="store_true")
    rp.set_defaults(f=cmd_copy_last)
    rs = sub.add_parser("reports", help="one row per worker report: task, branch, PR, commits, tokens, calls, active minutes, lab seconds, and a total")
    rs.add_argument("names", nargs="*", metavar="NAME")
    rs.add_argument("--since", metavar="DATE", help="only reports from this day on (YYYY-MM-DD)")
    rs.add_argument("--since-refactor", action="store_true", help="only reports after the last one whose task mentions refactor, cleanup or audit")
    rs.set_defaults(f=cmd_reports)
    sub.add_parser("report", help=argparse.SUPPRESS).set_defaults(f=lambda a: sys.exit("hyperbeam report was renamed: `hyperbeam copy-last` copies Claude's last message, `hyperbeam reports` lists the workers' reports"))
    cx = sub.add_parser("context", help="copy a context bundle (RULES, CLAUDE.md, DECISIONS, README, manifest, recent history) to paste into a chat; default project $HB_PROJECT")
    cx.add_argument("project", nargs="?")
    cx.add_argument("--print", action="store_true", help="print it instead of copying")
    cx.add_argument("--size", action="store_true", help="show the size of each part (bytes, rough tokens) instead of the bundle")
    cx.add_argument("--full", action="store_true", help="also include docs/REFERENCE.md (the long reference moved out of CLAUDE.md)")
    cx.set_defaults(f=cmd_context)
    mg = sub.add_parser("_migrate-config", help="copy an old repo config.toml's values to ~/.config/hyperbeam/config.toml (once)")
    mg.add_argument("legacy", nargs="?")
    mg.set_defaults(f=lambda a: print(f"wrote {CONFIG_FILE}" if migrate_config(a.legacy) else f"nothing to do ({CONFIG_FILE} exists or no old file)"))
    lb = sub.add_parser("lab", help="agent testing as the user hblab on a disk image: run | reset | status (set up with lab/setup.sh)")
    lsub = lb.add_subparsers(dest="action", required=True)
    lr = lsub.add_parser("run", help="copy a directory into the lab and run a command there")
    lr.add_argument("--dir", help="directory to copy (default: the current one)")
    lr.add_argument("--name", help="name of the run directory (default: the directory's name)")
    lr.add_argument("--why", help="a short reason for this run (goes in the run log)")
    lr.add_argument("--collect", metavar="PATH", help="after the run, copy PATH (inside the project's lab copy, or an absolute lab path) back to ~/.cache/hyperbeam-shots/<time>/")
    lr.add_argument("--fresh", action="store_true", help="wipe this project's synced copy (and what the lab installed in it) first")
    lr.add_argument("--timeout", type=int, default=600, help="seconds before the command is stopped (default 600)")
    lr.add_argument("cmd", nargs=argparse.REMAINDER)
    lst = lsub.add_parser("stop", help="stop this project's active lab runs (and what they started); other projects' runs are not touched")
    lst.add_argument("project", nargs="?", help="default: the project of the current folder, else $HB_PROJECT")
    lrs = lsub.add_parser("reset", help="stop YOUR project's runs and clear leftover run files; refuses while other projects have runs (keeps synced projects and caches)")
    lrs.add_argument("--all", action="store_true", help="also wipe the synced projects and the caches")
    lrs.add_argument("--force", action="store_true", help="the user only: kill everything hblab runs, other projects' runs and the display too")
    dg = lsub.add_parser("digest", help="what the lab runs show: flaky commands, slowest, repeated work (tool candidates); plain text, no Claude")
    dg.add_argument("--today", action="store_true")
    dg.add_argument("--since", help="YYYY-MM-DD")
    dg.add_argument("--no-tests", action="store_true", help="do not run the tools' tests")
    lg = lsub.add_parser("log", help="the lab run log: what ran, why, how long")
    lg.add_argument("--today", action="store_true")
    lsub.add_parser("status", help="disk use, synced projects, caches, processes")
    lb.set_defaults(f=cmd_lab)
    ms = sub.add_parser("_migrate-state", help="copy ~/.local/state/hyperbeam into the per-project layout under ~/.local/share/hyperbeam (also runs by itself)")
    ms.add_argument("old", nargs="?")
    ms.set_defaults(f=lambda a: print("migrated %d files%s" % ((lambda r: (r[0], f"; problems: {r[1]}" if r[1] else "; old folder removed"))(migrate_state(a.old)))))
    tl = sub.add_parser("tool", help="run a tool of tools/ in the lab, in this project's synced copy (--list: TOOLS.md, --test [NAME]: their tests)")
    tl.add_argument("--list", action="store_true")
    tl.add_argument("--test", action="store_true")
    tl.add_argument("--dir", help="the project folder to run in (default: the current directory)")
    tl.add_argument("--timeout", type=int, default=600)
    tl.add_argument("name", nargs="?")
    tl.add_argument("args", nargs=argparse.REMAINDER)
    tl.set_defaults(f=cmd_tool)
    vf = sub.add_parser("verify", help="check what only your own accounts and machine can show (gh logins, hooks, lab, home permissions); prints PASS/FAIL/YOU with the exact command")
    vf.add_argument("what", nargs="?", choices=["all", "github", "hooks", "lab", "merge"], default="all")
    vf.set_defaults(f=cmd_verify)
    nw = sub.add_parser("new", help="a new project that conforms from the first commit: README, CLAUDE.md, DECISIONS.md, manifest, and version/help/update/install built in")
    nw.add_argument("name")
    nw.add_argument("--cli", action="store_true", help="a Python (uv) command line tool (the default)")
    nw.add_argument("--web", action="store_true", help="a Node web app with /version")
    nw.add_argument("--about", help="one line: what it is")
    nw.add_argument("--no-open", action="store_true", help="do not start its session")
    nw.set_defaults(f=cmd_new)
    us = sub.add_parser("usage", help="what the 5-hour windows cost, from Claude Code's conversation files (plain script)")
    us.add_argument("--today", action="store_true")
    us.add_argument("--week", action="store_true")
    us.add_argument("--all", action="store_true")
    us.set_defaults(f=cmd_usage)
    sh_ = sub.add_parser("shot", help="pictures of the sidebar at a given width, made in the lab and brought back to ~/.cache/hyperbeam-shots/")
    sh_.add_argument("--cols", type=int, default=35, help="menu width in columns (default 35)")
    sh_.add_argument("--rows", type=int, default=40)
    sh_.add_argument("--phone", action="store_true", help="42 columns, what the phone shows")
    sh_.add_argument("--screen", choices=["all", *SHOT_SCREENS], default="all")
    sh_.add_argument("--dir", help="draw this checkout's sidebar (a dev folder or a worktree, to see a branch) instead of the installed copy")
    sh_.set_defaults(f=cmd_shot)
    sr = sub.add_parser("_shot-render")
    sr.add_argument("--cols", type=int, default=35)
    sr.add_argument("--rows", type=int, default=40)
    sr.add_argument("--out", required=True)
    sr.add_argument("--screens", type=lambda v: v.split(","), default=SHOT_SCREENS)
    sr.set_defaults(f=cmd_shot_render)
    sub.add_parser("_close-sidebar").set_defaults(f=cmd_close_sidebar)
    sb = sub.add_parser("sidebar", help="hide / show the sidebar (the same as M-s)")
    sb.add_argument("client", nargs="?")
    sb.set_defaults(f=cmd_sidebar)
    sv = sub.add_parser("_save")
    sv.add_argument("session", nargs="?")
    sv.set_defaults(f=cmd_save)
    argv = sys.argv[1:]
    if argv and argv[0] not in sub.choices and ("/" in argv[0] or argv[0] in (".", "~")) and Path(argv[0]).expanduser().is_dir():
        # `hyperbeam <dir>`: that folder's projects for this run (the sidebar and its menu inherit it through the environment)
        global ROOT
        ROOT = Path(argv[0]).expanduser().resolve()
        os.environ["HB_PROJECTS_DIR"] = str(ROOT)
        argv = argv[1:]
    try:
        _done, _bad = migrate_state() if (not argv or argv[0] not in ("lab", "tool", "shot", "_shot-render") and not (len(argv) > 1 and argv[1] == "test")) else (0, [])      # `lab` commands run as the user: never touch state
        if _bad:
            print("hyperbeam: could not migrate the old state folder; it was left in place:\n  " + "\n  ".join(_bad[:5]), file=sys.stderr)
    except OSError as e:
        print(f"hyperbeam: state migration failed: {e}", file=sys.stderr)
    if argv and argv[0] not in sub.choices and not argv[0].startswith("-") and "/" not in argv[0] and project_exists(argv[0]):
        name = argv[0]                          # `hyperbeam NAME VERB`: a standard verb of that project; `hyperbeam NAME`: open it
        if len(argv) >= 2 and argv[1] in VERBS:
            sys.exit(cmd_project_verb(name, argv[1]))
        if len(argv) == 1:
            argv = ["open", name]
    if Path(sys.argv[0]).name == "kk":      # ~/.local/bin/kk is a symlink to this script
        argv = ["info", *argv]
    a = ap.parse_args(argv)
    if a.cmd is None:
        cmd_menu(a)
    else:
        sys.exit(a.f(a) or 0)
