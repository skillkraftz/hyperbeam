# hyperbeam, part 'sidebar': showing a session, the menu session, the stack, the sidebar window. Runs in the namespace of the `hyperbeam` script (see its loader): no imports of its own.
# ---------- showing a session ----------
def is_remote():
    return bool(os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY")) \
        or not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"))


def attach_here(sess):
    """Switch or attach in the current terminal (used over SSH and by the CLI)."""
    if os.environ.get("TMUX"):
        return subprocess.run(["tmux", "switch-client", "-t", sess]).returncode
    return subprocess.run(["tmux", "attach", "-t", sess]).returncode


# ---------- the menu session, the stack, copy ----------
def menu_client(field="client_name"):
    """The client that is looking at the menu session (the most recently active one): its name (tty) or another format field; '' if none."""
    rows = [l.split(None, 1) for l in tmux("list-clients", "-t", f"={MENU}", "-F", "#{client_activity} #{" + field + "}",
                                          check=False).stdout.splitlines()]
    rows = [r for r in rows if len(r) == 2]
    return max(rows, key=lambda r: int(r[0]))[1] if rows else ""


def display_env():
    """Environment for a GUI program started from the tmux server (which may have been started over SSH): remove TMUX, find the Wayland socket."""
    env = dict(os.environ)
    env.pop("TMUX", None)
    rt = env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    if not env.get("WAYLAND_DISPLAY") and not env.get("DISPLAY"):
        socks = [x for x in sorted(Path(rt).glob("wayland-[0-9]*")) if not x.name.endswith(".lock")]
        if socks:
            env["WAYLAND_DISPLAY"] = socks[0].name
    return env


def kitty_guard():
    if os.environ.get("HB_CONFIG") and not os.environ.get("HB_KITTY_ARGS"):      # a test config: never pop a window on the user's screens
        raise RuntimeError("test configuration (HB_CONFIG) in use: refusing to open a real window")


def spawn_kitty(sess):
    """open_mode = "window": a new kitty window attached to the session. HB_KITTY_ARGS adds kitty options (used by tests)."""
    kitty_guard()
    subprocess.Popen(["kitty", "--title", f"hyperbeam: {sess}", *shlex.split(os.environ.get("HB_KITTY_ARGS", "")),
                      "tmux", "attach", "-t", f"={sess}"],
                     env=display_env(), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


# ---------- the sidebar: one kitty window, the menu on the left, a tmux client on the right ----------
SIDEBAR_FILE = STATE_DIR / "sidebar.json"


def sidebar_read():
    try:
        return json.loads(SIDEBAR_FILE.read_text())
    except (OSError, ValueError):
        return {}


def sidebar_update(**kv):
    d = {**sidebar_read(), **kv}
    SIDEBAR_FILE.parent.mkdir(parents=True, exist_ok=True)
    SIDEBAR_FILE.write_text(json.dumps(d))


def sidebar_client():
    """The tmux client of the sidebar's right side (its tty, recorded by `hyperbeam _right` before it execs `tmux attach`), '' if it isn't attached."""
    tty = sidebar_read().get("tty")
    return tty if tty and tty in tmux("list-clients", "-F", "#{client_tty}", check=False).stdout.split() else ""


def client_sessions():
    """{client tty: the session it looks at} for every tmux client."""
    return dict(l.split(" ", 1) for l in tmux("list-clients", "-F", "#{client_tty} #{client_session}", check=False).stdout.splitlines() if " " in l)


def home_target(client):
    """Where a client goes when it goes to the hyperbeam session: the sidebar's right client sees `home` (Claude and a shell), others the menu."""
    return f"={MENU}:{'home' if client and client == sidebar_read().get('tty') else 'menu'}"


def sidebar_session_file(cols=170, rows=48):
    """A kitty session: one OS window, `splits` layout, the menu on the left (menu_width columns; --bias is the percentage the new right window takes),
    the tmux client (`hyperbeam _right`) on the right. The menu runs in a loop: exit code 0 (Quit) ends it, anything else (a restart signal
    from `hyperbeam update`, a crash) starts it again."""
    w = cfg_get("menu_width")
    bias = round(100 * (cols - w - 1) / (cols - 1))
    loop = f"while :; do {SELF} _menu; [ $? -eq 0 ] && break; sleep 1; done"
    return "\n".join([
        "os_window_class hyperbeam-sidebar", f"os_window_size {cols}c {rows}c", "layout splits",
        shlex.join(["launch", "--title", "menu", "--env", "HB_SIDEBAR=1", "sh", "-c", loop]), "focus",
        shlex.join(["launch", "--location=vsplit", f"--bias={bias}", "--title", "main", str(HERE / "hyperbeam"), "_right"]), ""])


def sidebar_possible():
    """Sidebar mode applies at the desktop only: not over SSH, and there must be a screen to open on."""
    if open_mode() != "sidebar" or os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY") or os.environ.get("TMUX"):
        return False
    env = display_env()
    return bool(env.get("WAYLAND_DISPLAY") or env.get("DISPLAY")) and (not sys.stdin.isatty() or bool(os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")))


def pid_alive(pid, word):
    try:
        return word in Path(f"/proc/{pid}/cmdline").read_text()
    except (OSError, ValueError):
        return False


def sidebar_menu_alive():
    """Is a sidebar menu process (pid file written by run_menu) running?"""
    for f in MENU_PIDS.glob("*"):
        try:
            if json.loads(f.read_text()).get("sidebar") and Path(f"/proc/{int(f.name)}").exists():
                return True
        except (OSError, ValueError):
            pass
    return False


def sidebar_healthy(grace=8):
    """Both halves of an open sidebar window are there: the menu (left) and the tmux client (right). A window that was opened a moment ago
    is given time to start; a menu between two restarts gets a few seconds."""
    if time.time() - sidebar_read().get("started", 0) < grace:
        return True
    for _ in range(6):
        if sidebar_client() and sidebar_menu_alive():
            return True
        time.sleep(0.5)
    return False


def close_sidebar(wait=3.0):
    """Close the whole sidebar kitty window (both halves): remote control (close all its tabs), else SIGTERM to that kitty (its pid is checked
    to be the sidebar's). The tmux sessions are not touched: the right client just detaches. Returns True if the window is gone."""
    kp = sidebar_read().get("kitty_pid", 0)
    if not pid_alive(kp, "hyperbeam-sidebar"):
        return True
    try:
        kitten_sidebar("close-tab", "--match", "all", check=False)
    except (OSError, subprocess.SubprocessError):
        pass
    end = time.time() + wait
    while time.time() < end and pid_alive(kp, "hyperbeam-sidebar"):
        time.sleep(0.2)
    if pid_alive(kp, "hyperbeam-sidebar"):
        os.kill(kp, signal.SIGTERM)
        end = time.time() + wait
        while time.time() < end and pid_alive(kp, "hyperbeam-sidebar"):
            time.sleep(0.2)
    return not pid_alive(kp, "hyperbeam-sidebar")


def cmd_close_sidebar(_):
    time.sleep(1)           # the menu that asked is inside the window: let it finish its last message
    close_sidebar()


def launch_sidebar():
    """Open the sidebar kitty window (once: if one is open and whole, say so; a half-open one, menu without the right side or the reverse,
    is closed and opened again). The hyperbeam session is created first so both sides find it."""
    kitty_guard()
    ensure_menu()
    source_conf()
    repaired = False
    if pid_alive(sidebar_read().get("kitty_pid", 0), "hyperbeam-sidebar"):
        if sidebar_healthy():
            return "the sidebar window is already open"
        if not close_sidebar():
            return "the sidebar window is half open and could not be closed: close it by hand, then press the hotkey again"
        repaired = True
    f = STATE_DIR / "sidebar.session"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(sidebar_session_file())
    proc = subprocess.Popen(["kitty", "--class", "hyperbeam-sidebar", "--title", "hyperbeam", *shlex.split(os.environ.get("HB_KITTY_ARGS", "")),
                             "-o", "allow_remote_control=socket-only", "-o", "enabled_layouts=splits,stack", "--listen-on", f"unix:{display_env()['XDG_RUNTIME_DIR']}/hyperbeam-sidebar",
                             "--session", str(f)],
                            env=display_env(), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    sidebar_update(kitty_pid=proc.pid, started=time.time(), tty="")
    return "the sidebar window was half open: closed it and opened a new one" if repaired else "opened the sidebar window"


SIDEBAR_SOCK = lambda: f"unix:{display_env()['XDG_RUNTIME_DIR']}/hyperbeam-sidebar"


def kitten_sidebar(*args, check=True):
    """`kitten @ --to <the sidebar kitty's socket> ...` (that kitty only: see launch_sidebar)."""
    return subprocess.run(["kitten", "@", "--to", SIDEBAR_SOCK(), *args], capture_output=True, text=True, timeout=8, check=check)


def sidebar_toggle():
    """M-s / the Hide button: switch the sidebar kitty's layout between `splits` (menu left, main right) and `stack` (only the focused window,
    the main side, full width). Nothing is closed: the menu keeps running behind. Returns what it did."""
    try:
        tabs = [t for ow in json.loads(kitten_sidebar("ls").stdout) for t in ow.get("tabs", [])]
    except (OSError, ValueError, subprocess.SubprocessError):
        return "the sidebar window can't be controlled (open it again once: it was started before this version)"
    if not tabs:
        return "no sidebar window"
    hidden = tabs[0].get("layout") == "stack"
    try:
        if hidden:
            kitten_sidebar("goto-layout", "splits")
            return "sidebar shown"
        kitten_sidebar("focus-window", "--match", "title:^main$")
        kitten_sidebar("goto-layout", "stack")
        return "sidebar hidden (M-s shows it)"
    except (OSError, subprocess.SubprocessError) as e:
        return f"sidebar toggle failed: {(getattr(e, 'stderr', '') or e)!s:.80}"


def cmd_sidebar(a):
    msg = sidebar_toggle()
    if a.client:
        tmux_msg(a.client, msg)
    else:
        print(msg)


