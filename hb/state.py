# hyperbeam, part 'state': scan, per-project data folders, migration, last opened, session record. Runs in the namespace of the `hyperbeam` script (see its loader): no imports of its own.
# ---------- scan ----------
def owner_of(url):
    if not url:
        return "no remote"
    m = re.search(r"[:/]([^/:]+)/[^/]+?(?:\.git)?/?$", url)
    if not m:
        return "other"
    return "mine" if m.group(1).lower() in ACCOUNTS else "other"


def scan():
    repos = []
    for dp, dns, fns in os.walk(ROOT):
        if ".git" in dns or ".git" in fns:
            repos.append(Path(dp))
        dns[:] = sorted(d for d in dns if d not in SKIP)
    rows = []
    for p in repos:
        url = run("git", "-C", str(p), "remote", "get-url", "origin")
        rows.append(dict(path=p, git=True, remote=url, owner=owner_of(url),
                         dirty=bool(run("git", "-C", str(p), "status", "--porcelain"))))
    for d in sorted(ROOT.iterdir()):
        if d.is_dir() and not d.name.startswith(".") \
                and not any(r["path"] == d or d in r["path"].parents for r in rows):
            rows.append(dict(path=d, git=False, remote="", owner="no git", dirty=False))
    for r in rows:
        r["name"] = str(r["path"].relative_to(ROOT)).replace("/", "_")
    return sorted(rows, key=lambda r: r["name"].lower())


def load_manifests():
    out = {}
    for f in sorted(MANIFESTS.glob("*.toml")):
        try:
            out[f.stem] = tomllib.loads(f.read_text())
        except tomllib.TOMLDecodeError:
            pass
    return out


def running_sessions():
    return set(tmux("list-sessions", "-F", "#{session_name}", check=False).stdout.split())


# ---------- per-project data: DATA_DIR/projects/<name>-<6 hex of the absolute path>/ , linked into the project as .hyperbeam ----------
_PATHS = {}


def known_path(name):
    """The project's folder: manifest, hyperbeam itself, ROOT/name (nested names use _ for /), else a scan; ROOT/name if nothing matches."""
    if name in _PATHS:
        return _PATHS[name]
    man = load_manifests().get(name)
    if man:
        p = manifest_path(man)
    elif name == "hyperbeam" and not (ROOT / "hyperbeam").is_dir():       # normally ~/projects/hyperbeam, the dev folder; HERE (the installed copy) is the app
        p = HERE
    else:
        p = next((c for c in (ROOT / name, ROOT / name.replace("_", "/")) if c.is_dir()), None)
        if p is None:
            row = next((r for r in scan() if r["name"] == name), None) if ROOT.is_dir() else None
            p = row["path"] if row else ROOT / name
    _PATHS[name] = p
    return p


def project_dir(name, path=None, create=True):
    """Everything hyperbeam keeps for one project. The hash of the absolute path keeps two same-named projects in different folders apart."""
    p = Path(path) if path else known_path(name)
    d = DATA_DIR / "projects" / f"{name}-{hashlib.sha1(str(p.resolve()).encode()).hexdigest()[:6]}"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


GIT_IGNORE_LINE = ".hyperbeam"


def ensure_git_ignore():
    f = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "git" / "ignore"
    try:
        have = f.read_text().splitlines() if f.exists() else []
        if GIT_IGNORE_LINE not in (x.strip() for x in have):
            f.parent.mkdir(parents=True, exist_ok=True)
            with f.open("a") as fh:
                fh.write(("" if not have or f.read_text().endswith("\n") else "\n") + GIT_IGNORE_LINE + "\n")
    except OSError:
        pass


def link_force(link, target):
    """Make `link` a symlink to `target` (recreated if missing or pointing elsewhere); a real file or folder there is left alone."""
    if link.is_symlink():
        if os.readlink(link) == str(target):
            return True
        link.unlink()
    elif link.exists():
        return False
    link.symlink_to(target)
    return True


def ensure_link(name, path=None):
    """On Open: <project>/.hyperbeam -> the project's data folder (made again if deleted; the data was never inside the project),
    RULES.md in that folder -> the one in the hyperbeam repo."""
    p = Path(path) if path else known_path(name)
    if not p.is_dir():
        return None
    d = project_dir(name, p)
    link_force(d / "RULES.md", HERE / "RULES.md")
    (d / "notes").mkdir(exist_ok=True)
    ensure_git_ignore()
    try:
        link_force(p / ".hyperbeam", d)
    except OSError:
        pass
    return d


# ---------- migration: ~/.local/state/hyperbeam -> ~/.local/share/hyperbeam (per project folders) ----------
PER_PROJECT = {"layouts": "layout.json", "status": "status.json", "claude": "claude", "auto": "auto", "waiting": "waiting", "startcheck": "startcheck.txt"}


def migrate_state(old=None):
    """Copy the old state folder into the new layout, check every file arrived, then remove the old folder. Nothing already in the new
    place is overwritten. Returns (files copied, problems); the old folder is kept if there are any problems."""
    old = Path(old) if old else OLD_STATE_DIR
    if not old.is_dir() or old.resolve() == DATA_DIR.resolve():
        return 0, []
    pairs = []
    for f in sorted(x for x in old.rglob("*") if x.is_file() or x.is_symlink()):
        rel = f.relative_to(old)
        kind = rel.parts[0]
        if kind in PER_PROJECT and len(rel.parts) == 2:
            name = f.name[:-len(f.suffix)] if kind in ("layouts", "status", "startcheck") else f.name
            dst = project_dir(name) / PER_PROJECT[kind]
        elif kind == "prompts" and len(rel.parts) == 2:
            m = re.match(r"^(.*)-\d{8}-\d{6}\.md$", f.name)
            dst = project_dir(m.group(1) if m else "unsorted") / "prompts" / f.name
        else:
            dst = DATA_DIR / rel
        pairs.append((f, dst))
    done, bad = 0, []
    for src, dst in pairs:
        try:
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst, follow_symlinks=False)
                done += 1
            if not (dst.exists() or dst.is_symlink()):
                bad.append(str(src))
        except OSError as e:
            bad.append(f"{src}: {e}")
    if not bad:
        shutil.rmtree(old)
    return done, bad


# ---------- state (last opened) ----------
def load_state():
    try:
        return json.loads((STATE_DIR / "state.json").read_text())
    except (OSError, ValueError):
        return {"opened": {}}


def touch_opened(name):
    st = load_state()
    st.setdefault("opened", {})[name] = time.time()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / "state.json").write_text(json.dumps(st))
    journal_record(name)


# ---------- session record (journal.json): which projects were worked on since the menu started ----------
JOURNAL = lambda: STATE_DIR / "journal.json"


def load_journal():
    try:
        d = json.loads(JOURNAL().read_text())
    except (OSError, ValueError):
        d = {}
    d.setdefault("projects", {})
    return d


def save_journal(d):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    JOURNAL().write_text(json.dumps(d, indent=1))


def journal_start():
    """The menu started. A record that wasn't cleared by a completed Done for now survives, with its original start."""
    d = load_journal()
    d.setdefault("started", time.time())
    d["menu_started"] = time.time()
    save_journal(d)


def journal_record(name):
    d = load_journal()
    now = time.time()
    d.setdefault("started", now)
    d["projects"].setdefault(name, {"first": now})["last"] = now
    save_journal(d)


def journal_clear():
    JOURNAL().unlink(missing_ok=True)


def build_projects():
    mans, run_set, opened = load_manifests(), running_sessions(), load_state().get("opened", {})
    rows = scan()
    for r in rows:
        m = mans.get(r["name"])
        r["manifest"] = m is not None
        r["port"] = m.get("port") if m else None
        r["running"] = sanitize(r["name"]) in run_set
        r["worker"] = worker_sess(r["name"]) in run_set
        r["opened"] = opened.get(r["name"], 0)
    rows.append(dict(name=MENU, path=MANAGER_DIR, git=True, remote="", owner="manager", dirty=False, manifest=False, port=None,
                     running=MENU in run_set, opened=opened.get(MENU, 0)))      # the manager: the first row, not a project in ~/projects
    return rows


def ago(ts):
    s = int(time.time() - ts)
    return "now" if s < 60 else f"{s // 60}m" if s < 3600 else f"{s // 3600}h" if s < 86400 else f"{s // 86400}d"


