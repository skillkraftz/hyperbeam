#!/usr/bin/env python3
"""hyperbeam guard: a Claude Code PreToolUse hook for the Bash tool (installed by `hyperbeam _hooks`).

Claude Code runs it before every Bash call of a Claude started inside a hyperbeam session (the hook command exits at once without $HB_PROJECT).
It reads the tool call as JSON on stdin ({"tool_name": "Bash", "tool_input": {"command": "..."}, "cwd": "..."}).
To block: print the message on stderr and exit 2. To allow: exit 0 with no output. Plain stdlib, no hyperbeam import.

How: the command line is split into simple commands (heredoc bodies dropped, quoted strings stay single words, so text that merely mentions
`kitty` or `kill` is data and never matches; `bash -c '...'` and `$(...)` are looked into). Each command is reduced to its command word and
arguments (leading VAR=x and wrappers like sudo/env/timeout removed) and tested against RULES. `hyperbeam lab run ...` commands are skipped:
they run as hblab in the lab, which refuses what it must.

Why tmux: agents in a hyperbeam session have $TMUX, so a bare `tmux ...` reaches the user's REAL server. Only `-L <name>` or `-S <path>`
reaches another one. One kill-server took down every session.
"""
import json
import os
import re
import shlex
import subprocess
import sys

CWD = ""                                                      # the tool call's working directory (set by main)
INSTALLED = os.path.expanduser("~/.local/lib/hyperbeam")      # the app the user runs: a clone of main that install.sh keeps current
KILLERS = {"kill", "pkill", "killall"}
TMUX_KILL = {"kill-server", "kill-session", "kill-window", "kill-pane", "killw", "killp"}
WRAPPERS = {"sudo", "env", "nohup", "exec", "time", "command", "xargs", "timeout", "setsid", "stdbuf", "nice", "ionice", "builtin",
            "then", "do", "else", "!"}
SHELLS = {"bash", "sh", "zsh", "dash"}
GUI = {"kitty", "xterm", "gnome-terminal", "alacritty", "foot", "wezterm", "konsole", "terminator", "tilix", "firefox", "google-chrome",
       "chrome", "chromium", "code", "gedit", "nautilus", "eog", "evince", "xdg-open", "xdotool", "wmctrl"}
SETUP_SCRIPT = re.compile(r"(^|/)lab/(setup|remove|podman-setup)\.sh$")
SEP = ";&|\n()`"
base = os.path.basename


def parse(cmd):
    """Token lists of every simple command in a command line, including those inside `bash -c '...'` and `$(...)`/backticks."""
    lines, drop = [], None
    for line in cmd.split("\n"):                               # heredoc bodies are data
        if drop:
            drop = None if line.strip() == drop else drop
            continue
        lines.append(line)
        m = re.search(r"<<-?\s*(['\"]?)(\w+)\1", line)
        drop = m.group(2) if m else None
    text = "\n".join(lines)
    try:
        lex = shlex.shlex(text, posix=True, punctuation_chars=SEP)
        lex.whitespace, lex.whitespace_split = " \t\r", True
        toks = list(lex)
    except ValueError:                                         # odd quoting: split on words
        toks = [w for part in re.split(f"([{re.escape(SEP)}])", text) for w in ([part] if part and part in SEP else part.split())]
    out, cur = [], []
    for t in toks + [";"]:
        if set(t) <= set(SEP):
            if cur:
                out.append(cur)
            cur = []
        else:
            cur.append(t)
    for toks in list(out):
        for t in toks:
            if "$(" in t or "`" in t:                          # inside double quotes a substitution still runs
                out += parse(re.sub(r"\$\(|\)|`", ";", t))
        if "-c" in toks[:-1] and not any(base(t) == "hyperbeam" for t in toks) and any(base(t) in SHELLS for t in toks[:toks.index("-c")]):
            out += parse(toks[toks.index("-c") + 1])
    return out


def head(toks):
    """(wrappers skipped, command word and arguments): leading VAR=x, wrappers, their options and numbers are dropped."""
    wrappers, i = [], 0
    while i < len(toks):
        t = toks[i]
        if re.fullmatch(r"\w+=.*", t):
            pass
        elif t in WRAPPERS or t.startswith("-") or t.isdigit():
            wrappers.append(t)
            i += t == "-u"                                     # env -u NAME
        else:
            break
        i += 1
    return wrappers, toks[i:]


def unset_vars(cmds):
    """Display variables unset somewhere in the line: `-u X`, `unset X`, `X=`."""
    return {v for t in cmds for v in ("WAYLAND_DISPLAY", "DISPLAY")
            if f"{v}=" in t or (v in t[1:] and (t[0] == "unset" or t[t.index(v) - 1] == "-u"))}


def real_socket():
    t = os.environ.get("TMUX", "")                              # $TMUX = path,pid,session: the user's real server
    return t.split(",")[0] if t else f"/tmp/tmux-{os.getuid()}/default"


def tmux_kills_real_server(w, argv, ctx):
    if base(argv[0]) != "tmux" or not TMUX_KILL & set(argv):
        return False
    real = real_socket()
    for i, a in enumerate(argv[:-1]):                           # -L <name> / -S <path> name another server
        if a == "-L" and argv[i + 1] != base(real):
            return False
        if a == "-S" and os.path.realpath(argv[i + 1]) != os.path.realpath(real):
            return False
    return True


def gui_on_screens(w, argv, ctx):
    if not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")) or {"WAYLAND_DISPLAY", "DISPLAY"} <= ctx["unset"]:
        return False
    b = base(argv[0])
    return b in GUI or b.startswith("gnome-") or (b == "gio" and argv[1:2] == ["open"])


def is_worktree_dir(d):
    """A folder of a git worktree (under ~/.cache/hyperbeam-work/, or with a .git *file*, anywhere up its path), or, once hyperbeam is installed,
    any other checkout of hyperbeam itself (the dev folder): only the installed copy may run as the user."""
    d = os.path.realpath(d)
    if "/hyperbeam-work/" in d + "/":
        return True
    if os.path.isdir(INSTALLED) and d != os.path.realpath(INSTALLED) and all(os.path.isfile(os.path.join(d, f)) for f in ("guard.py", "hyperbeam")):
        return True
    while d != "/":
        if os.path.isfile(os.path.join(d, ".git")):
            return True
        d = os.path.dirname(d)
    return False


def worktree_script(w, argv, ctx):
    """The command runs a `hyperbeam` script that lives in a worktree (directly, or by an interpreter like `uv run --script ./hyperbeam`).
    A bare mention (`git add hyperbeam`) is not a run; read-only lab commands, `tool` and `shot` never touch state."""
    if re.search(r"\blab (status|stop|log|digest)\b|\bhyperbeam (tool|shot)\b", " ".join(argv)):
        return False
    cand = [argv[0]]
    if re.fullmatch(r"python[\d.]*|bash|sh", base(argv[0])):
        cand += [t for t in argv[1:] if not t.startswith("-")][:1] if not {"-m", "-c"} & set(argv[1:3]) else []
    elif base(argv[0]) == "uv":
        cand += argv[1:8]
    for t in cand:
        if base(t) != "hyperbeam" or (t == argv[0] and "/" not in t):          # a bare `hyperbeam` is the installed one, from PATH
            continue
        p = os.path.normpath(os.path.join(ctx["cwd"], os.path.expandvars(os.path.expanduser(t))))
        if os.path.isfile(p) and is_worktree_dir(os.path.dirname(p)):
            return True
    return False


def lab_reset(w, argv, ctx):
    return any(base(t) == "hyperbeam" and argv[i + 1:i + 3] == ["lab", "reset"] for i, t in enumerate(argv))


def lab_setup(w, argv, ctx):
    """Running lab/setup.sh, remove.sh or podman-setup.sh (directly or with a shell). Reading them is fine."""
    script = [t for t in argv[1:] if not t.startswith("-")][:1] if base(argv[0]) in SHELLS else argv[:1]
    return bool(script) and bool(SETUP_SCRIPT.search(script[0]))


def sudo(w, argv, ctx):
    """Any sudo except `sudo -n -l` (listing the rules)."""
    return "sudo" in w and not (not argv and w[w.index("sudo") + 1:] in (["-n", "-l"], ["-nl"], ["-ln"]))


def worktree_force_remove(w, argv, ctx):
    return any(argv[i:i + 2] == ["worktree", "remove"] and any(re.fullmatch(r"--force|-[a-z]*f[a-z]*", t) for t in argv[i + 2:])
               for i in range(len(argv)))


def rm_dirty_worktree(w, argv, ctx):
    """`rm -r` of a git worktree folder (or of the folder that holds worktrees) with uncommitted changes or untracked files."""
    if base(argv[0]) != "rm" or not any(re.fullmatch(r"-[a-zA-Z]*[rR][a-zA-Z]*|--recursive", t) for t in argv[1:]):
        return False
    for t in argv[1:]:
        if t.startswith("-"):
            continue
        path = os.path.normpath(os.path.join(ctx["cwd"], os.path.expandvars(os.path.expanduser(t))))
        cands = [os.path.join(path, d) for d in os.listdir(path)] if base(path) == "hyperbeam-work" and os.path.isdir(path) else [path]
        for c in cands:
            if os.path.isfile(os.path.join(c, ".git")):
                r = subprocess.run(["git", "-C", c, "status", "--porcelain"], capture_output=True, text=True, timeout=10)
                if r.stdout.strip():
                    return True
    return False


# The rules: (name, test(wrappers, argv, ctx), message shown to Claude). Anything that matches none is allowed.
RULES = [
    ("tmux-kill-real-server", tmux_kills_real_server,
     "BLOCKED by hyperbeam: this tmux kill command would hit the user's REAL tmux server (you are inside it, via $TMUX): it would take down "
     "hyperbeam and every project session. Instead: for tests use your own server, `tmux -L hb-test ...` (or `-S /tmp/<short>/sock`); "
     "TMUX_TMPDIR does not help while $TMUX is set. Ask the user before touching real sessions."),
    ("kill-outside-lab", lambda w, argv, ctx: base(argv[0]) in KILLERS,
     "BLOCKED by hyperbeam: kill, pkill and killall are not allowed here: they run as the user and can take down live sessions (a `pkill -f` once "
     "killed the whole tmux server: a server's command line is the command that created it, so any pattern can match it). Run tests and anything "
     "that needs a kill in the lab: `hyperbeam lab run <command>` runs it as the user hblab, which cannot signal the user's processes "
     "(`hyperbeam lab status` shows whether the lab is set up). To stop your own test, give the lab command a `--timeout`. If the word only appears "
     "in text (a PR body, a commit message), write that text to a file with the Write tool and pass it with `--body-file` or `-F`."),
    ("gui-on-user-screens", gui_on_screens,
     "BLOCKED by hyperbeam: starting a kitty or other GUI app here would open a window on the user's screens (WAYLAND_DISPLAY or DISPLAY is set). "
     "Instead: run headless (`env -u WAYLAND_DISPLAY -u DISPLAY ...`) or use the lab."),
    ("worktree-script-outside-lab", worktree_script,
     "BLOCKED by hyperbeam: a worktree's or the dev folder's `hyperbeam` script must not run as the user: it uses the user's real state, tmux and config (running one "
     "once migrated the user's live state folder). Run it in the lab: `hyperbeam lab run --dir <worktree> -- uv run --quiet --script hyperbeam ...` "
     "(the lab copies the folder and runs it as hblab with its own home, tmux and display). Only `hyperbeam lab run ...` itself is allowed from a "
     "worktree. The installed `hyperbeam` (~/.local/lib/hyperbeam, on PATH) is the one that runs as the user; or ask the user."),
    ("lab-reset", lab_reset,
     "BLOCKED by hyperbeam: `hyperbeam lab reset` (forced or not) is for the user only. The lab is shared: reset kills what other projects have running "
     "(it once killed another project's e2e suite). To stop your own runs use `hyperbeam lab stop` (it touches only this project's runs). To see what is "
     "running: `hyperbeam lab status`. If a reset is really needed, ask the user."),
    ("lab-setup", lab_setup,
     "BLOCKED by hyperbeam: lab/setup.sh, remove.sh and podman-setup.sh are for the user only (they change /etc, the disk image, the hblab user). If the lab fails, "
     "check read-only (`hyperbeam lab status`, `id hblab`, `df /srv/hblab`, the last lines of ~/.local/share/hyperbeam/lab-runs.jsonl), report what you find and "
     "ask the user. An error message is not a reason to change the lab."),
    ("sudo", sudo,
     "BLOCKED by hyperbeam: agents don't use sudo (only `sudo -n -l`, to list rules). Tests and tools run as hblab through `hyperbeam lab run`, `hyperbeam tool` and "
     "`hyperbeam NAME test`. If something really needs root, say what and why, and ask the user to run it."),
    ("worktree-force-remove", worktree_force_remove,
     "BLOCKED by hyperbeam: `git worktree remove --force` throws away uncommitted work (it was lost once). Commit or stash first, push the branch, then "
     "`git worktree remove <path>` without --force: git itself refuses if something is uncommitted."),
    ("rm-dirty-worktree", rm_dirty_worktree,
     "BLOCKED by hyperbeam: that worktree has uncommitted changes or untracked files, and deleting it would lose them. Commit or stash first (and push), "
     "then remove it with `git worktree remove <path>`."),
]


def violations(cmd):
    """(name, message) of every rule the command line breaks. `hyperbeam lab run|tool|shot ...` commands are skipped (they run in the lab, which
    refuses a lab inside the lab itself)."""
    raw = parse(cmd)
    ctx, found = {"cwd": CWD or os.getcwd(), "unset": unset_vars(raw)}, []
    for w, argv in map(head, raw):
        if not argv:
            continue
        if argv[0] == "cd" and len(argv) > 1:
            ctx["cwd"] = os.path.normpath(os.path.join(ctx["cwd"], os.path.expandvars(os.path.expanduser(argv[1]))))
        elif not (base(argv[0]) == "hyperbeam" and (argv[1:3] == ["lab", "run"] or argv[1:2] in (["tool"], ["shot"]))):
            found += [(n, m) for n, test, m in RULES if test(w, argv, ctx)]
    return found


def check(cmd):
    """The message of the first rule the command breaks, else None."""
    found = violations(cmd)
    return found[0][1] if found else None


def main():
    try:
        call = json.load(sys.stdin)
    except ValueError:
        return 0
    if call.get("tool_name") != "Bash":
        return 0
    global CWD
    CWD = str(call.get("cwd") or "")
    message = check(str((call.get("tool_input") or {}).get("command", "")))
    if message:
        print(message, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
