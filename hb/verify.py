# hyperbeam, part 'verify': verify, shot. Runs in the namespace of the `hyperbeam` script (see its loader): no imports of its own.
# ---------- verify: one command that checks what only the user's own accounts and machine can show ----------
def user_runs(script):
    return f"(the user runs this, never an agent) sudo bash {HERE / 'lab' / script}"


def verify_checks(which="all"):
    """[(status, text, how)] with status PASS / FAIL / YOU (only the user can do it; `how` is the exact command). Run as the user."""
    out = []
    add = lambda st, text, how="": out.append((st, text, how))
    if which in ("all", "github"):
        owners = {}
        try:
            for r in scan():
                sl = github_slug(r["path"])
                if sl:
                    owners.setdefault(sl.split("/")[0], []).append(r["name"])
        except OSError:
            pass
        if not shutil.which("gh"):
            add("FAIL", "gh is not installed", "sudo apt-get install -y gh")
        for o, names in sorted(owners.items()):
            if gh_account(o):
                add("PASS", f"gh: logged in as {o} ({len(names)} project{'s' * (len(names) != 1)})")
            else:
                add("FAIL", f"gh: no login for {o}: {len(names)} project(s) get no PR badge and can't be merged from the sidebar ({', '.join(names[:3])}{'...' if len(names) > 3 else ''})", "gh auth login")
        hp = known_path("hyperbeam")
        slug = github_slug(hp)
        if slug and gh_account(slug.split("/")[0]):
            prs = open_prs("hyperbeam", hp, force=True)
            err = (json.loads(pr_cache_file("hyperbeam", hp).read_text()).get("error") if pr_cache_file("hyperbeam", hp).exists() else "")
            add("FAIL" if err else "PASS", f"gh: listing your open PRs in {slug}" + (f" failed: {err}" if err else f" works ({len(prs)} open)"), "gh pr list -R " + slug if err else "")
        mv = DATA_DIR / "merge-verified"
        if mv.is_file():
            add("PASS", f"Merge worked end to end ({mv.read_text().strip()})")
        else:
            add("YOU", "Merge has not been used yet: the first real Merge click makes this PASS (or open a throwaway PR to try it)", "hyperbeam verify merge")
    if which in ("all", "hooks"):
        sf = Path(os.environ.get("HB_SETTINGS") or Path.home() / ".claude/settings.json")
        try:
            d = json.loads(sf.read_text())
        except (OSError, ValueError):
            d = None
        if d is None:
            add("FAIL", f"{home_rel(sf)} is missing or unreadable", "hyperbeam _hooks")
        else:
            add("PASS" if "hyperbeam-guard" in json.dumps(d) else "FAIL", "Claude hooks (guard and the dot states) are installed", "" if "hyperbeam-guard" in json.dumps(d) else "hyperbeam _hooks")
            want = cfg_get("claude_model")
            add("PASS" if d.get("model") == want else "YOU", f"Claude's default model is {d.get('model') or 'unset'}" + ("" if d.get("model") == want else f" (hyperbeam's setting is {want})"),
                "" if d.get("model") == want else f"claude --model {want}   (or /model {want} inside Claude)")
    if which in ("all", "lab"):
        msg = lab_ready()
        if msg:
            add("FAIL", "lab: " + msg.splitlines()[0], user_runs("setup.sh"))
        else:
            ps = subprocess.run(lab_sudo("true"), capture_output=True, stdin=subprocess.DEVNULL).returncode == 0
            add("PASS" if ps else "FAIL", "lab: runs commands as hblab" if ps else "lab: sudo as hblab does not work", "" if ps else user_runs("setup.sh"))
            u = shutil.disk_usage(LAB_HOME)
            add("PASS" if u.free > 2 ** 30 else "FAIL", f"lab: disk {u.used / 2**30:.1f} of {u.total / 2**30:.1f} GB used", "" if u.free > 2 ** 30 else "hyperbeam lab status")
        mode = Path.home().stat().st_mode & 0o777
        if mode & 0o005:
            add("YOU", f"{home_rel(Path.home())} is mode {mode:o}: the lab user can READ your home (it can't write it)", f"chmod 750 {Path.home()}")
        else:
            add("PASS", f"{home_rel(Path.home())} is mode {mode:o}: the lab user can't read your home")
        add("PASS" if shutil.which("podman") else "YOU", "podman " + ("is installed" if shutil.which("podman") else "is not installed: Docker-based tests can't run in the lab yet (docs/PODMAN.md)"),
            "" if shutil.which("podman") else user_runs("podman-setup.sh"))
    return out


def verify_merge():
    """Open a throwaway PR in hyperbeam's own repo (an empty commit on a branch, pushed from a temporary clone so your checkout is untouched), so the
    only thing left for the user is the Merge button. A PR from an earlier run that is still open is reused. -> [(status, text, how)]."""
    path = known_path("hyperbeam")
    slug = github_slug(path)
    if not slug or not gh_account(slug.split("/")[0]):
        return [("FAIL", "hyperbeam has no GitHub origin, or no gh login for its owner", "gh auth login")]
    left = [x for x in open_prs("hyperbeam", path, force=True) if x["branch"].startswith("verify-merge-test")]
    if left:
        return [("YOU", f"a throwaway PR is already open: #{left[0]['number']} {left[0]['url']}", "in the sidebar: select hyperbeam, press Merge (m), answer Yes. The PR merges, the checkout stays on main, the magenta branch goes away")]
    url = git_out(path, "config", "--get", "remote.origin.url")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="verify-merge.", dir=str(DATA_DIR)))
    br = "verify-merge-test-" + time.strftime("%Y%m%d-%H%M%S")
    try:
        for cmd in (["git", "clone", "-q", "--depth", "1", url, str(tmp / "r")], ["git", "-C", str(tmp / "r"), "checkout", "-q", "-b", br],
                    ["git", "-C", str(tmp / "r"), "-c", "user.name=hyperbeam verify", "-c", "user.email=noreply@hyperbeam.invalid", "commit", "-q", "--allow-empty", "-m", "verify merge (throwaway)"],
                    ["git", "-C", str(tmp / "r"), "push", "-q", "-u", "origin", br]):
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
            if r.returncode:
                return [("FAIL", f"could not prepare the throwaway branch: {(r.stderr or r.stdout).strip()[-160:]}", "")]
        rc, out, err = gh_run(slug, "pr", "create", "--head", br, "--base", default_branch(path), "--title", "verify merge (throwaway)",
                              "--body", "Opened by `hyperbeam verify merge`. Press Merge in the sidebar; nothing else changes.")
        if rc:
            subprocess.run(["git", "-C", str(tmp / "r"), "push", "-q", "origin", "--delete", br], capture_output=True)
            return [("FAIL", f"could not open the PR: {(err or out).strip()[-160:]}", "")]
        open_prs("hyperbeam", path, force=True)
        return [("PASS", f"opened a throwaway PR: {out.strip().splitlines()[-1] if out.strip() else br}"),
                ("YOU", "click Merge", "in the sidebar: select hyperbeam (its branch is magenta within a minute), press Merge (m), answer Yes")]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cmd_verify(a):
    rows = verify_merge() if a.what == "merge" else verify_checks(a.what)
    for st, text, how in rows:
        print(f"{st:<5} {text}")
        if how and st != "PASS":
            print(f"      run: {how}")
    n = {k: sum(1 for r in rows if r[0] == k) for k in ("PASS", "FAIL", "YOU")}
    print(f"\n{n['PASS']} passed, {n['FAIL']} failed, {n['YOU']} for you")
    return 1 if n["FAIL"] else 0


# ---------- shot: the sidebar as pictures, at a chosen width (rendered in the lab, brought back to ~/.cache/hyperbeam-shots) ----------
ANSI = {"black": (0, 0, 0), "red": (205, 49, 49), "green": (13, 188, 121), "brown": (229, 229, 16), "yellow": (229, 229, 16), "blue": (36, 114, 200),
        "magenta": (188, 63, 188), "cyan": (17, 168, 205), "white": (204, 204, 204), "brightblack": (102, 102, 102), "brightred": (241, 76, 76),
        "brightgreen": (35, 209, 139), "brightbrown": (245, 245, 67), "brightyellow": (245, 245, 67), "brightblue": (59, 142, 234),
        "brightmagenta": (214, 112, 214), "brightcyan": (41, 184, 219), "brightwhite": (255, 255, 255)}
SHOT_SCREENS = ["main", "pr", "project", "settings", "merge", "done"]


def _rgb(name, default):
    if name in (None, "default"):
        return default
    if name in ANSI:
        return ANSI[name]
    if re.fullmatch(r"[0-9a-fA-F]{6}", name):
        return tuple(int(name[i:i + 2], 16) for i in (0, 2, 4))
    return default


def render_png(screen, path, title):
    """A pyte screen as a PNG: DejaVu Sans Mono cells with the colours, bold and reverse of the terminal, a title strip and a ruler of the column edge."""
    from PIL import Image, ImageDraw, ImageFont
    fdir = "/usr/share/fonts/truetype/dejavu/"
    font, bold = ImageFont.truetype(fdir + "DejaVuSansMono.ttf", 16), ImageFont.truetype(fdir + "DejaVuSansMono-Bold.ttf", 16)
    cw, ch, pad, top = int(font.getlength("M")), 21, 10, 26
    BG, FG = (30, 30, 30), (204, 204, 204)
    img = Image.new("RGB", (screen.columns * cw + 2 * pad, screen.lines * ch + 2 * pad + top), (12, 12, 12))
    d = ImageDraw.Draw(img)
    d.text((pad, 4), title, font=font, fill=(150, 150, 150))
    d.rectangle([pad - 1, top + pad - 1, pad + screen.columns * cw, top + pad + screen.lines * ch], fill=BG, outline=(70, 70, 70))
    for y in range(screen.lines):
        row = screen.buffer[y]
        for x in range(screen.columns):
            c = row[x]
            fg, bg = _rgb(c.fg, FG), _rgb(c.bg, BG)
            if c.reverse:
                fg, bg = bg, fg
            px, py = pad + x * cw, top + pad + y * ch
            if bg != BG:
                d.rectangle([px, py, px + cw - 1, py + ch - 1], fill=bg)
            if c.data.strip():
                d.text((px, py), c.data, font=bold if c.bold else font, fill=fg)
    img.save(path)


def cmd_shot_render(a):
    """Runs in the lab: a throwaway set of projects (long names, a PR, a working and a waiting Claude, a branch), the menu in a pty at COLSxROWS,
    a picture and a text dump of each screen into --out."""
    import pty, select, fcntl, struct, termios, tempfile
    import pyte
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix="shot.", dir=os.environ.get("HB_SHOT_TMP") or "/tmp"))
    root, man, data, binp = base / "proj", base / "man", base / "share", base / "bin"
    for d in (root, man, binp):
        d.mkdir(parents=True)
    (binp / "claude").write_text("#!/bin/bash\nexec -a claude sleep 900\n")
    (binp / "claude").chmod(0o755)
    (base / "cfg.toml").write_text(f'projects_dir = "{root}"\nopen_mode = "sidebar"\nmenu_width = {a.cols}\n')
    env = dict(os.environ, PATH=f"{binp}:" + os.environ["PATH"], HB_CONFIG=str(base / "cfg.toml"), HB_MANIFESTS=str(man), XDG_DATA_HOME=str(data),
               XDG_CONFIG_HOME=str(base / "cfgdir"), TERM="xterm-256color", HB_SIDEBAR="1")
    for k in ("TMUX", "TMUX_PANE", "HB_PROJECT", "WAYLAND_DISPLAY"):
        env.pop(k, None)
    G = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    me = str(Path(__file__).resolve())
    uvrun = ["uv", "run", "--quiet", "--script", me]
    fixtures = [("hyperbeam", 3100, "review-loop", "running", None), ("dotwork", 3103, "feature/week-view-and-scroll", "working", ("51", "Add the week view and fix the scroll jump")),
                ("stenographr", None, "main", "waiting", None), ("algoviewz-platform", 3102, "main", "", None), ("trifactoria-landing", None, "main", "", None),
                ("alpha", 3101, "main", "running", None), ("journal-system", None, "main", "", None), ("automatr", None, "wip", "", None)]
    for name, port, branch, state, pr in fixtures:
        pd = root / name
        subprocess.run(["git", "init", "-q", "-b", "main", str(pd)])
        subprocess.run([*G, "-C", str(pd), "commit", "-q", "--allow-empty", "-m", "init"])
        if branch != "main":
            subprocess.run(["git", "-C", str(pd), "checkout", "-q", "-b", branch])
        if name != "trifactoria-landing" and name != "journal-system":
            (man / f"{name}.toml").write_text(f'path = "{pd}"\n' + (f"port = {port}\n" if port else ""))
    for name, port, branch, state, pr in fixtures:
        if state:
            subprocess.run([*uvrun, "open", name, "-d"], env=env, capture_output=True, stdin=subprocess.DEVNULL, timeout=120)
            pdata = data / "hyperbeam" / "projects" / f"{name}-{hashlib.sha1(str((root / name).resolve()).encode()).hexdigest()[:6]}"
            if state in ("working", "waiting"):
                pdata.mkdir(parents=True, exist_ok=True)
                (pdata / "claude").write_text("working\n" if state == "working" else "waiting finished responding\n")
        if pr:
            pdata = data / "hyperbeam" / "projects" / f"{name}-{hashlib.sha1(str((root / name).resolve()).encode()).hexdigest()[:6]}"
            pdata.mkdir(parents=True, exist_ok=True)
            (pdata / "prs.json").write_text(json.dumps({"time": time.time(), "prs": [{"number": int(pr[0]), "title": pr[1], "url": "https://github.com/x/y/pull/" + pr[0], "branch": "feature"}], "error": ""}))
    (base / "task.md").write_text("# Add the week view\n")
    subprocess.run([*uvrun, "work", "dotwork", str(base / "task.md")], env=env, capture_output=True, stdin=subprocess.DEVNULL, timeout=120)       # a running worker: the » mark
    (data / "hyperbeam").mkdir(parents=True, exist_ok=True)
    (data / "hyperbeam" / "rate-limits.json").write_text(json.dumps({"at": time.time(), "five_hour": {"used_percentage": 83, "resets_at": time.time() + 3 * 3600 + 120},
                                                                      "seven_day": {"used_percentage": 41, "resets_at": time.time() + 3 * 86400}}))
    (root / "dotwork" / "t.txt").write_text("x")                                    # an untracked file only: nothing to show but the PR
    for n in ("dotwork",):                                                      # github_slug needs a GitHub origin for the PR cache to be read
        subprocess.run(["git", "-C", str(root / n), "remote", "add", "origin", f"git@github-skillkraftz:skillkraftz/{n}.git"])
    subprocess.run(["tmux", "new-session", "-d", "-s", MENU, "-n", "home", str(binp / "claude")], env=env)
    class Scr(pyte.Screen):
        def report_device_status(self, *x, **k): pass
        def report_device_attributes(self, *x, **k): pass
    scr = Scr(a.cols, a.rows)
    stream = pyte.ByteStream(scr)
    pid, fd = pty.fork()
    if pid == 0:
        os.environ.clear()
        os.environ.update(env)
        os.execvp("uv", ["uv", "run", "--quiet", "--script", me, "_menu"])
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", a.rows, a.cols, 0, 0))

    def pump(secs=0.5):
        end = time.time() + secs
        while time.time() < end:
            if select.select([fd], [], [], 0.1)[0]:
                try:
                    dd = os.read(fd, 65536)
                except OSError:
                    return
                if dd:
                    stream.feed(dd)

    def text():
        return "\n".join(scr.display)

    def until(f, secs=60):
        end = time.time() + secs
        while time.time() < end:
            pump(0.4)
            if f():
                return True
        return False

    def find(needle):
        for y, l in enumerate(scr.display):
            if y and needle in l:
                return l.index(needle) + 1, y + 1

    def click(x, y):
        os.write(fd, f"\x1b[<0;{x};{y}M\x1b[<0;{x};{y}m".encode())

    def snap(name):
        render_png(scr, out / f"{name}-{a.cols}x{a.rows}.png", f"{name}  -  {a.cols} columns x {a.rows} rows")
        (out / f"{name}-{a.cols}x{a.rows}.txt").write_text("\n".join(l.rstrip() for l in scr.display).rstrip() + "\n")
        print(f"shot: {name}")
    ok = until(lambda: "alpha" in text() and "dotwork" in text(), 90)
    pump(5)
    if "main" in a.screens:
        snap("main")
    if "pr" in a.screens or "merge" in a.screens or "project" in a.screens:
        pos = find("dotwork")
        if pos:
            click(*pos)
        until(lambda: "PR #51" in text(), 30)
        pump(1)
        if "pr" in a.screens:
            snap("pr")
    if "merge" in a.screens:
        os.write(fd, b"m")
        until(lambda: "Merge PR" in text() or "Yes" in text(), 20)
        pump(1)
        snap("merge")
        os.write(fd, b"\x1b")
        pump(1.5)
    if "project" in a.screens:
        os.write(fd, b"j")
        until(lambda: "onboarded:" in text(), 30)
        pump(1)
        snap("project")
        os.write(fd, b"\x1b")
        pump(1.5)
    if "settings" in a.screens:
        os.write(fd, b"t")
        pump(2)
        snap("settings")
        os.write(fd, b"\x1b")
        pump(1.5)
    if "done" in a.screens:
        os.write(fd, b"d")
        pump(3)
        snap("done")
        os.write(fd, b"\x1b")
        pump(1)
    os.write(fd, b"q")
    return 0 if ok else 1


def cmd_shot(a):
    """hyperbeam shot [--cols 35] [--rows 40] [--screen ...]: pictures of the sidebar at that width. It runs in the lab (never on your tmux or screen) and the
    pictures are brought back to ~/.cache/hyperbeam-shots/<time>/ (the path is printed; Claude can read the PNGs)."""
    screens = SHOT_SCREENS if a.screen in (None, "all") else [a.screen]
    cols = 42 if a.phone else a.cols
    sid = time.strftime("%Y%m%d-%H%M%S")
    dest = f"{LAB_HOME}/shots/{sid}"
    cmd = ["--", "uv", "run", "--quiet", "--with", "pyte", "--with", "pillow", "--script", "hyperbeam", "_shot-render", "--cols", str(cols), "--rows", str(a.rows),
           "--out", dest, "--screens", ",".join(screens)]
    ns = types.SimpleNamespace(action="run", dir=str(Path(a.dir).expanduser()) if a.dir else str(HERE), name="hyperbeam", why=f"shot {cols}x{a.rows}", fresh=False, timeout=300, cmd=cmd, collect=dest, collect_to=None, quiet=False)
    return cmd_lab(ns)


def cmd_lab_collect(name_dest, src_in_lab):
    """Bring a folder the lab made back to the user: rsync as hblab (read) into a folder of the user's (write). -> (dest, number of files) or None."""
    dest = Path.home() / ".cache/hyperbeam-shots" / time.strftime("%Y%m%d-%H%M%S")
    dest.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["rsync", "-a", "-e", str(HERE / "lab/sudo-hblab"), f"lab:{src_in_lab}/", f"{dest}/"], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if r.returncode:
        print(f"lab: could not collect {src_in_lab}: {r.stderr.strip()[-200:]}", file=sys.stderr)
        return None
    return dest, sum(1 for _ in dest.rglob("*") if _.is_file())


