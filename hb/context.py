# hyperbeam, part 'context': align facts, context bundle, copy report. Runs in the namespace of the `hyperbeam` script (see its loader): no imports of its own.
# ---------- Align: the facts ALIGN.md compares the project's docs against ----------
def align_facts(path):
    """Facts about the real repo, as text, for ALIGN.md: visibility (gh), docs layout, tests, ignores, the hyperbeam wiring, and doc lines that
    look like claims about visibility (so a stale one can be spotted against the real visibility)."""
    path = Path(path)
    out = []
    r = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner,visibility", "-q", ".nameWithOwner + \" \" + .visibility"], cwd=path,
                       capture_output=True, text=True, timeout=15) if shutil.which("gh") else None
    vis = r.stdout.strip().split()[-1].lower() if r and r.returncode == 0 and r.stdout.strip() else ""
    out.append(f"repo on GitHub: {r.stdout.strip()}" if vis else "repo on GitHub: unknown (no gh, no remote, or not logged in)")

    def has(*names):
        return [n for n in names if (path / n).exists()]
    out.append("hyperbeam files: " + (", ".join(has("CLAUDE.md", "README.md", "docs/DECISIONS.md", "PRIVATE.md")) or "none of CLAUDE.md, README.md, docs/DECISIONS.md, PRIVATE.md"))
    docs = sorted(str(f.relative_to(path)) for f in (path / "docs").rglob("*.md")) if (path / "docs").is_dir() else []
    out.append("docs/: " + (", ".join(docs[:30]) or "none"))
    like = [str(f.relative_to(path)) for f in path.glob("*.md") if re.search(r"decision|adr|architecture|design|product|spec|notes", f.name, re.I)] \
        + [d for d in docs if re.search(r"decision|adr|architecture|design|product|model|spec", d, re.I) and not d.endswith("DECISIONS.md")]
    out.append("other decision/design-like docs (how do they relate to docs/DECISIONS.md?): " + (", ".join(like) or "none"))
    claude = (path / "CLAUDE.md").read_text(errors="replace") if (path / "CLAUDE.md").is_file() else ""
    out.append("CLAUDE.md imports the rules (@.hyperbeam/RULES.md): " + ("yes" if re.search(r"^@(?:\.hyperbeam/)?RULES\.md\s*$", claude, re.M) else "no"))
    out.append("CLAUDE.md has an 'Exceptions to hyperbeam rules' section: " + ("yes" if re.search(r"^#+\s*Exceptions to hyperbeam rules", claude, re.M | re.I) else "no"))
    tests = []
    pj = path / "package.json"
    if pj.is_file():
        try:
            sc = json.loads(pj.read_text()).get("scripts", {})
            tests += [f"package.json script `{k}`" for k in sc if re.search(r"test|e2e|lint|check", k)]
        except ValueError:
            pass
    tests += [n for n in has("tests", "test", "pytest.ini", "vitest.config.ts", "vitest.e2e.config.ts", "playwright.config.ts", "tox.ini", "Makefile") ]
    out.append("tests: " + (", ".join(tests) or "none found"))
    dock = [str(f.relative_to(path)) for f in list(path.glob("docker-compose*")) + list(path.glob("compose*.y*ml")) + list(path.glob("tests/**/docker-compose*"))[:5]]
    out.append("docker compose files (Docker-based tests are an exception, never run in the lab): " + (", ".join(dock) or "none"))
    gi = (path / ".gitignore").read_text(errors="replace").splitlines() if (path / ".gitignore").is_file() else []
    envs = [f.name for f in path.glob(".env*") if not f.name.endswith((".example", ".sample"))]
    out.append(f".gitignore: {'has' if any(l.strip().startswith('.env') for l in gi) else 'no'} .env rule; env files present: {', '.join(envs) or 'none'}"
               + ("; steno-*.txt rule: " + ("yes" if any("steno" in l for l in gi) else "no")))
    claims = []
    for fn in ("CLAUDE.md", "README.md"):
        f = path / fn
        if f.is_file():
            for i, l in enumerate(f.read_text(errors="replace").splitlines(), 1):
                if re.search(r"\b(not public|private repo|private repository|closed[- ]source|internal only|public repo|open[- ]source|is public|is private)\b", l, re.I):
                    claims.append(f"{fn}:{i}: {l.strip()[:140]}")
    out.append("standard verbs (install, update, test, version, help; a project's own script/target beats hyperbeam's default): " + verbs_facts(path, path.name))
    stale = stale_doc_items(path)
    out.append("docs that may be stale (commands/paths that don't exist, docs older than the setup): " + ("; ".join(f"{d} {w}" for d, w in stale[:8]) or "none found"))
    out.append("lines that claim public/private" + (f" (real visibility: {vis})" if vis else "") + ": " + ("; ".join(claims[:6]) or "none"))
    return "\n".join(f"- {x}" for x in out)


def cmd_align_facts(a):
    path = Path(a.path) if a.path else known_path(os.environ.get("HB_PROJECT", ""))
    print(align_facts(path))
    return 0


# ---------- context bundle: what a new chat (web or Claude Code) needs, in one paste ----------
def recent_history(path):
    """Branch, upstream, uncommitted summary and the last 20 commits. Only cheap git calls, so it stays fast on large repos: `log -n 20` reads
    20 commits, `status -uno` skips the untracked-file scan (the slow part on a big tree), `rev-list --count` on the upstream range."""
    def g(*a):
        r = subprocess.run(["git", "-C", str(path), *a], capture_output=True, text=True, timeout=10, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
        return r.stdout.rstrip("\n") if r.returncode == 0 else ""      # not strip(): status lines start with a space
    if not g("rev-parse", "--git-dir"):
        return "(not a git repository)"
    br = g("symbolic-ref", "--short", "-q", "HEAD") or f"(detached at {g('rev-parse', '--short', 'HEAD')})"
    lines = [f"branch: {br}"]
    ahead = g("rev-list", "--left-right", "--count", "@{u}...HEAD")
    if ahead:
        behind, ah = ahead.split()
        lines.append(f"upstream: {g('rev-parse', '--abbrev-ref', '@{u}')} ({ah} ahead, {behind} behind)")
    st = [l for l in g("status", "--porcelain=v1", "-uno").splitlines() if l.strip()]
    lines.append(f"uncommitted (tracked files): {len(st)}" + (" - " + ", ".join(l[3:] for l in st[:8]) + (", ..." if len(st) > 8 else "") if st else ""))
    lines += ["", "last 20 commits:"] + [f"  {l}" for l in g("log", "-n", "20", "--no-color", "--date=short", "--pretty=format:%h %ad %s").splitlines()]
    return "\n".join(lines)


def context_bundle(name, path=None, full=False, parts_only=False):
    """One text to paste into a chat: header, RULES.md, the project's CLAUDE.md, docs/DECISIONS.md, README, hyperbeam manifest, recent history."""
    path = Path(path) if path else known_path(name)

    def first(*names):
        for n in names:
            f = path / n
            if f.is_file():
                return f.read_text(errors="replace").rstrip()
        return None
    readme = next((f for f in sorted(path.glob("README*")) if f.is_file()), None) if path.is_dir() else None
    man = MANIFESTS / f"{name}.toml"
    parts = [("RULES.md", (HERE / "RULES.md").read_text().rstrip() if (HERE / "RULES.md").is_file() else None),
             ("CLAUDE.md", first("CLAUDE.md")),
             *([("docs/REFERENCE.md", first("docs/REFERENCE.md"))] if full else []),
             ("docs/DECISIONS.md", first("docs/DECISIONS.md")),
             ("IDEAS.md", first("IDEAS.md")),
              (readme.name if readme else "README", readme.read_text(errors="replace").rstrip() if readme else None),
             (f"hyperbeam manifest (projects/{name}.toml)", man.read_text().rstrip() if man.is_file() else None),
             ("Recent history", recent_history(path) if path.is_dir() else None)]
    if parts_only:
        return parts
    out = [f"# Context for {name}", f"path: {home_rel(path)}", f"date: {time.strftime('%Y-%m-%d')}", "",
           "Paste this at the start of a chat. It is the project's own docs, current as of the date above."]
    for title, body in parts:
        out += ["", f"======== {title} ========", body if body is not None else "(none yet)"]
    return "\n".join(out) + "\n"


def deliver_text(text, label, remote):
    """Text to the clipboard (local) or the outbox (remote). -> 'copied N lines' / 'saved N lines: path'."""
    n = len(text.splitlines())
    if not remote:
        try:
            wl_copy(text)
            return f"copied {n} lines"
        except (RuntimeError, OSError, subprocess.SubprocessError) as e:
            why = f"clipboard failed ({e}); "
    else:
        why = ""
    d = STATE_DIR / "outbox"
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{label}-{time.strftime('%Y%m%d-%H%M%S')}.txt"
    f.write_text(text)
    f.chmod(0o600)
    return f"{why}saved {n} lines: {home_rel(f)}"


def copy_context(name, remote, full=False):
    return deliver_text(context_bundle(name, full=full), f"{name}-context", remote)


# ---------- Copy report: Claude's last message of the project's session ----------
def _user_text(o):
    """The text of a user record, or None if it is a tool result (those are not prompts)."""
    c = (o.get("message") or {}).get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        if any(b.get("type") == "tool_result" for b in c):
            return None
        return "\n".join(b.get("text", "") for b in c if b.get("type") == "text")
    return None


NOT_PROMPT = ("<task-notification", "<system-reminder", "[SYSTEM NOTIFICATION", "<command-", "<local-command", "Caveat:", "[Usage limit", "This session is being continued")


def is_human_prompt(o):
    """Is this conversation-file record something the user typed? Claude Code marks the source of a user record: `origin.kind` is "human" for the
    user, "task-notification" for a finished background task or monitor, "auto-continuation" after a usage limit; records with `isMeta` or
    `isCompactSummary`, tool results and sidechains are never prompts. Files written without `origin` fall back to the text: notices start with
    known tags."""
    if o.get("type") != "user" or o.get("isSidechain") or o.get("isMeta") or o.get("isCompactSummary"):
        return False
    t = _user_text(o)
    if t is None or not t.strip():
        return False
    if "origin" in o:
        return (o["origin"] or {}).get("kind") == "human"
    return not t.lstrip().startswith(NOT_PROMPT)


def last_assistant_message(f):
    """Claude's final text answer in the user's last real prompt's turn (the PR report), not a reply to a notice that arrived after it.
    After the last human prompt the assistant's messages are looked at in order (one API message = the records sharing its id; thinking and tool calls
    are left out). A notice (a finished background task, a monitor) is not a prompt: a reply to it - text, short or after no work, written once
    the notice arrived - is skipped, so the real report stays the answer. If every answer would be skipped, the last text is used."""
    recs = []
    for line in Path(f).read_text(errors="replace").splitlines():
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if o.get("type") in ("user", "assistant") and not o.get("isSidechain"):
            recs.append(o)
    start = max((i for i, o in enumerate(recs) if is_human_prompt(o)), default=-1) + 1
    msgs, order = {}, []                    # assistant messages by id, in order: {id: [text, has_tool, after_notice, worked_since_notice]}
    after_notice = worked = False
    for o in recs[start:]:
        if o["type"] == "user":
            if _user_text(o) is not None and not o.get("isMeta"):         # not a tool result, not the user: a notice
                after_notice, worked = True, False
            continue
        m = o.get("message") or {}
        c = m.get("content")
        blocks = c if isinstance(c, list) else [{"type": "text", "text": c or ""}]
        key = m.get("id") or f"anon{len(order)}"
        if key not in msgs:
            msgs[key] = {"text": [], "tool": False, "notice": after_notice, "worked": worked}
            order.append(key)
        for b in blocks:
            if b.get("type") == "tool_use":
                msgs[key]["tool"] = True
                if after_notice:
                    worked = True
            elif b.get("type") == "text" and b.get("text", "").strip():
                msgs[key]["text"].append(b["text"].strip())
        msgs[key]["worked"] = worked
    texts = [msgs[k] for k in order if msgs[k]["text"]]
    if not texts:
        return ""
    ok = [m for m in texts if not (m["notice"] and (not m["worked"] or len("\n\n".join(m["text"])) < 200))]
    pick = (ok or texts)[-1]
    return "\n\n".join(pick["text"]).strip() + "\n"


def first_line(text, n=70):
    l = next((x.strip() for x in text.splitlines() if x.strip()), "")
    return l if len(l) <= n else l[:n - 1] + "…"


def report_text(name):
    """Claude's last message in the project's Claude pane (HB_CLAUDE_PANE of its session, else the pane running claude). -> text or raises."""
    sess = sanitize(name)
    if not session_exists(sess):
        raise RuntimeError(f"{name} is not running: no Claude session to read")
    pane = tmux("show-environment", "-t", f"={sess}", "HB_CLAUDE_PANE", check=False).stdout.strip().partition("=")[2] or find_claude_pane(sess)
    f = claude_session_file(pane) if pane else None
    if not f:
        raise RuntimeError(f"no Claude is running in {name}'s Claude pane")
    text = last_assistant_message(f)
    if not text:
        raise RuntimeError("Claude has not written a message yet")
    return text


def cmd_refresh_prs(a):
    """hyperbeam refresh-prs [PROJECT] [NUMBER...]: fetch the project's open PRs now (the sidebar picks the result up within seconds). Run it after
    `gh pr create` (with the new number) and after merging or closing one, so the Merge button is right at once."""
    name = a.project or os.environ.get("HB_PROJECT")
    if not name:
        sys.exit("hyperbeam refresh-prs: no project (run it in a project session, or give a name)")
    path = known_path(name)
    if not github_slug(path):
        sys.exit(f"hyperbeam refresh-prs: {name} has no GitHub remote")
    prs = open_prs(name, path, force=True, add=[int(n) for n in a.numbers], gone={int(n) for n in a.gone})
    nudge_menus()
    missing = [n for n in a.numbers if int(n) not in [x["number"] for x in prs]]
    print(f"{name}: {len(prs)} open PR{'s' if len(prs) != 1 else ''}" + "".join(f"\n  #{x['number']} {x['title']}" for x in prs)
          + "".join(f"\n  #{n} is not open (merged, closed, or not yours)" for n in missing))
    return 0


def cmd_copy_last(a):
    name = a.project or os.environ.get("HB_PROJECT")
    if not name:
        sys.exit("hyperbeam copy-last: no project (run it in a project session, or give a name)")
    try:
        text = report_text(name)
    except RuntimeError as e:
        sys.exit(f"hyperbeam copy-last: {e}")
    if a.print:
        print(text, end="")
        return 0
    print(f"{name}: {deliver_text(text, name + '-last', is_remote())} - \"{first_line(text)}\"")
    return 0


