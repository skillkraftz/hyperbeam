# hyperbeam, part 'merge': open PRs (gh), refresh, Merge. Runs in the namespace of the `hyperbeam` script (see its loader): no imports of its own.
# ---------- open pull requests of the user, through gh (cached; never called from the menu's UI thread) ----------
PR_TTL = 300


def github_slug(path):
    """owner/repo of a project's origin if it is on GitHub (github.com or a github-<account> ssh alias), else None."""
    url = git_out(path, "config", "--get", "remote.origin.url") if (Path(path) / ".git").exists() else ""      # as written, not after url.*.insteadOf
    m = re.match(r"^(?:git@|ssh://git@|https://)(github\.com|github-[\w.-]+)[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url.strip())
    return f"{m.group(2)}/{m.group(3)}" if m and m.group(2).lower() not in IGNORE_OWNERS else None


_GH = {"accounts": None}


def gh_account(owner):
    """The logged-in gh account for a repo owner (same name), else None: that account's token is used for the call (GH_TOKEN), never printed."""
    if _GH["accounts"] is None:
        r = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True) if shutil.which("gh") else None
        _GH["accounts"] = re.findall(r"Logged in to github\.com account (\S+)", (r.stdout + r.stderr) if r else "")
    return next((a for a in _GH["accounts"] if a.lower() == owner.lower()), None)


def gh_run(slug, *args, timeout=30):
    """`gh ARGS -R slug` as the account that owns the repo. -> (returncode, stdout, stderr)."""
    acct = gh_account(slug.split("/")[0])
    if not acct:
        return 1, "", f"no gh login for {slug.split('/')[0]} (run: gh auth login)"
    if acct not in _GH:
        _GH[acct] = subprocess.run(["gh", "auth", "token", "--user", acct], capture_output=True, text=True).stdout.strip()
    env = dict(os.environ, GH_TOKEN=_GH[acct], GH_PROMPT_DISABLED="1")
    try:
        r = subprocess.run(["gh", *args, "-R", slug], capture_output=True, text=True, timeout=timeout, env=env, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return 1, "", "gh timed out"
    return r.returncode, r.stdout, r.stderr


def pr_cache_file(name, path):
    return project_dir(name, path) / "prs.json"


def cached_prs(name, path):
    """What the cache says: (list of PR dicts or None if never fetched, age in seconds, error text)."""
    try:
        d = json.loads(pr_cache_file(name, path).read_text())
        return d.get("prs"), time.time() - d.get("time", 0), d.get("error", "")
    except (OSError, ValueError):
        return None, 1e9, ""


PR_FIELDS = "number,title,url,headRefName,baseRefName,createdAt"


def pr_row(x):
    """One PR as the sidebar keeps it, from a `gh pr list|view --json PR_FIELDS` object."""
    return {"number": x["number"], "title": x["title"], "url": x["url"], "branch": x.get("headRefName", ""), "base": x.get("baseRefName", ""), "created": x.get("createdAt", "")}


def open_prs(name, path, force=False, gone=(), add=()):
    """Open PRs opened by the user (newest first): [{number, title, url, branch}]. Cached for PR_TTL seconds per project, errors too.
    gone: PR numbers just merged. `gh pr list --author` goes through GitHub's search index, which lags a few seconds, so right after a
    merge it still lists the merged PR (the Merge button stayed until a second click). add: PR numbers just opened, looked up one by one
    (`gh pr view` is not behind that index), so a PR created a second ago shows at once."""
    slug = github_slug(path)
    if not slug:
        return []
    prs, age, err = cached_prs(name, path)
    if not force and age < PR_TTL and (prs is not None or err):
        return prs or []
    rc, out, e = gh_run(slug, "pr", "list", "--author", "@me", "--state", "open", "--json", PR_FIELDS)
    try:
        prs = sorted((pr_row(x) for x in json.loads(out)), key=lambda x: -x["number"]) if rc == 0 else None
        prs = [x for x in prs if x["number"] not in gone] if prs is not None else None
        for n in add:
            if prs is not None and n not in [x["number"] for x in prs]:
                rc2, out2, _ = gh_run(slug, "pr", "view", str(n), "--json", PR_FIELDS + ",state")
                x = json.loads(out2) if rc2 == 0 else {}
                if x.get("state") == "OPEN":
                    prs.append(pr_row(x))
        prs = sorted(prs, key=lambda x: -x["number"]) if prs is not None else None
    except (ValueError, KeyError, TypeError):
        prs, e = None, "unreadable gh output"
    try:
        pr_cache_file(name, path).write_text(json.dumps({"time": time.time(), "prs": prs, "error": "" if prs is not None else (e or "gh failed").strip()[:200]}))
    except OSError:
        pass
    return prs or []


STALE_DAYS = 7


def pr_age_days(pr):
    """Whole days since the PR was opened (0 if unknown)."""
    try:
        return max(0, int((time.time() - __import__("calendar").timegm(time.strptime(pr["created"][:19], "%Y-%m-%dT%H:%M:%S"))) // 86400))
    except (KeyError, ValueError, TypeError):
        return 0


def pr_stale(pr):
    return pr_age_days(pr) > STALE_DAYS


def pr_state(path, pr):
    """Where the PR's branch stands against its base: {"behind": commits the base has that the branch lacks, "overlap": files both sides changed since the branch
    point, "conflicts": files a merge would conflict in}, or None when it can't be told (a fork, no network, no branch name). Fetches both branches quietly;
    the dry-run merge touches nothing. Only an overlap is worth stopping the merge for: main moving on in other files (a manifest, another PR) can't change
    this PR's tests; a conflict needs Claude."""
    base = pr.get("base") or default_branch(path)
    head = pr.get("branch")
    if not head:
        return None
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=5")
    f = subprocess.run(["git", "-C", str(path), "fetch", "-q", "origin", f"+refs/heads/{base}:refs/remotes/origin/{base}", f"+refs/heads/{head}:refs/hyperbeam/pr-head"],
                       capture_output=True, text=True, timeout=60, env=env)
    if f.returncode:
        return None
    b, h = f"refs/remotes/origin/{base}", "refs/hyperbeam/pr-head"
    n = git_out(path, "rev-list", "--count", f"{h}..{b}")
    if not n.isdigit():
        return None
    state = {"behind": int(n), "overlap": [], "conflicts": []}
    if not state["behind"]:
        return state
    theirs = set(git_out(path, "diff", "--name-only", f"{h}...{b}").split("\n")) - {""}
    ours = set(git_out(path, "diff", "--name-only", f"{b}...{h}").split("\n")) - {""}
    state["overlap"] = sorted(theirs & ours)
    r = subprocess.run(["git", "-C", str(path), "merge-tree", "--write-tree", "--name-only", "--no-messages", b, h], capture_output=True, text=True, timeout=60)
    if r.returncode == 1:
        state["conflicts"] = [l for l in r.stdout.splitlines()[1:] if l.strip()]
    return state


def update_prompt(name, pr, behind, base, conflicts=()):
    """What Claude is asked to do about a PR that is behind its base (or conflicts with it). Written to the prompts folder; returns the file."""
    why = (f"The PR branch `{pr.get('branch')}` is {behind} commit{'s' if behind != 1 else ''} behind `{base}`, so its tests ran against an older {base}."
           if not conflicts else
           f"The PR branch `{pr.get('branch')}` conflicts with `{base}` ({behind} commit{'s' if behind != 1 else ''} behind) in: {', '.join(conflicts)}. "
           "Merge was run for all the open PRs, oldest first, and stopped here. Files where every PR adds a line at the same spot (an index, a changelog) usually need both sides kept.")
    return write_prompt(sanitize(name), f"""# Update PR #{pr['number']} ({pr['title']}) and re-test it

{why}
Do this, in the project's folder (use a worktree if the checkout has other work):
1. `git fetch`, then rebase the branch onto `origin/{base}` (or merge `origin/{base}` into it if a rebase is messy). Resolve conflicts carefully; ask me if a conflict is not obvious.
2. Re-run the project's tests in the lab: `hyperbeam lab run --why "re-test PR #{pr['number']} on current {base}" ...` (see the project's CLAUDE.md for the test command).
3. Push the branch (`--force-with-lease` after a rebase) and tell me the result: tests pass or fail, what changed.
Do not merge the PR; I will.
""")


def default_branch(path):
    ref = git_out(path, "symbolic-ref", "--short", "-q", "refs/remotes/origin/HEAD")
    return ref.split("/", 1)[1] if "/" in ref else "main"


def merge_pr(name, path, pr, say=print):
    """Merge PR `pr` (a dict from open_prs) with a merge commit and delete the branch; retry once if GitHub says the base branch was modified. Then the local
    checkout, only where that is safe: when it is on the default branch or on the merged branch and has no uncommitted tracked changes it goes to the default
    branch and pulls; anything else (a feature branch you are working on) is left as it is. -> (merged, local_ok, message lines); local_ok: on the default branch, pulled."""
    slug = github_slug(path)
    if not slug:
        return False, False, ["no GitHub remote"]
    for attempt in (1, 2):
        rc, out, err = gh_run(slug, "pr", "merge", str(pr["number"]), "--merge", "--delete-branch")
        if rc == 0:
            break
        if attempt == 1 and "base branch was modified" in (out + err).lower():
            say("base branch was modified, retrying once...")
            time.sleep(2)
            continue
        return False, False, [f"merge failed: {(err or out).strip().splitlines()[-1] if (err or out).strip() else 'gh error'}"]
    msgs = [f"merged PR #{pr['number']} on GitHub"]
    path = Path(path)
    base, cur = default_branch(path), branch_of(path)
    if cur not in (base, pr.get("branch")):
        msgs.append(f"local checkout is on {cur}: left as it is (`git switch {base} && git pull` when you are ready)")
        return True, False, msgs
    if git_out(path, "status", "--porcelain", "--untracked-files=no"):
        msgs.append(f"local checkout has uncommitted changes: left as it is on {cur} (commit or stash, then `git checkout {base} && git pull`)")
        return True, False, msgs
    co = subprocess.run(["git", "-C", str(path), "checkout", "-q", base], capture_output=True, text=True)
    if co.returncode:
        msgs.append(f"could not check out {base}: {co.stderr.strip()[:120]}")
        return True, False, msgs
    pull = subprocess.run(["git", "-C", str(path), "pull", "-q", "--ff-only"], capture_output=True, text=True, timeout=60,
                          env=dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=5"))
    msgs.append(f"local: on {base}" + ("" if pull.returncode == 0 else f", pull failed: {pull.stderr.strip()[:120]}"))
    if pr.get("branch") and pr["branch"] != base:
        subprocess.run(["git", "-C", str(path), "branch", "-d", pr["branch"]], capture_output=True)
    return True, pull.returncode == 0, msgs


def cmd_context(a):
    name = a.project or os.environ.get("HB_PROJECT")
    if not name:
        sys.exit("hyperbeam context: no project (run it in a project session, or give a name)")
    if a.size:
        rows = [(t, len((b or "").encode()), len((b or "").encode()) // 4) for t, b in context_bundle(name, full=a.full, parts_only=True)]
        print(f"{'part':<44}{'bytes':>9}{'~tokens':>9}")
        for t, n, k in rows:
            print(f"{t[:43]:<44}{n:>9}{k:>9}")
        print(f"{'total':<44}{sum(r[1] for r in rows):>9}{sum(r[2] for r in rows):>9}   (tokens = bytes / 4, a rough guide; CLAUDE.md and RULES.md are what Claude loads at every session start)")
        return 0
    if a.print:
        print(context_bundle(name, full=a.full), end="")
        return 0
    print(f"{name}: {copy_context(name, is_remote(), a.full)}")
    return 0


def cmd_clip(a):
    """Mouse drag-select: tmux pipes the selection here. Local client: also onto the Wayland clipboard."""
    text = sys.stdin.read()
    if text and not client_is_remote(a.client_pid):
        try:
            wl_copy(text)
        except (RuntimeError, OSError, subprocess.SubprocessError):
            pass


def cmd_menu(_):
    """`hyperbeam` with no arguments. Desktop, open_mode sidebar: open the sidebar window and return (the old hotkey, `kitty hyperbeam`, leaves
    its own window to close). Otherwise attach to the hyperbeam session's menu window, creating the session if needed."""
    if sidebar_possible():
        print(launch_sidebar())
        return 0
    ensure_menu()
    source_conf()
    tmux("select-window", "-t", f"={MENU}:menu", check=False)
    return attach_here(MENU)


