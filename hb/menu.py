# hyperbeam, part 'menu': the Textual menu. Runs in the namespace of the `hyperbeam` script (see its loader): no imports of its own.
# ---------- the menu ----------
def project_summary(name, path, st=None, prs=None):
    """The Project screen as short lines (the screen truncates each with an ellipsis; the full texts are in the Info window and the notes folder).
    (Computed in a worker thread.)"""
    path = Path(path)
    man = load_manifests().get(name)
    sess = sanitize(name)
    running = session_exists(sess)
    br = branch_of(path)
    L = [f"{name}" + (f"  {br}" if br not in ("-", "main", "master") else ""),
         "  ".join(x for x in (str(man["port"]) if man and man.get("port") else "", "running" if running else "stopped", "" if man else "no manifest") if x)]
    if man and man.get("service"):
        ports = {p: (proc, lo) for p, proc, lo in session_listeners(sess)} if running else {}
        L.append("services: " + ", ".join(f"{n} {s_}" for n, s_, d in service_states(sess, man, ports)))
    prs = prs if prs is not None else open_prs(name, path)
    L.append("PR: " + (f"#{prs[0]['number']} {prs[0]['title']}" + (" [stale]" if pr_stale(prs[0]) else "") + (f" (+{len(prs) - 1})" if len(prs) > 1 else "") if prs else "none"))
    red = red_findings(name, man) if running else []
    notes = note_findings(name) if running else []
    L.append("problems: " + ("none" if not red else ""))
    L += [f"  ! {x}" for x in red]
    L.append(f"notes: {len(notes) or 'none'}")
    L += [f"  - {x}" for x in notes[:3]] + ([f"  ... +{len(notes) - 3} more (Info window)"] if len(notes) > 3 else [])
    when = onboarded_on(name, path)
    drift = next((x for x in (notes if running else drift_notes(name, path)) if x.startswith("setup changed")), "")
    stale = next((x for x in (notes if running else stale_doc_notes(name, path)) if x.startswith("docs may be stale")), "")
    L.append("set up " + (when.split(" ")[0][5:] if when else ("never" if not man else "?")) + (" drift" if drift else "") + (" docs stale" if stale else ""))
    nd = project_dir(name, path) / "notes"
    nf = sorted(nd.glob("*.md")) if nd.is_dir() else []
    if nf:
        L.append(f"notes folder: {len(nf)}, latest {nf[-1].name}")
    try:
        L.append(verbs_summary(name, path))
    except Exception:
        pass
    try:
        rl = rate_limits()
        if rl and rl.get("five_hour"):
            L.append(usage_window_text(rl["five_hour"], "five_hour", rl.get("at"), short=True))
            if rl.get("seven_day"):
                L.append(usage_window_text(rl["seven_day"], "seven_day", rl.get("at"), short=True))
        else:
            L.append(usage_line())
        big = [r for r in conversation_sizes(within=6 * 3600) if r[0] == name]
        if big:
            L.append(f"context: {fmt_tok(big[0][2])} per request" + (" (very long)" if big[0][2] >= cfg_get("context_warn") else ""))
    except Exception:
        pass
    return "\n".join(L)


class ProjectScreen(ModalScreen):
    """The selected project at a glance, with the actions that belong to it. A button closes the screen and returns its name; the Menu then runs it."""
    BINDINGS = [Binding("escape", "close", "Close")]
    DEFAULT_CSS = """
    ProjectScreen { align: center top; }
    ProjectScreen > Vertical { width: 100%; max-width: 80; height: 100%; background: $surface; padding: 0 1; }
    ProjectScreen #ptext { height: 1fr; }
    ProjectScreen .pline { height: 1; }
    ProjectScreen #pbuttons { layout: grid; grid-size: 2; grid-gutter: 0 1; height: auto; margin-top: 1; }
    ProjectScreen Button { width: 1fr; height: 1 !important; border: none !important; min-width: 8; }
    """

    def __init__(self, text):
        super().__init__()
        self.text = text

    def compose(self) -> ComposeResult:
        with Vertical():
            with VerticalScroll(id="ptext"):
                w = max(20, self.app.size.width - 4)
                for line in self.text.split("\n"):
                    yield Static(clip(line, w), classes="pline", markup=False)          # cut with an ellipsis ourselves: a wrapped line would hide its tail in a 1-row Static
            with Container(id="pbuttons"):
                for bid, label in [("update", "Update"), ("install", "Install"), ("test", "Test (lab)"), ("version", "Version"), ("help_verbs", "Help"),
                                   ("edit_manifest", "Edit manifest"), ("context", "Copy context"), ("report", "Copy report"), ("info", "Info window"),
                                   ("mark_onboarded", "Mark onboarded"), ("settings", "Settings"), ("keys", "Keys"), *([("hide", "Hide sidebar")] if os.environ.get("HB_SIDEBAR") else []),
                                   ("close", "Close")]:
                    b = Button(label, id=f"pb-{bid}")
                    b.can_focus = False
                    yield b

    def on_button_pressed(self, event):
        event.stop()
        self.dismiss(event.button.id[3:] if event.button.id != "pb-close" else "")

    def action_close(self):
        self.dismiss("")


class Confirm(ModalScreen):
    BINDINGS = [Binding("y,enter", "answer(True)", "Yes"), Binding("n,escape", "answer(False)", "No")]
    DEFAULT_CSS = """
    Confirm { align: center middle; }
    Confirm > Vertical { width: 100%; max-width: 64; height: auto; max-height: 100%; border: round $accent; background: $surface; padding: 1 1; }
    Confirm #cbtns { height: auto; margin-top: 1; }
    Confirm Button { width: 100%; height: 1 !important; border: none !important; }
    """

    def __init__(self, text):
        super().__init__()
        self.text = text

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self.text, markup=False)
            with Vertical(id="cbtns"):
                yield Button("Yes (y)", id="yes")
                yield Button("No (n)", id="no")

    def on_button_pressed(self, event):
        event.stop()
        self.dismiss(event.button.id == "yes")

    def action_answer(self, value: bool):
        self.dismiss(value)


class Choice(ModalScreen):
    """Several buttons; `options` is [(id, label, key)]. The last one is also Escape."""
    DEFAULT_CSS = """
    Choice { align: center middle; }
    Choice > Vertical { width: 100%; max-width: 84; height: auto; max-height: 100%; border: round $accent; background: $surface; padding: 1 1; }
    Choice VerticalScroll { height: auto; max-height: 24; }
    Choice #cbtns { height: auto; margin-top: 1; }
    Choice Button { width: 100%; height: 1 !important; border: none !important; }
    """

    def __init__(self, text, options, enter=None):
        super().__init__()
        self.text, self.options, self.enter = text, options, enter       # `enter`: the id Enter picks (none: Enter does nothing)

    def on_key(self, event):
        if event.key == "enter" and self.enter:
            event.stop()
            self.dismiss(self.enter)
            return
        for oid, _, key in self.options:
            if event.key == key or (event.key == "escape" and oid == self.options[-1][0]):
                event.stop()
                self.dismiss(oid)
                return

    def compose(self) -> ComposeResult:
        with Vertical():
            with VerticalScroll():
                yield Static(self.text, markup=False)
            with Vertical(id="cbtns"):
                for oid, label, _ in self.options:
                    yield Button(label, id=f"c-{oid}")

    def on_button_pressed(self, event):
        event.stop()
        self.dismiss(event.button.id[2:])


DOT = {"green": "green", "red": "red", "blue": "dodger_blue1", "cyan": "cyan"}


def clip(text, width):
    return text if len(text) <= width else text[:max(0, width - 1)] + "…"


def branch_of(path):
    """Branch of a checkout, read from .git/HEAD (no git process): the name, a 6-character hash when HEAD is detached, "-" without git."""
    try:
        g = Path(path) / ".git"
        if g.is_file():
            g = Path(os.path.join(path, g.read_text().split(":", 1)[1].strip()))
        head = (g / "HEAD").read_text().strip()
    except (OSError, IndexError):
        return "-"
    if head.startswith("ref: refs/heads/"):
        return head[16:]
    return head[:6] if re.fullmatch(r"[0-9a-f]{40,64}", head) else "-"


def fit_row(name, branch, avail):
    """Name and branch within `avail` columns: the branch is shortened first (down to 6 characters, ending in …), then the name."""
    if len(name) + len(branch) <= avail:
        return name, branch
    keep = min(len(branch), max(6, avail - len(name)))
    branch = clip(branch, keep)
    return clip(name, max(1, avail - len(branch))), branch


def row_text(p, st, width, note=""):
    """One list row: dot, project, then (only when there is something to say) the branch and the port. The branch is shown only when it is not
    main/master (magenta with an open PR of yours); the port only when set (`note` replaces it on the hyperbeam row: "behind"). The branch gives way first."""
    port = str(p["port"]) if p.get("port") else ""
    pstyle = "cyan"
    if note:
        port, pstyle = note, "yellow"
    branch = p.get("branch", "-")
    show_branch = branch not in ("-", "main", "master")
    right = (" " + port) if port else ""
    avail = max(4, width - 2 - len(right) - (1 if show_branch else 0))           # the dot, the port, the space before the branch
    name, branch = fit_row(p["name"], branch if show_branch else "", avail)
    t = Text(no_wrap=True, overflow="crop")
    t.append("●" if st else " ", style=DOT.get(st[0], "") if st else "")
    t.append("»" if p.get("worker") else " ", style="bold yellow")           # a worker the manager started runs for this project
    t.append(name.ljust(avail - len(branch)), style="bold white" if p["recent"] else "grey54")
    if branch:
        t.append(" " + branch, style="#ff79c6" if p.get("prs") else "yellow")           # a light pink stays readable on the blue selected row
    t.append(right, style=pstyle)
    return t


class ProjectList(OptionList):
    """A click or tap selects; a double click or tap (Textual's click chain count 2) or Enter opens."""
    async def _on_click(self, event) -> None:
        event.prevent_default()         # Textual calls the base class handler too, unless this is called: it would select on every click
        i = event.style.meta.get("option")
        if i is None or self._options[i].disabled:
            return
        self.highlighted = i
        if event.chain >= 2:
            self.action_select()
        event.stop()


class KeysScreen(ModalScreen):
    """The key cheat sheet (it used to be under the Settings rows, which made Settings two screens long at 35 columns)."""
    BINDINGS = [Binding("escape", "close", "Close")]
    DEFAULT_CSS = """
    KeysScreen { align: center top; }
    KeysScreen > Vertical { width: 100%; max-width: 70; height: 100%; background: $surface; padding: 0 1; }
    KeysScreen #ksheet { height: 1fr; }
    KeysScreen #kclose { height: 1 !important; border: none !important; }
    """

    def compose(self) -> ComposeResult:
        lines = ["Keys are shortcuts; every action also has a button.", "", "hyperbeam keys (no prefix)"]
        lines += [f"  {k}\n      {d}" for k, d in KEYS]
        lines += ["", "your tmux keys (prefix C-a)"] + [f"  {k}\n      {d}" for k, d in USER_KEYS]
        lines += ["", "menu keys: o open, s stop, d done, u update, m merge PR, t settings, j project screen (More), c copy context, p copy report, h hide, r refresh, q quit"]
        with Vertical():
            yield Static("Keys", id="ktitle")
            with VerticalScroll(id="ksheet"):
                yield Static("\n".join(lines), markup=False)
            yield Button("Close (esc)", id="kclose")

    def on_button_pressed(self, event):
        event.stop()
        self.dismiss("")

    def action_close(self):
        self.dismiss("")


class SettingsScreen(ModalScreen):
    """Settings, a modal: it owns all input while open (App bindings don't reach past a modal; events are stopped here so they don't bubble
    to the Menu's handlers). Up/Down choose a setting, Left/Right or the - and + buttons change it, Esc or Close goes back. Values are written to config.toml."""
    BINDINGS = [Binding("escape", "close", "Close"), Binding("up", "move(-1)", "Up"), Binding("down", "move(1)", "Down"),
                Binding("left", "adjust(-1)", "Less"), Binding("right", "adjust(1)", "More"), Binding("enter", "adjust(1)", "More")]
    DEFAULT_CSS = """
    SettingsScreen { align: center top; }
    SettingsScreen > Vertical { width: 100%; max-width: 70; height: 100%; background: $surface; padding: 0 1; }
    SettingsScreen .srow { height: 1; }
    SettingsScreen .srow Static { width: 1fr; }
    SettingsScreen .srow.sel Static { background: $accent 40%; }
    SettingsScreen .srow Button { height: 1 !important; border: none !important; min-width: 5; width: 5; margin-left: 1; }
    SettingsScreen #wnote { height: 2; margin-top: 1; color: $text-muted; }
    SettingsScreen #whelp { height: 1; color: $text-muted; }
    SettingsScreen #close { height: 1 !important; border: none !important; }
    """
    LABELS = [("open_mode", "open mode"), ("claude_model", "model"), ("manager_model", "manager"), ("claude_effort", "effort"),
              ("claude_permissions", "prompts"), ("menu_width", "width"), ("recent_days", "recent")]      # short: label + value must fit beside - and + at 35 columns

    def __init__(self):
        super().__init__()
        self.sel = 0

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Settings", id="stitle")
            for key, label in self.LABELS:
                with Horizontal(classes="srow", id=f"row-{key}"):
                    yield Static("", id=f"v-{key}", markup=False)
                    yield Button("−", id=f"m-{key}")
                    yield Button("+", id=f"p-{key}")
            yield Static(self.width_note(), id="wnote", markup=False)
            yield Static("Left/Right or - +: change", id="whelp", markup=False)
            yield Button("Close (esc)", id="close")

    @staticmethod
    def width_note():
        live = os.environ.get("HB_SIDEBAR") and os.environ.get("KITTY_LISTEN_ON")
        return "menu width: applies at once in this sidebar window" if live else "menu width: applies when the sidebar window is opened again"

    def on_mount(self):
        self.show()

    def show(self):
        for i, (key, label) in enumerate(self.LABELS):
            self.query_one(f"#v-{key}", Static).update(f" {label:<11}{cfg_get(key)}")
            self.query_one(f"#row-{key}").set_class(i == self.sel, "sel")

    def change(self, key, step):
        vals = CHOICES[key]
        cur = cfg_get(key)
        i = vals.index(cur) if cur in vals else 0
        new = vals[(i + 1) % len(vals)] if len(vals) == 2 or key == "open_mode" else vals[max(0, min(len(vals) - 1, i + step))]      # a toggle flips; a number clamps
        if new != cur:
            set_config(key, new)
            if key == "menu_width":
                self.app.fit_width()
            self.app.refresh_list()
        self.show()

    def action_move(self, step: int):
        self.sel = max(0, min(len(self.LABELS) - 1, self.sel + step))
        self.show()

    def action_adjust(self, step: int):
        self.change(self.LABELS[self.sel][0], step)

    def on_button_pressed(self, event):
        event.stop()
        bid = event.button.id
        if bid == "close":
            self.dismiss()      # not `return self.dismiss()`: Textual awaits what a handler returns, and a screen can't await its own dismiss
            return
        kind, key = bid.split("-", 1)
        self.sel = [k for k, _ in self.LABELS].index(key)
        self.change(key, -1 if kind == "m" else 1)

    def action_close(self):
        self.dismiss()


class Menu(App):
    TITLE = "hyperbeam"
    ENABLE_COMMAND_PALETTE = False
    CSS = """
    #title { height: 1; padding: 0 1; text-style: bold; color: $accent; }
    #list { height: 1fr; border: none; padding: 0; scrollbar-size-vertical: 1; }
    #why { height: 1; padding: 0 1; color: $text-muted; }
    #notice { height: 2; padding: 0 1; margin-bottom: 1; }
    #buttons { layout: grid; grid-size: 2; grid-gutter: 0 1; height: auto; }
    #b-merge { display: none; column-span: 2; }
    .pr #b-merge { display: block; }
    #buttons Button { width: 1fr; height: 1 !important; border: none !important; min-width: 8; }
    #b-merge { background: $success 60%; text-style: bold; }
    """
    BINDINGS = [Binding("o", "open", "Open"), Binding("s", "stop", "Stop"), Binding("d", "done", "Done"), Binding("t", "settings", "Settings"), Binding("u", "update", "Update"), Binding("h", "hide", "Hide sidebar"),
                Binding("c", "context", "Copy context"), Binding("p", "report", "Copy report"), Binding("m", "merge", "Merge PR"), Binding("i", "project", "Project"), Binding("j", "project", "Project"), Binding("r", "refresh", "Refresh"), Binding("q", "quit", "Quit")]

    def __init__(self):
        super().__init__()
        self.projects, self.busy, self.status = [], set(), {}
        self.keep_notice = False        # True after an action: the refresh then leaves its result message on screen
        self.repo = ("", "")            # (short, long) note on the hyperbeam row: on a branch / origin/main is ahead
        self.recheck_next = False       # Refresh: run the red checks again

    def compose(self) -> ComposeResult:
        yield Static("hyperbeam", id="title")
        yield ProjectList(id="list")
        yield Static("", id="why", markup=False)
        yield Static("Loading projects...", id="notice", markup=False)
        with Container(id="buttons"):
            for bid, label in [("open", "Open"), ("stop", "Stop"), ("done", "Done"), ("update", "Update"), ("merge", "Merge"), ("more", "More"), ("hide", "Hide")]:
                if bid == "hide" and not os.environ.get("HB_SIDEBAR"):
                    continue
                button = Button(label, id=f"b-{bid}")
                button.can_focus = False
                yield button

    def on_mount(self):
        self.query_one("#list", OptionList).focus()
        self.action_refresh()
        self.set_interval(3, self.poll_running)
        self.set_interval(5, self.poll_status)
        self.set_interval(600, self.fetch_repo)
        self.set_interval(60, self.recheck_running)
        self.set_interval(60, self.poll_prs)
        self.set_interval(5, lambda: self.poll_prs(False))
        self.set_interval(60, self.poll_usage)
        self.set_timer(4, self.poll_usage)
        self.set_timer(3, self.poll_prs)
        self.set_timer(2, self.recheck_running)
        self.set_timer(20, self.tool_check)
        asyncio.get_running_loop().add_signal_handler(signal.SIGUSR1, lambda: self.exit(return_code=75))      # `hyperbeam update`: restart me
        asyncio.get_running_loop().add_signal_handler(signal.SIGUSR2, lambda: self.poll_prs(False))                      # `hyperbeam refresh-prs`: read the PR cache now
        self.fetch_repo()
        self.set_timer(1.0, self.fit_width)
        self.set_interval(300, self.save_layouts)
        journal_start()
        touch_opened(MENU)       # the manager session is home: recent (bold) and part of the session record

    HINTS = {"open": "o", "stop": "s", "done": "d", "update": "u", "merge": "m", "more": "j", "hide": "h"}

    def on_resize(self, event):
        self.set_class(event.size.width < 50, "narrow")
        for bid, key in self.HINTS.items():                   # key hints only where there is room: in a narrow sidebar the label is the whole button
            for b in self.query(f"#b-{bid}"):
                b.label = bid.capitalize() + (f" ({key})" if event.size.width >= 50 else "")
        self.call_after_refresh(self.refresh_list)
        if os.environ.get("HB_SIDEBAR") and event.size.width != cfg_get("menu_width"):   # the window was resized: kitty keeps the split's proportion, so bring the width back
            if getattr(self, "_fit_timer", None):
                self._fit_timer.stop()
            self._fit_timer = self.set_timer(0.5, self.fit_width)

    def tool_check(self):
        """The daily tool check (daily_tool_check), in the background; a failing tool is a quiet note on the hyperbeam row (never a dot)."""
        def work():
            try:
                failing = daily_tool_check()
            except Exception as e:
                failing = [("?", str(e))]
            if failing:
                self.say_from_thread("tools: " + "; ".join(f"{n} FAILS its test ({w[:60]})" for n, w in failing) + " (note on the hyperbeam row)")
                self.recheck_running()
        self.run_worker(work, thread=True, group="toolcheck")

    def recheck_running(self):
        """Git notes and the red git checks of running projects, again (the stored result is what the dot, kk and the status segment read)."""
        def work():
            st = self.compute_status(self.projects, True)
            self.call_from_thread(self.set_status, st)
        self.run_worker(work, thread=True, group="recheck")

    def fit_width(self, tries=4):
        """Sidebar: make this window `menu_width` columns wide through kitty remote control (this kitty only: the sidebar was started with
        allow_remote_control=socket-only and --listen-on, which puts KITTY_LISTEN_ON in our environment). resize-window moves the split by a
        number of cells, so we measure our own width and correct it a few times."""
        if not (os.environ.get("HB_SIDEBAR") and os.environ.get("KITTY_LISTEN_ON")) or tries <= 0:
            return
        delta = cfg_get("menu_width") - self.size.width
        if not delta:
            return

        def work():
            try:                                            # hidden (stack layout): the menu is not beside anything, leave it
                if any(t.get("layout") == "stack" for ow in json.loads(kitten_sidebar("ls").stdout) for t in ow.get("tabs", [])):
                    return
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
            subprocess.run(["kitten", "@", "resize-window", "--self", "--axis", "horizontal", "--increment", str(delta)],
                           capture_output=True, timeout=5)
            self.call_from_thread(lambda: self.set_timer(0.6, lambda: self.fit_width(tries - 1)))
        self.run_worker(work, thread=True, group="width")

    def fetch_repo(self):
        """The hyperbeam row's note: on a branch / origin/main ahead. Fetches (short, quiet) every 10 minutes."""
        def work():
            git_fetch(HERE)
            self.call_from_thread(self.set_repo)
        self.run_worker(work, thread=True, group="repo")

    def set_repo(self):
        self.repo = repo_note()
        self.refresh_title()

    def refresh_title(self):
        w = max(20, (self.query_one("#title", Static).size.width or 35) - 2)
        usage = getattr(self, "usage_text", "")
        text = "hyperbeam  update available (u)" if self.repo[0] == "behind" else (usage or "hyperbeam")          # the limit as claude.ai shows it; the name only when there is nothing else
        self.query_one("#title", Static).update(clip(text, w))

    def poll_usage(self):
        """The 5-hour limit for the title (what claude.ai shows, from the status line's file), read every minute in a worker thread."""
        def work():
            try:
                line = usage_line(short=True)
            except Exception:
                return
            self.usage_text = line
            self.call_from_thread(self.refresh_title)
        self.run_worker(work, thread=True, group="usage", exclusive=True)
        self.refresh_list()

    # --- data ---
    def action_refresh(self):
        self.recheck_next = True
        self.reload(keep=False)

    def reload(self, keep):
        self.keep_notice = keep
        if not keep:
            self.say("Scanning projects...")
        self.run_worker(self._load, thread=True, exclusive=True, group="load")

    def _load(self):
        rows = build_projects()
        status = self.compute_status(rows, self.recheck_next)
        self.recheck_next = False
        self.call_from_thread(self.apply, rows, status)

    def compute_status(self, rows, recheck_all=False):
        mans = load_manifests()
        if recheck_all:
            for r in rows:
                if r["running"]:
                    recheck(r["name"], known_path(r["name"]))
        return {r["name"]: project_status(r["name"], mans.get(r["name"])) for r in rows if r["running"]}

    def apply(self, rows, status):
        old = {p["name"]: p.get("prs") for p in self.projects}
        for r in rows:
            r["prs"] = old.get(r["name"])
        self.projects, self.status = rows, status
        self.refresh_list()
        if not self.keep_notice:
            self.say(f"{len(rows)} projects, {sum(1 for r in rows if r['running'])} running")

    def poll_running(self):
        run_set = running_sessions()
        changed = False
        for p in self.projects:
            now = sanitize(p["name"]) in run_set
            w = worker_sess(p["name"]) in run_set
            changed |= now != p["running"] or w != p.get("worker", False)
            p["running"], p["worker"] = now, w
        if changed:
            self.poll_status()

    def poll_status(self):
        def work():
            mans, changed = load_manifests(), False          # a manifest written or committed since the last scan shows up (port, "unset")
            for p in self.projects:
                m = mans.get(p["name"])
                now = (m is not None, m.get("port") if m else None)
                if (p["manifest"], p["port"]) != now:
                    p["manifest"], p["port"] = now
                    changed = True
            for p in self.projects:                             # a branch switched since the last look
                b = branch_of(p["path"])
                if p.get("branch") != b:
                    changed = True
            st = self.compute_status(self.projects)
            if st != self.status or changed:
                self.call_from_thread(self.set_status, st)
        self.run_worker(work, thread=True, group="status")

    def poll_prs(self, fetch=True):
        """Open PRs of yours per project, from the cache on disk and, with `fetch`, from gh where the cache is older than PR_TTL (a worker thread, one project at a
        time). fetch=False reads the disk only: a list written by `hyperbeam refresh-prs` shows within seconds (every 5 s, and at once on SIGUSR2)."""
        def work():
            changed = False
            for p in list(self.projects):
                try:
                    if p.get("slug", 0) == 0:
                        p["slug"] = github_slug(p["path"])
                    if not p["slug"]:
                        continue
                    prs, age, err = cached_prs(p["name"], p["path"])
                    if fetch and age >= PR_TTL:
                        prs = open_prs(p["name"], p["path"], force=True)
                    elif prs is None:
                        continue
                except Exception:
                    continue
                if (prs or None) != (p.get("prs") or None):
                    p["prs"], changed = prs or None, True
            if changed:
                self.call_from_thread(self.refresh_list)
        self.run_worker(work, thread=True, group="prs" if fetch else "prcache", exclusive=True)

    def set_status(self, st):
        self.status = st
        self.refresh_list()

    # --- the list: running, then recent, then the rest; alphabetical within each ---
    def ordered(self):
        days = cfg_get("recent_days")
        now = time.time()
        for p in self.projects:
            p["recent"] = bool(p["opened"]) and now - p["opened"] < days * 86400
        return sorted(self.projects, key=lambda p: (-1 if p["name"] == MENU else 0 if p["running"] else 1 if p["recent"] else 2, p["name"].lower()))

    def refresh_list(self):
        ol = self.query_one("#list", OptionList)
        keep = self.current()
        ol.clear_options()
        rows = self.ordered()
        width = max(20, self.size.width - 2 - 1)    # the option's own padding, the 1-column scrollbar
        for p in rows:
            p["branch"] = branch_of(p["path"])
            note = self.repo[0] if p["name"] == MENU and self.repo[0] == "behind" else ""
            ol.add_option(Option(row_text(p, self.status.get(p["name"]) if p["running"] else None, width, note), id=p["name"]))
        if rows:
            names = [p["name"] for p in rows]
            if keep and keep["name"] in names:
                ol.highlighted = names.index(keep["name"])
            else:                                           # fresh list: the project the main area shows, else the manager session (row 0)
                shown = client_sessions().get(sidebar_read().get("tty"), "")
                ol.highlighted = next((i for i, p in enumerate(rows) if sanitize(p["name"]) == shown), 0)
        self.show_why()

    def current(self):
        ol = self.query_one("#list", OptionList)
        if ol.highlighted is None or ol.highlighted >= ol.option_count:
            return None
        name = ol.get_option_at_index(ol.highlighted).id
        return next((p for p in self.projects if p["name"] == name), None)

    def show_why(self):
        p, why = self.current(), ""
        st = self.status.get(p["name"]) if p and p["running"] else None
        self.set_class(bool(p and p.get("prs")), "pr")              # a project with an open PR gets a Merge button
        if p and p.get("prs") and not (st and st[0] == "red"):
            pr = p["prs"][0]
            why = f"PR #{pr['number']}: {pr['title']}" + (f" [stale: {pr_age_days(pr)}d]" if pr_stale(pr) else "") + (f"  (+{len(p['prs']) - 1} more)" if len(p["prs"]) > 1 else "")
        elif st:
            why = f"[{st[0]}] {st[1]}"
        elif p and p["name"] == MENU:
            why = self.repo[1] or "the manager: talk about your projects"
        elif p and not p["manifest"]:
            why = "no manifest: Open starts Claude to set it up"
        w = self.query_one("#why", Static).size.width or 40
        self.query_one("#why", Static).update(clip(why, w - 2))

    def say(self, msg):
        w = max(12, (self.query_one("#notice", Static).size.width or 40) - 2)
        lines = []
        for part in str(msg).splitlines() or [""]:
            lines += textwrap.wrap(part, w) or [""]
        if len(lines) > 2:
            lines = [lines[0], clip(" ".join(lines[1:]), w)]
        self.query_one("#notice", Static).update("\n".join(lines))

    def say_from_thread(self, msg):
        self.call_from_thread(self.say, msg)

    # --- events ---
    # Messages bubble from any screen up to the App, so every handler here checks that it came from the main list or the main buttons.
    def on_option_list_option_highlighted(self, event):
        if event.option_list.id == "list":
            self.show_why()

    def on_option_list_option_selected(self, event):
        if event.option_list.id == "list":
            self.action_open()

    def on_button_pressed(self, event):
        if event.button.id and event.button.id.startswith("b-"):
            getattr(self, "action_" + event.button.id[2:])()

    def check_action(self, action, parameters):
        """The Menu's keys do nothing while any other screen (Settings, a question) is up."""
        if action in ("open", "stop", "done", "settings", "update", "hide", "context", "report", "merge", "info", "project", "more", "keys", "edit_manifest", "mark_onboarded", "install", "test", "version", "help_verbs", "refresh", "quit") and len(self.screen_stack) > 1:
            return False
        return True

    def action_settings(self):
        self.push_screen(SettingsScreen())

    # --- actions ---
    def action_open(self):
        p = self.current()
        if not p:
            return self.say("Nothing selected.")
        if p["name"] in self.busy:
            return self.say(f"{p['name']} is busy.")
        self.busy.add(p["name"])
        self.run_worker(lambda: self._open(p), thread=True)

    def ask(self, text):
        """Ask y/n in a modal; called from a worker thread, blocks until answered."""
        done, box = threading.Event(), []
        self.call_from_thread(self.push_screen, Confirm(text), lambda v: (box.append(bool(v)), done.set()))
        done.wait()
        return box[0]

    def _open(self, p):
        """Open: start the session if needed (the saved layout comes back), then show it. Nothing is ever sent to Claude."""
        name, sess = p["name"], sanitize(p["name"])
        try:
            open_project(name, p["path"], load_manifests().get(name), self.ask, self.say_from_thread)
            touch_opened(name)
            how = show_session(sess)
            self.say_from_thread(f"{name}: {how} ({HINT})")
        except Exception as e:
            self.say_from_thread(f"{name}: ERROR {e}")
        finally:
            self.busy.discard(name)
            self.call_from_thread(self.reload, True)

    def save_layouts(self):
        self.run_worker(save_all, thread=True, group="save")

    def choose(self, text, options, enter=None):
        """Like ask(): a modal with several buttons, from a worker thread; returns the chosen id."""
        done, box = threading.Event(), []
        self.call_from_thread(self.push_screen, Choice(text, options, enter), lambda v: (box.append(v), done.set()))
        done.wait()
        return box[0]

    def action_stop(self):
        p = self.current()
        if not p:
            return self.say("Nothing selected.")
        man = load_manifests().get(p["name"])
        if not man and not p["running"]:
            return self.say(f"{p['name']} is not running.")
        if p["name"] in self.busy:
            return self.say(f"{p['name']} is busy.")
        self.busy.add(p["name"])
        self.say(f"{p['name']}: checking for unfinished work...")
        self.run_worker(lambda: self._stop(p, man), thread=True)

    def _stop(self, p, man):
        """Stop: the wrap-up check first. Clean: confirm and stop. Not clean: stop anyway or cancel."""
        name = p["name"]
        try:
            r = check_project(name)
            if r and not wrapup_clean(r):
                pick = self.choose(f"{format_wrapup(r)}\n\nStop {name} anyway?", [
                    ("stop", "Stop anyway (s)", "s"), ("cancel", "Cancel (c)", "c")])
                if pick != "stop":
                    return self.say_from_thread(f"{name}: not stopped.")
            else:
                ports = ", ".join(map(str, project_ports(man))) or "(none: no manifest)"
                if not self.ask(f"{name}: all clean (nothing uncommitted, unpushed or secret-looking).\n\nStop it? Runs its stop commands in reverse order, "
                                f"kills the tmux session, and checks that port(s) {ports} are free."):
                    return self.say_from_thread(f"{name}: not stopped.")
            stop_project(name, man, self.say_from_thread)
        except Exception as e:
            self.say_from_thread(f"{name}: ERROR {e}")
        finally:
            self.busy.discard(name)
            self.call_from_thread(self.reload, True)

    def action_done(self):
        if "@done" in self.busy:
            return self.say("Done for now is already running.")
        self.busy.add("@done")
        self.say("Done for now: checking every project in the session record...")
        self.run_worker(self._done, thread=True)

    def _done(self):
        """Done for now: the wrap-up check on every project worked on since the menu started. All clean: offer to stop their sessions.
        Otherwise say which are not clean and stop nothing."""
        try:
            names = sorted(n for n in load_journal()["projects"] if n != MENU)       # the manager is not a project: its notes are committed by its own wrap-up
            if not names:
                return self.say_from_thread("Done for now: no project has been opened since the menu started.")
            results = [r for r in (check_project(n) for n in names) if r]
            if any(not wrapup_clean(r) for r in results):
                return self.say_from_thread("Done for now: not clean, nothing stopped: " + ", ".join(r["name"] for r in results if not wrapup_clean(r)) + ". Stop one to see why.")
            all_running = [n for n in names if sanitize(n) != MENU and session_exists(sanitize(n))]
            busy = {n: claude_state(n)[0] for n in all_running if claude_state(n)[0] in ("working", "waiting")}       # git-clean is not the same as finished
            running = [n for n in all_running if n not in busy]
            left = ", ".join(f"{n} (Claude {'is working' if k == 'working' else 'waits for you'})" for n, k in busy.items())
            if busy and not running:
                return self.say_from_thread(f"Done for now: all clean, but {left}. Nothing was stopped; the sidebar stays open.")
            msg = f"All clean: {', '.join(names)}.\n\n" + (f"Stop these sessions? {', '.join(running)}" if running else "No session of them is running.") + (f"\n\nLeft running: {left}." if busy else "")
            if running and not self.ask(msg):
                return self.say_from_thread("Done for now: all clean, nothing stopped.")
            for n in running:
                stop_project(n, load_manifests().get(n), self.say_from_thread)
            if busy:
                return self.say_from_thread(f"Done for now: stopped {', '.join(running)}; left running: {left}. The session record and the sidebar stay.")
            journal_clear()
            self.say_from_thread("Done for now: all clean" + (f"; stopped {', '.join(running)}" if running else "") + ". Session record cleared.")
            if os.environ.get("HB_SIDEBAR"):        # close the whole sidebar window (this menu is inside it: a detached helper does it)
                subprocess.Popen([str(HERE / "hyperbeam"), "_close-sidebar"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, start_new_session=True)
        except Exception as e:
            self.say_from_thread(f"Done for now: ERROR {e}")
        finally:
            self.busy.discard("@done")
            self.call_from_thread(self.reload, True)

    def action_context(self):
        """Copy the context bundle of the selected project (clipboard at the laptop, outbox over SSH)."""
        p = self.current()
        if not p:
            return self.say("Nothing selected.")
        name = p["name"]

        def work():
            remote = False if os.environ.get("HB_SIDEBAR") else client_is_remote(menu_client("client_pid") or "0")
            try:
                self.say_from_thread(f"{name}: {copy_context(name, remote)}")
            except Exception as e:
                self.say_from_thread(f"{name}: context failed: {e}")
        self.run_worker(work, thread=True)

    def action_report(self):
        """Copy Claude's last message of the selected project's session (the PR report): clipboard at the laptop, outbox over SSH."""
        p = self.current()
        if not p:
            return self.say("Nothing selected.")
        name = p["name"]

        def work():
            remote = False if os.environ.get("HB_SIDEBAR") else client_is_remote(menu_client("client_pid") or "0")
            try:
                text = report_text(name)
                self.say_from_thread(f"{name}: report {deliver_text(text, name + '-report', remote)} - \"{first_line(text, 50)}\"")
            except Exception as e:
                self.say_from_thread(f"{name}: no report: {e}")
        self.run_worker(work, thread=True)

    def action_merge(self):
        """Merge all of the selected project's open PRs (yours), oldest first, after one confirmation. See _merge_all."""
        p = self.current()
        if not p or not p.get("prs"):
            return self.say("No open PR of yours for the selected project.")
        if p["name"] in self.busy:
            return self.say(f"{p['name']} is busy.")
        self.busy.add(p["name"])
        self.run_worker(lambda: self._merge_all(p, sorted(p["prs"], key=lambda x: x["number"])), thread=True)

    def _merge_all(self, p, prs):
        """One confirmation, then every PR in order; before each one the check against main is made again (the one before it moved main). A PR
        with nothing in common with main's new commits merges without a question; the first real problem (main changed the PR's own files and
        the user says update or cancel, GitHub refuses, a conflict) stops the run and the rest stay open. The project's update runs once, last:
        for hyperbeam always (the installed copy updates from GitHub whatever state the dev folder is in), for others when the checkout was pulled."""
        name = p["name"]
        merged, stopped, local_ok = [], None, False
        try:
            since = git_out(p["path"], "rev-parse", default_branch(p["path"]))      # before the first merge pulls: the update compares against it
            lines = "\n".join(f"#{x['number']} {x['title']}" + (f" (stale: {pr_age_days(x)} days old)" if pr_stale(x) else "") for x in prs)
            if not self.ask(f"Merge {len(prs)} PR{'s' if len(prs) != 1 else ''} in {name}, oldest first?\n\n{lines}\n\n"
                            "A merge commit each; the branches are deleted on GitHub. It stops at the first one that needs a look. Nothing is merged without Yes."):
                return self.say_from_thread(f"{name}: merge cancelled")
            for pr in prs:
                stop, pulled = self._merge_one(p, pr)
                if stop:
                    stopped = f"stopped at #{pr['number']}: {stop}"
                    break
                merged.append(pr)
                local_ok = pulled
            if merged:
                p["prs"] = open_prs(name, p["path"], force=True, gone={x["number"] for x in merged}) or None
                self.call_from_thread(self.refresh_list)
                try:
                    (DATA_DIR / "merge-verified").write_text(time.strftime("%Y-%m-%d %H:%M") + f" {name} #{merged[-1]['number']}\n")     # `verify` stops asking for a Merge test
                except OSError:
                    pass
            summary = (("merged " + ", ".join(f"#{x['number']}" for x in merged)) if merged else "nothing merged") + (f"; {stopped}" if stopped else "")
            if merged and name == "hyperbeam":
                self.say_from_thread(f"{name}: {summary}")
                self.call_from_thread(self.update_hyperbeam)       # the menu restarts itself: this runs in a popup
            elif merged and local_ok:
                lines = []                                         # merged and pulled: now the project's own update (install, restart services), one click in all
                rc = run_verb(name, "update", p["path"], lines.append, since=since or None)
                last = next((l for l in reversed(lines) if l.strip()), "")
                self.say_from_thread(f"{name}: {summary}; update {'ok' if rc == 0 else 'FAILED'}: {last}")
            else:
                self.say_from_thread(f"{name}: {summary}")
        except Exception as e:
            self.say_from_thread(f"{name}: merge ERROR {e}" + (f" (merged {', '.join('#' + str(x['number']) for x in merged)} before)" if merged else ""))
        finally:
            self.busy.discard(name)

    def _ask_update(self, p, pr, behind, base, conflicts=()):
        """Ask the project's Claude to rebase the PR onto its base and re-test (update_prompt). -> the sentence that stops the merge run."""
        name = p["name"]
        sess = sanitize(name)
        pane = find_claude_pane(sess) if session_exists(sess) else None
        why = f"conflicts with {base}" if conflicts else f"behind {base}"
        if not pane:
            return f"{why}, and {name} is not running: Open it, then click Merge again (nothing more was merged)"
        inject_prompt(pane, update_prompt(name, pr, behind, base, conflicts), [])
        return f"{why}; asked Claude to rebase it and re-test: click Merge again when it has pushed"

    def _merge_one(self, p, pr):
        """Check one PR against its base and merge it. -> (None, whether the local checkout was pulled) when merged, else (why the run stops, False)."""
        name = p["name"]
        self.say_from_thread(f"{name}: checking PR #{pr['number']} against {pr.get('base') or 'main'}...")
        try:
            state = pr_state(p["path"], pr)
        except (subprocess.SubprocessError, OSError):
            state = None
        base = pr.get("base") or default_branch(p["path"])
        if state is None:
            self.say_from_thread(f"{name}: could not check PR #{pr['number']} against {base} (offline? a fork?): merging without that check")
            state = {"behind": 0, "overlap": [], "conflicts": []}
        behind, overlap, conflicts = state["behind"], state["overlap"], state["conflicts"]
        if conflicts:                  # "Merge anyway" can't work: Claude rebases it, then Merge again
            return self._ask_update(p, pr, behind, base, conflicts), False
        if behind and overlap:
            shown = ", ".join(overlap[:3]) + (f" and {len(overlap) - 3} more" if len(overlap) > 3 else "")
            pick = self.choose(f"PR #{pr['number']} in {name}: {pr['title']}\n\nThis PR is {behind} commit{'s' if behind != 1 else ''} behind {base}, and {base} also changed {shown}; "
                               "its tests ran without those changes.\n\nAsk Claude to update it and re-test (Enter), or merge it as it is.", [
                ("ask", "Ask Claude to update and re-test (a)", "a"), ("merge", "Merge anyway (m)", "m"), ("cancel", "Cancel (c)", "c")], enter="ask")
            if pick == "ask":
                return self._ask_update(p, pr, behind, base), False
            if pick != "merge":
                return "cancelled", False
        self.say_from_thread(f"{name}: merging PR #{pr['number']}...")
        ok, local_ok, msgs = merge_pr(name, p["path"], pr, self.say_from_thread)
        if not ok and any(w in " ".join(msgs).lower() for w in ("conflict", "not mergeable", "cannot be cleanly")):      # GitHub's own view of a conflict
            return self._ask_update(p, pr, behind, base, ["(see the PR on GitHub)"]), False
        if not ok:
            return "; ".join(msgs), False
        for m in msgs[1:]:
            self.say_from_thread(f"{name}: {m}")
        return None, local_ok

    def action_more(self):
        self.action_project()

    def action_keys(self):
        self.push_screen(KeysScreen())

    def action_project(self):
        """The Project screen for the selected project (also on i); its buttons run the matching actions after it closes."""
        p = self.current()
        if not p:
            return self.say("Nothing selected.")
        name, path, prs = p["name"], p["path"], p.get("prs")

        def work():
            try:
                text = project_summary(name, path, prs=prs)
            except Exception as e:
                text = f"{name}\n\ncould not read the project: {e}"
            self.call_from_thread(lambda: self.push_screen(ProjectScreen(text), lambda r: self.run_project_action(r)))
        self.run_worker(work, thread=True)

    def run_project_action(self, what):
        if what and hasattr(self, "action_" + what):
            getattr(self, "action_" + what)()

    def action_edit_manifest(self):
        """projects/<name>.toml in $EDITOR (else nvim), in a new window of the project's tmux session, shown on the right side of the sidebar."""
        p = self.current()
        if not p:
            return self.say("Nothing selected.")
        man = MANIFESTS / f"{p['name']}.toml"
        sess = sanitize(p["name"])
        if not man.is_file():
            return self.say(f"{p['name']}: no manifest yet: use Onboard.")
        if not session_exists(sess):
            return self.say(f"{p['name']}: not running: Open it first, then Edit manifest.")
        win = "manifest"
        tmux("kill-window", "-t", f"={sess}:={win}", check=False)
        side = sidebar_client() if os.environ.get("HB_SIDEBAR") else menu_client()
        tmux("new-window", *(["-d"] if side else []), "-t", f"{sess}:", "-n", win, "-c", str(MANIFESTS), f"${{EDITOR:-nvim}} {shlex.quote(str(man))}")
        if side:
            tmux("switch-client", "-c", side, "-t", f"={sess}:={win}", check=False)
        self.say(f"{p['name']}: editing {home_rel(man)} (window `{win}` of its session)")

    def action_mark_onboarded(self):
        """Take the project's fingerprint as it is now: the setup is onboarded (clears a 'setup changed' note)."""
        p = self.current()
        if not p:
            return self.say("Nothing selected.")
        if not (MANIFESTS / f"{p['name']}.toml").is_file():
            return self.say(f"{p['name']}: no manifest yet: use Onboard.")
        take_fingerprint(p["name"], p["path"])
        if p["running"]:
            recheck(p["name"], p["path"])
        self.recheck_next = True
        self.reload(keep=True)
        self.say(f"{p['name']}: marked as onboarded ({onboarded_on(p['name'], p['path'])})")

    def action_info(self):
        """The same text as `kk`, in a plain tmux window (so mouse-drag copy works), closed with Enter."""
        p = self.current()
        if not p:
            return self.say("Nothing selected.")
        win = f"info-{sanitize(p['name'])}"
        tmux("kill-window", "-t", f"={MENU}:={win}", check=False)
        side = sidebar_client() if os.environ.get("HB_SIDEBAR") else ""
        tmux("new-window", *(["-d"] if side else []), "-t", f"{MENU}:", "-n", win,
             f"{SELF} info {shlex.quote(p['name'])}; echo; read -r -p '[Enter closes this window] '")
        if side:                    # the sidebar's right client looks at `home`: show the info window there
            tmux("switch-client", "-c", side, "-t", f"={MENU}:={win}", check=False)

    def action_hide(self):
        """Sidebar: hide it (the main side goes full width; M-s on that side brings it back)."""
        if not os.environ.get("HB_SIDEBAR"):
            return self.say("Hide: only in the sidebar window.")
        self.run_worker(lambda: self.say_from_thread(sidebar_toggle()), thread=True)

    def action_update(self):
        """Update the selected project through its `update` verb. The hyperbeam row (or nothing selected) runs `hyperbeam update` in a popup."""
        p = self.current()
        if p and p["name"] not in ("hyperbeam", MENU):
            return self.run_verb_action(p, "update")
        return self.update_hyperbeam()

    def run_verb_action(self, p, verb):
        """A standard verb of the selected project in a worker thread; the last line of its output is the result, all of it is saved to
        <project data>/verb-<verb>.txt (the Project screen's Info window shows it)."""
        name = p["name"]
        if name == "hyperbeam" and verb == "update":
            return self.update_hyperbeam()
        if name in self.busy:
            return self.say(f"{name} is busy.")
        self.busy.add(name)
        self.say(f"{name}: {verb}...")

        def work():
            lines = []
            try:
                rc = run_verb(name, verb, p["path"], lines.append)
                try:
                    (project_dir(name, p["path"]) / f"verb-{verb}.txt").write_text("\n".join(lines) + "\n")
                except OSError:
                    pass
                last = next((l for l in reversed(lines) if l.strip()), "done" if rc == 0 else f"failed ({rc})")
                self.say_from_thread(f"{name} {verb}: {'ok' if rc == 0 else 'FAILED'}: {last}")
            except Exception as e:
                self.say_from_thread(f"{name} {verb}: ERROR {e}")
            finally:
                self.busy.discard(name)
                self.call_from_thread(self.reload, True)
        self.run_worker(work, thread=True)

    def action_install(self):
        p = self.current()
        return self.run_verb_action(p, "install") if p else self.say("Nothing selected.")

    def action_test(self):
        p = self.current()
        return self.run_verb_action(p, "test") if p else self.say("Nothing selected.")

    def action_version(self):
        p = self.current()
        return self.run_verb_action(p, "version") if p else self.say("Nothing selected.")

    def action_help_verbs(self):
        p = self.current()
        return self.run_verb_action(p, "help") if p else self.say("Nothing selected.")

    def update_hyperbeam(self):
        """A popup on the client that shows the main area runs `hyperbeam update` (it restarts this menu at the end, so it must not run here)."""
        c = sidebar_client() if os.environ.get("HB_SIDEBAR") else menu_client()
        if not c:
            return self.say("No tmux client to show the update on: run `hyperbeam update` in a terminal.")
        subprocess.Popen(["tmux", "display-popup", "-c", c, "-E", "-w", "90%", "-h", "80%", "-T", " hyperbeam update ",
                          f"{SELF} update; echo; read -r -p '[Enter closes] '"],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        self.say("Update running in a popup...")

    def action_quit(self):
        """In the sidebar Quit ends the menu (its window closes with it). In tmux it detaches the client; the menu keeps running there."""
        if os.environ.get("HB_SIDEBAR"):
            return self.exit()
        c = menu_client()
        if c:
            tmux("detach-client", "-t", c, check=False)


MENU_PIDS = STATE_DIR / "menus"


def run_menu():
    """The menu process. It records itself (pid file) so `hyperbeam update` can restart it, and restarts on SIGUSR1 (exit code 75)."""
    MENU_PIDS.mkdir(parents=True, exist_ok=True)
    f = MENU_PIDS / str(os.getpid())
    f.write_text(json.dumps({"home": str(HERE), "sidebar": bool(os.environ.get("HB_SIDEBAR")), "usr2": True}))       # usr2: handles SIGUSR2 (an older menu would be killed by it)
    app = Menu()
    try:
        app.run()
    finally:
        f.unlink(missing_ok=True)
    return app.return_code or 0


