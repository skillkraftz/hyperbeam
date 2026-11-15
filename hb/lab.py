# hyperbeam, part 'lab': the lab (agent testing), lab digest. Runs in the namespace of the `hyperbeam` script (see its loader): no imports of its own.
# ---------- the lab: agent testing runs as the user `hblab`, whose home is a disk image (see lab/setup.sh) ----------
LAB_USER, LAB_HOME, LAB_DISPLAY = "hblab", Path("/srv/hblab"), ":99"
LAB_USERS_OWN = "The lab's setup (lab/setup.sh, remove.sh, podman-setup.sh, the sudoers rule, the disk image) is the user's: report this, and don't run or suggest running them."
LAB_SETUP = f"The lab user {LAB_USER} does not exist on this machine. {LAB_USERS_OWN}"
LAB_NESTED = ("This command starts the lab, and you are already in it (HB_LAB=1: a `hyperbeam lab run` is running you), where hblab has no sudo. Nothing is wrong with "
              "the lab and nothing on the machine needs changing. `hyperbeam tool`, `shot`, `NAME test` and `lab run` start the lab themselves, so do not put them inside "
              "`hyperbeam lab run`: run the program directly instead (a tool: `$HB_TOOLS/NAME/NAME`; tests: the project's own test command).")


TOOLS_SRC = Path(os.environ.get("HB_TOOLS_SRC") or HERE / "tools")       # the tools folder (HB_TOOLS_SRC: tests)
LAB_RUN_USAGE = ("usage: hyperbeam lab run [--dir DIR] [--name NAME] [--why TEXT] [--fresh] [--timeout SECONDS] [--] COMMAND...\n"
                 "options go before the command; one argument = a shell command line, several = argv.\n\n"
                 "example:  hyperbeam lab run --why \"unit tests\" --timeout 300 -- uv run pytest -q")
LAB_TOOLS = "/srv/hblab/cache/tools"       # pnpm lives here: npm-installed into the lab disk (corepack 0.24 can't run pnpm 12)
LAB_SYNC_EXCLUDE = [".git", "node_modules", ".venv", "venv", "__pycache__", ".next", "target", ".pytest_cache", ".hyperbeam",
                    "steno-*.txt", ".env", ".env.*", "*.pem", "*.key", "id_rsa*", "id_ed25519*"]
LAB_PORTS = (39000, 39999)          # the lab shares the machine's network: its servers use these (or port 0), never the projects' 3100+
LAB_LOG = lambda: DATA_DIR / "lab-runs.jsonl"


def lab_project_name(src):
    """The project a directory belongs to: for a worktree the name of the main checkout (not the branch folder), else the folder's name."""
    r = subprocess.run(["git", "-C", str(src), "rev-parse", "--path-format=absolute", "--git-common-dir"], capture_output=True, text=True)
    common = Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None
    return common.parent.name if common and common.name == ".git" else src.name


def lab_log_run(project, cwd, cmd, why, seconds, rc, tail):
    """One JSON line per `lab run`, written by this script (hblab can't write there): the base for a later digest of repeated lab work."""
    rec = dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), project=project, cwd=str(cwd), command=cmd[0] if len(cmd) == 1 else shlex.join(cmd),
               why=why, seconds=round(seconds, 1), exit=rc, tail=tail[-20:])
    try:
        LAB_LOG().parent.mkdir(parents=True, exist_ok=True)
        with LAB_LOG().open("a") as f:
            f.write(json.dumps(rec) + "\n")
        LAB_LOG().chmod(0o600)
    except OSError as e:
        print(f"(lab: could not write the run log: {e})", file=sys.stderr)


def cmd_lab_log(a):
    try:
        runs = [json.loads(l) for l in LAB_LOG().read_text().splitlines() if l.strip()]
    except (OSError, ValueError):
        runs = []
    if a.today:
        runs = [r for r in runs if r["time"].startswith(time.strftime("%Y-%m-%d"))]
    if not runs:
        print("no lab runs logged" + (" today" if a.today else "") + f" ({home_rel(LAB_LOG())})")
        return 0
    for r in runs:
        cmd = r["command"] if len(r["command"]) < 70 else r["command"][:69] + "…"
        print(f"{r['time'][5:16].replace('T', ' ')}  {r['project']:<14} {'ok ' if r['exit'] == 0 else 'rc' + str(r['exit']):<5}{r['seconds']:>6.1f}s  {r['why'] or '(no why)'}  | {cmd}")
    fails = [r for r in runs if r["exit"] != 0]
    print(f"\n{len(runs)} runs, {sum(r['seconds'] for r in runs) / 60:.1f} min, {len(fails)} failed")
    again = {}
    for r in runs:
        again.setdefault((r["project"], r["command"]), []).append(r)
    rep = [(k, v) for k, v in again.items() if len(v) > 1]
    if rep:
        print("repeated (candidates for a small tool):")
        for (proj, c), v in sorted(rep, key=lambda kv: -sum(r["seconds"] for r in kv[1])):    # by total time, not by count
            print(f"  {len(v)}x  {sum(r['seconds'] for r in v) / 60:.1f} min  {proj}: {c[:90]}")
    return 0


# Runs as hblab (`sudo -u hblab python3 -c LAB_PY MODE ARGS`). Every `lab run` has an id; its processes (and everything they start, even daemonised
# ones) carry HB_RUN_ID=<id> in their environment, and the run is recorded in /srv/hblab/runs/<id>.json while it is alive. A run is alive while some
# process has its tag: records of dead runs are removed here. Modes: list | stop PROJECT | done ID | killall | clean.
LAB_PY = r"""
import glob, json, os, shutil, signal, sys, time
HOME = "/srv/hblab"; ME = os.getpid(); UID = os.getuid()
def tagged():
    out = {}
    for p in os.listdir("/proc"):
        if not p.isdigit() or int(p) == ME:
            continue
        try:
            if os.stat(f"/proc/{p}").st_uid != UID:
                continue
            env = open(f"/proc/{p}/environ", "rb").read().split(b"\0")
        except OSError:
            continue
        for e in env:
            if e.startswith(b"HB_RUN_ID="):
                out.setdefault(e[10:].decode(), []).append(int(p))
                break
    return out
def records(alive):
    recs = []
    for f in glob.glob(HOME + "/runs/*.json"):
        try:
            r = json.load(open(f))
        except Exception:
            r = None
        if r and r.get("id") in alive:
            recs.append(r)
        else:
            try: os.unlink(f)
            except OSError: pass
    return recs
def kill(ids, everything=False):
    n = 0
    for sig, wait in ((signal.SIGTERM, 3), (signal.SIGKILL, 0)):
        pids = [p for i, ps in tagged().items() if everything or i in ids for p in ps]
        if everything:
            pids = [int(p) for p in os.listdir("/proc") if p.isdigit() and int(p) != ME and os.stat(f"/proc/{p}").st_uid == UID]
        if not pids:
            break
        for p in pids:
            try: os.kill(p, sig); n += 1
            except OSError: pass
        t = time.time() + wait
        while wait and time.time() < t and any(os.path.exists(f"/proc/{p}") for p in pids):
            time.sleep(0.2)
    return n
def cleanup(i):
    for d in (f"{HOME}/rt/{i}", f"{HOME}/tmux/{i}"):
        shutil.rmtree(d, ignore_errors=True)
    try: os.unlink(f"{HOME}/runs/{i}.json")
    except OSError: pass
mode = sys.argv[1]
if mode == "list":
    print(json.dumps(records(tagged())))
elif mode == "stop":
    recs = [r for r in records(tagged()) if r["project"] == sys.argv[2]]
    ids = {r["id"] for r in recs}
    n = kill(ids)
    for i in ids: cleanup(i)
    print(json.dumps({"stopped": sorted(ids), "killed": n}))
elif mode == "done":
    kill({sys.argv[2]}); cleanup(sys.argv[2])
elif mode == "killall":
    n = kill(set(), everything=True)
    for f in glob.glob(HOME + "/runs/*.json"): os.unlink(f)
    print(json.dumps({"killed": n}))
elif mode == "clean":
    alive = set(tagged())
    for d in glob.glob(HOME + "/rt/*") + glob.glob(HOME + "/tmux/*"):
        b = os.path.basename(d)
        if len(b) == 8 and all(c in "0123456789abcdef" for c in b) and b not in alive:      # per-run folders only (never older, shared ones)
            shutil.rmtree(d, ignore_errors=True)
"""


def lab_py(*args):
    r = subprocess.run(lab_sudo("python3", "-c", LAB_PY, *args), capture_output=True, text=True, stdin=subprocess.DEVNULL)
    try:
        return json.loads(r.stdout) if r.stdout.strip() else None
    except ValueError:
        return None


def lab_runs():
    """Active lab runs: [{id, project, why, command, cwd, pgid, start}] (records of runs that are gone are removed on the way)."""
    return sorted(lab_py("list") or [], key=lambda r: r.get("start", 0))


def lab_caller_project():
    """The project the caller means: the folder's project when inside a git repo, else $HB_PROJECT."""
    cwd = Path.cwd()
    if subprocess.run(["git", "-C", str(cwd), "rev-parse", "--git-dir"], capture_output=True).returncode == 0:
        return lab_project_name(cwd)
    return os.environ.get("HB_PROJECT") or None


def fmt_age(sec):
    sec = int(sec)
    return f"{sec}s" if sec < 60 else f"{sec // 60}m{sec % 60:02d}s" if sec < 3600 else f"{sec // 3600}h{sec % 3600 // 60:02d}m"


# ---------- lab digest: what the day's lab runs show (plain script, no tokens) ----------
KILLED = lambda rc: rc < 0 or rc in (137, 143)        # stopped by a signal (a reset, a timeout kill): not a test result
TRIVIAL_MIN_SECONDS = 30                              # a repeated command is only worth a tool if it cost this much in total


def norm_command(cmd):
    """A command with what changes between runs stripped: a leading `cd X &&`, `2>&1`, `| tail/head`, paths, ids, long numbers."""
    c = " ".join(str(cmd).split())
    c = re.sub(r"^(?:cd \S+ && )+", "", c)
    c = re.sub(r"\s*2>&1", "", c)
    c = re.sub(r"\s*\|\s*(?:tail|head)(?: -\w+)*(?: \d+)?\s*$", "", c)
    out = []
    for t in c.split(" "):
        if "/" in t or re.search(r"\.(?:py|js|ts|tsx|jsx|mjs|toml|json|md|txt|sh|log|csv|yml|yaml)$", t):
            t = "<path>"
        elif re.fullmatch(r"[0-9a-f]{7,}", t):
            t = "<id>"
        elif re.fullmatch(r"\d{3,}", t):
            t = "<n>"
        if not (out and out[-1] == t == "<path>"):
            out.append(t)
    return " ".join(out)


def read_lab_runs(since=None):
    """The run log (lab-runs.jsonl) as a list of dicts, oldest first; `since` = 'YYYY-MM-DD' keeps runs from that day on."""
    try:
        runs = [json.loads(l) for l in LAB_LOG().read_text().splitlines() if l.strip()]
    except (OSError, ValueError):
        return []
    return [r for r in runs if not since or r["time"][:10] >= since]


def lab_digest(runs):
    """-> dict: per-project totals, flaky commands, slowest, repeated commands and sequences, and the tool candidates among them. Runs of the tools'
    own tests ('tool test: ...') are not work and are left out."""
    runs = [r for r in runs if not (r.get("why") or "").startswith("tool test:")]
    for r in runs:
        r["_n"] = norm_command(r["command"])
    proj = {}
    for r in runs:
        d = proj.setdefault(r["project"], dict(runs=0, seconds=0.0, failed=0, killed=0))
        d["runs"] += 1
        d["seconds"] += r["seconds"]
        d["failed"] += r["exit"] > 0 and not KILLED(r["exit"])
        d["killed"] += KILLED(r["exit"])
    groups = {}
    for r in runs:
        groups.setdefault((r["project"], r["_n"]), []).append(r)
    flaky = []
    for (pj, n), rs in groups.items():
        for day in sorted({x["time"][:10] for x in rs}):
            d = [x for x in rs if x["time"][:10] == day]
            seen_fail = False
            for x in d:
                if x["exit"] > 0 and not KILLED(x["exit"]):
                    seen_fail = True
                elif x["exit"] == 0 and seen_fail:
                    flaky.append(dict(project=pj, command=n, day=day, failed=sum(1 for y in d if y["exit"] > 0 and not KILLED(y["exit"])), passed=sum(1 for y in d if y["exit"] == 0)))
                    break
    slow = sorted(({"project": pj, "command": n, "max": max(x["seconds"] for x in rs), "count": len(rs), "total": sum(x["seconds"] for x in rs)} for (pj, n), rs in groups.items()),
                  key=lambda d: -d["total"])[:5]                # where the time went: count x duration, so 6 x 15 min ranks above 1 x 45 min
    repeated = sorted(({"project": pj, "command": n, "count": len(rs), "total": sum(x["seconds"] for x in rs),
                        "failed": sum(1 for x in rs if x["exit"] > 0 and not KILLED(x["exit"]))} for (pj, n), rs in groups.items() if len(rs) >= 3), key=lambda d: -d["total"])
    seqs = {}
    for pj in {r["project"] for r in runs}:
        rs = sorted((r for r in runs if r["project"] == pj), key=lambda r: r["time"])
        sessions, cur = [], []
        for r in rs:                                    # a new session after a 20 minute gap
            if cur and time.mktime(time.strptime(r["time"], "%Y-%m-%dT%H:%M:%S")) - time.mktime(time.strptime(cur[-1]["time"], "%Y-%m-%dT%H:%M:%S")) > 1200:
                sessions.append(cur)
                cur = []
            cur.append(r)
        sessions.append(cur)
        for n in (3, 2):
            for sess in sessions:
                for i in range(len(sess) - n + 1):
                    win = sess[i:i + n]
                    key = (pj, tuple(x["_n"] for x in win))
                    if len(set(key[1])) > 1:
                        e = seqs.setdefault(key, dict(count=0, total=0.0))
                        e["count"] += 1
                        e["total"] += sum(x["seconds"] for x in win)
    sequences = [dict(project=k[0], commands=list(k[1]), **v) for k, v in seqs.items() if v["count"] >= 3]
    sequences = [q for q in sequences if not any(len(o["commands"]) > len(q["commands"]) and o["project"] == q["project"] and o["count"] == q["count"]
                                                 and any(o["commands"][i:i + len(q["commands"])] == q["commands"] for i in range(len(o["commands"]))) for o in sequences)]
    sequences.sort(key=lambda d: -d["total"])
    cands = [dict(kind="command", project=r["project"], what=r["command"], count=r["count"], total=r["total"]) for r in repeated if r["total"] >= TRIVIAL_MIN_SECONDS] + \
            [dict(kind="sequence", project=q["project"], what=" -> ".join(q["commands"]), count=q["count"], total=q["total"]) for q in sequences if q["total"] >= TRIVIAL_MIN_SECONDS]
    cands.sort(key=lambda c: -c["total"])                       # commands and sequences together, biggest total cost first
    tools = {}
    for n in tool_names():
        pats = []
        try:
            pats = [re.compile(x.strip()) for x in (TOOLS_SRC / n / "replaces").read_text().splitlines() if x.strip()]
        except (OSError, re.error):
            pass
        used = [r for r in runs if (r.get("why") or "") == f"tool {n}"]
        by_hand = [r for r in runs if (r.get("why") or "") != f"tool {n}" and any(p.search(r["command"]) for p in pats)]
        tools[n] = dict(used=len(used), failed=sum(1 for r in used if r["exit"] != 0), by_hand=len(by_hand))
    return dict(runs=len(runs), seconds=sum(r["seconds"] for r in runs), projects=proj, flaky=flaky, slow=slow, repeated=repeated, sequences=sequences, candidates=cands,
                tools=tools)


def mins(sec):
    return f"{sec / 60:.1f} min" if sec >= 60 else f"{sec:.0f} s"


def format_digest(d, tool_notes=(), title="Lab digest"):
    if not d["runs"]:
        return f"{title}: no lab runs logged."
    L = [f"{title}: {d['runs']} runs, {mins(d['seconds'])}", "", "per project"]
    for pj, v in sorted(d["projects"].items(), key=lambda kv: -kv[1]["seconds"]):
        L.append(f"  {pj:<16} {v['runs']:>3} runs  {mins(v['seconds']):>9}  {v['failed']} failed" + (f", {v['killed']} killed (stopped by a signal)" if v["killed"] else ""))
    L += ["", "flaky (the same command failed, then passed, the same day)"] + ([f"  {x['project']}: {x['command'][:90]}  ({x['failed']} failed, {x['passed']} passed, {x['day']})" for x in d["flaky"]] or ["  none"])
    L += ["", "where the time went (total = count x average; the biggest total first, so a command run often can outrank one slow run)"]
    L += [f"  {mins(x['total']):>9}  {x['project']}: {x['command'][:80]}  ({x['count']}x, avg {mins(x['total'] / x['count'])}, longest {mins(x['max'])})" for x in d["slow"]]
    L += ["", "tool candidates (repeated work that cost real time)"]
    L += [f"  {c['count']}x  {mins(c['total']):>9}  {c['project']}: {c['what'][:100]}  [{c['kind']}]" for c in d["candidates"]] or ["  none"]
    tl = [f"  {n}: used {v['used']}x, failed {v['failed']}" + (f", done by hand {v['by_hand']}x (use the tool)" if v["by_hand"] else "")
          for n, v in d.get("tools", {}).items()]
    if tl or tool_notes:
        L += ["", "tools"] + tl + [f"  {n}" for n in tool_notes]
    return "\n".join(L)


def tool_names():
    """Tools: tools/NAME/ with an executable NAME, or a Go tool (go.mod) that is built on first use."""
    t = TOOLS_SRC
    return [x.name for x in sorted(t.iterdir()) if x.is_dir() and ((x / x.name).exists() or (x / "go.mod").exists())] if t.is_dir() else []


def build_tool(n):
    """A Go tool (tools/NAME/go.mod) is built to tools/NAME/NAME when a source is newer than the binary. Compiling is not a test: it runs as
    the user, and the binary goes into the lab with tools/. -> None, or why the build failed."""
    d = TOOLS_SRC / n
    if not (d / "go.mod").exists():
        return None
    b = d / n
    newest = max(f.stat().st_mtime for f in [d / "go.mod", *d.rglob("*.go")])
    if b.exists() and b.stat().st_mtime >= newest:
        return None
    try:
        r = subprocess.run(["go", "build", "-o", n, "."], cwd=d, capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        return "go is not installed (it builds this tool)"
    return None if r.returncode == 0 else "go build failed: " + ((r.stderr or r.stdout).strip().splitlines() or ["?"])[-1][:120]


def run_tool_tests(names=None):
    """Run each tool's test (tools/NAME/test) in the lab. -> [(name, ok, last output line)]. Needs the lab; ([] and no error) without tools."""
    out = []
    for n in names or tool_names():
        err = build_tool(n)
        if err:
            out.append((n, False, err))
            continue
        if not (TOOLS_SRC / n / "test").exists():
            out.append((n, False, "no test file (tools/%s/test)" % n))
            continue
        ns = types.SimpleNamespace(action="run", dir=str(TOOLS_SRC), name="hyperbeam-tools", why=f"tool test: {n}", fresh=False, timeout=180, cmd=["--", "bash", f"{n}/test"], quiet=True)
        rc = cmd_lab(ns)
        tail = (read_lab_runs()[-1:] or [{"tail": []}])[0]["tail"]
        out.append((n, rc == 0, (tail[-1] if tail else "")[:100]))
    return out


def tool_test_notes():
    """Notes for the digest: a failing tool test (or a lab that is not there to run them)."""
    if not tool_names():
        return []
    if lab_ready():
        return ["tool tests not run: the lab is not ready"]
    return [f"tool {n}: its test FAILS ({tail})" for n, ok, tail in run_tool_tests() if not ok]


TOOLS_CHECK = DATA_DIR / "tools-check.json"


def daily_tool_check():
    """Once a day (the first sidebar start): every tool's test in the lab, so a broken tool shows before agents route around it.
    -> the failing [(name, why)], or None when it already ran today, there are no tools, or the lab isn't ready."""
    try:
        if json.loads(TOOLS_CHECK.read_text()).get("date") == time.strftime("%Y-%m-%d"):
            return None
    except (OSError, ValueError):
        pass
    if not tool_names() or lab_ready():
        return None
    failing = [(n, tail) for n, ok, tail in run_tool_tests() if not ok]
    TOOLS_CHECK.write_text(json.dumps({"date": time.strftime("%Y-%m-%d"), "failing": failing}))
    return failing


def tool_check_findings():
    """Quiet notes for the hyperbeam row from the last daily check (cleared by the next check, or by `hyperbeam tool --test` passing)."""
    try:
        failing = json.loads(TOOLS_CHECK.read_text()).get("failing", [])
    except (OSError, ValueError):
        return []
    return [f"tool {n} fails its test: {why} (hyperbeam tool --test {n})" for n, why in failing if n in tool_names()]


def cmd_lab_digest(a):
    since = a.since or (time.strftime("%Y-%m-%d") if a.today else None)
    d = lab_digest(read_lab_runs(since))
    print(format_digest(d, tool_test_notes() if not a.no_tests else (), "Lab digest" + (f" since {since}" if since else "")))
    return 0


def cmd_tool(a):
    """hyperbeam tool NAME [ARGS]: a tool of tools/ in the lab, in the current project's synced copy. --list prints TOOLS.md. --test [NAME] runs tests."""
    if a.list:
        print((HERE / "TOOLS.md").read_text() if (HERE / "TOOLS.md").is_file() else "no TOOLS.md")
        return 0
    if os.environ.get("HB_LAB"):
        print(LAB_NESTED)
        return 2
    if a.test:
        res = run_tool_tests([a.name] if a.name else None)
        try:                                       # a passing test clears that tool's red finding
            d = json.loads(TOOLS_CHECK.read_text())
            d["failing"] = [f for f in d.get("failing", []) if not any(n == f[0] and ok for n, ok, _ in res)]
            TOOLS_CHECK.write_text(json.dumps(d))
        except (OSError, ValueError):
            pass
        for n, ok, tail in res:
            print(f"{'PASS' if ok else 'FAIL'} {n}" + ("" if ok else f"  {tail}"))
        return 0 if all(ok for _, ok, _ in res) else 1
    if not a.name:
        print("usage: hyperbeam tool NAME [ARGS...]   (hyperbeam tool --list shows the tools, hyperbeam tool --test [NAME] runs their tests)")
        return 2
    if a.name not in tool_names():
        print(f"hyperbeam tool: no tool called {a.name}. Tools: {', '.join(tool_names()) or 'none yet'}  (hyperbeam tool --list)")
        return 2
    err = build_tool(a.name)
    if err:
        print(f"hyperbeam tool {a.name}: {err}  (hyperbeam tool --test {a.name})")
        return 1
    ns = types.SimpleNamespace(action="run", dir=a.dir, name=None, why=f"tool {a.name}", fresh=False, timeout=a.timeout, cmd=["--", f"{LAB_HOME}/tools/{a.name}/{a.name}", *a.args])
    return cmd_lab(ns)


