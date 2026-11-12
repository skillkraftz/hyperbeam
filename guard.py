#!/usr/bin/env python3
"""hyperbeam guard: a Claude Code PreToolUse hook for the Bash tool (installed by `hyperbeam _hooks`).

Claude Code runs it before every Bash call of a Claude started inside a hyperbeam session (the hook command exits at once without $HB_PROJECT).
It reads the tool call as JSON on stdin ({"tool_name": "Bash", "tool_input": {"command": "..."}, ...}).
To block: print the message on stderr and exit 2 (Claude Code shows stderr to Claude and does not run the command).
To allow: exit 0 with no output. Plain stdlib, no hyperbeam import, ~20 ms.

Why: agents in a hyperbeam session have $TMUX, so a bare `tmux ...` reaches the user's REAL server. Only `-L <name>` or `-S <path>` (a different
socket) reaches another one; TMUX_TMPDIR and `env -u TMUX` do not help while $TMUX is set. One kill-server took down every session.
"""
import json
import os
import re
import shlex
import subprocess
import sys

KILL = r"(?:kill-server|kill-session|kill-window|kill-pane|killw|killp)"
GUI = ("kitty|xterm|gnome-terminal|alacritty|foot|wezterm|konsole|terminator|tilix|firefox|google-chrome|chromium|chrome|code|gedit|"
       "nautilus|eog|evince|xdg-open|gio open|gnome-[a-z-]+|xdotool|wmctrl")


def real_socket():
    """Socket path of the server we are in ($TMUX = path,pid,session): the user's real server."""
    t = os.environ.get("TMUX", "")
    return t.split(",")[0] if t else f"/tmp/tmux-{os.getuid()}/default"


def tmux_calls(cmd):
    """Each `tmux ...` invocation in the command line (up to the next ; & | or newline), as token lists (quotes stripped)."""
    for m in re.finditer(r"(?:^|[\s;&|(`'\"])tmux((?:\s+[^;&|\n)`]*)?)", cmd):
        yield [t.strip("'\"") for t in m.group(1).split()]


def reaches_real_server(args):
    """True unless the call names another socket with -L <name> / -S <path>."""
    real = real_socket()
    for i, a in enumerate(args[:-1]):
        if a == "-L" and args[i + 1] != os.path.basename(real):
            return False
        if a == "-S" and os.path.realpath(args[i + 1]) != os.path.realpath(real):
            return False
    return True


def tmux_kill(cmd):
    return any(any(re.fullmatch(KILL, a) for a in args) and reaches_real_server(args) for args in tmux_calls(cmd))


def kill_tmux_or_kitty(cmd):
    if re.search(r"\bpgrep\b\s+(?:-\S+\s+)*-\w*f[^\n;&]*\|\s*xargs\b[^\n;&]*\bkill", cmd):
        return True
    for seg in re.split(r"[;&|\n]+", cmd):
        if re.search(r"tmux\s+-[LS]\s", seg):                       # a pattern aimed at a test server's own command line
            continue
        if re.search(r"\b(?:pkill|killall)\b.*\b(?:tmux|kitty)\b", seg):
            return True
        # a full-command-line match: a tmux server's command line is the command that created it (`hyperbeam _menu; ...`), so any pattern can hit it
        if re.search(r"\bpkill\b\s+(?:-\S+\s+)*-\w*f", seg) or re.search(r"\bkill\b.*\$\(\s*pgrep\s+(?:-\S+\s+)*-\w*f", seg) \
                or re.search(r"\bpgrep\b\s+(?:-\S+\s+)*-\w*f.*\|\s*xargs\s+(?:\S+\s+)*kill", seg):
            return True
        if re.search(r"\bkill\b.*(?:pgrep|pidof)\b.*\b(?:tmux|kitty)\b", seg):
            return True
        if re.match(r"\s*(?:sudo\s+)?kill\b", seg):                 # kill <pid>: look at what the pid is
            for pid in re.findall(r"(?<![\w-])(\d+)(?!\w)", seg):
                try:
                    comm = open(f"/proc/{pid}/comm").read().strip()
                except OSError:
                    continue
                if comm.startswith(("tmux", "kitty")):
                    return True
    return False


def gui_with_display(cmd):
    """A GUI app started while this environment points at the user's screens, unless the command unsets both variables."""
    if not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")):
        return False
    unset = all(re.search(rf"(?:-u\s+{v}\b|unset\b[^;&|\n]*\b{v}\b|\b{v}=(?:\s|$|;))", cmd) for v in ("WAYLAND_DISPLAY", "DISPLAY"))
    if unset:
        return False
    prefix = r"(?:\w+=\S*\s+|env\s+(?:-\S+\s+)*|sudo\s+|nohup\s+|setsid\s+|exec\s+|command\s+)*"
    return any(re.match(rf"\s*{prefix}(?:\S*/)?(?:{GUI})(?:\s|$)", seg) for seg in re.split(r"[;&|\n(]+", cmd))


# The rules: (name, test, message shown to Claude). Anything that matches none is allowed.
RULES = [
    ("tmux-kill-real-server", tmux_kill,
     "BLOCKED by hyperbeam: this tmux kill command would hit the user's REAL tmux server (you are inside it, via $TMUX): it would take down "
     "hyperbeam and every project session. Instead: for tests use your own server, `tmux -L hb-test ...` (or `-S /tmp/<short>/sock`); "
     "TMUX_TMPDIR does not help while $TMUX is set. Ask the user before touching real sessions."),
    ("kill-tmux-or-kitty", kill_tmux_or_kitty,
     "BLOCKED by hyperbeam: killing tmux or kitty processes would take down the user's real sessions and terminals (also `pkill -f PATTERN`: a "
     "tmux server's command line is the command that created it, so any pattern can match the user's live server). Instead: stop only a test "
     "server you started yourself (`tmux -L hb-test kill-server`), kill your own test processes by pid, or ask the user."),
    ("gui-on-user-screens", gui_with_display,
     "BLOCKED by hyperbeam: starting a kitty or other GUI app here would open a window on the user's screens (WAYLAND_DISPLAY or DISPLAY is set). "
     "Instead: run headless (`env -u WAYLAND_DISPLAY -u DISPLAY ...`) or use the lab (coming soon)."),
]


KILLERS = {"kill", "pkill", "killall"}
WRAPPERS = {"sudo", "env", "nohup", "exec", "time", "command", "xargs", "timeout", "setsid", "stdbuf", "nice", "ionice", "builtin"}
SHELLS = {"bash", "sh", "zsh", "dash"}


def split_commands(cmd):
    """Tokens of each simple command of a command line (split at ; & | newline); None if it can't be parsed (heredoc, odd quoting)."""
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|\n")
        lex.whitespace, lex.whitespace_split = " \t\r", True
        toks = list(lex)
    except ValueError:
        return None
    out, cur = [], []
    for t in toks:
        if set(t) <= set(";&|\n"):
            out.append(cur)
            cur = []
        else:
            cur.append(t)
    return out + [cur]


def is_lab_run(toks):
    toks = [t for t in toks if not re.fullmatch(r"\w+=.*", t)]
    return len(toks) >= 2 and os.path.basename(toks[0]) == "hyperbeam" and (toks[1:3] == ["lab", "run"] or toks[1] in ("tool", "shot"))       # `tool` runs in the lab too


def outside_lab(cmd):
    """The command line without its `hyperbeam lab run ...` parts: those run as the user hblab, in the lab, and may do anything (with no
    command substitution anywhere in the line, which would run as the user first)."""
    cmds = split_commands(cmd)
    if cmds is None or "$(" in cmd or "`" in cmd or "<(" in cmd:
        return cmd
    return "\n".join(" ".join(c) for c in cmds if c and not is_lab_run(c))


def runs_killer(toks):
    for i, t in enumerate(toks):
        if t in WRAPPERS or t.startswith("-") or t.isdigit() or re.fullmatch(r"\w+=.*", t):
            continue
        b = os.path.basename(t)
        if b in KILLERS:
            return True
        if b in SHELLS and "-c" in toks[i + 1:]:                       # bash -c 'kill 1'
            inner = toks[toks.index("-c", i) + 1:][:1]
            return bool(inner) and kill_anywhere(inner[0])
        return False
    return False


def kill_anywhere(cmd):
    cmds = split_commands(cmd)
    if cmds is None:
        return bool(re.search(r"(?<![\w-])(?:kill|pkill|killall)(?![\w-])", cmd))
    return any(runs_killer(c) for c in cmds)


def kill_outside_lab(cmd):
    """Any kill, pkill or killall that does not run through `hyperbeam lab run` (hblab cannot signal the user's processes, you can)."""
    if ("$(" in cmd or "`" in cmd or "<(" in cmd) and re.search(r"(?<![\w-])(?:kill|pkill|killall)(?![\w-])", cmd):
        return True                     # a substitution runs as the user, even inside quotes or a lab command's arguments
    return kill_anywhere(cmd)


# The rules: (name, test, message shown to Claude). Anything that matches none is allowed.
RULES = RULES + [
    ("kill-outside-lab", kill_outside_lab,
     "BLOCKED by hyperbeam: kill, pkill and killall are not allowed here: they run as the user and can take down live sessions (a `pkill -f` once "
     "killed the whole tmux server). Run tests and anything that needs a kill in the lab: `hyperbeam lab run <command>` runs it as the user "
     "hblab, which cannot signal the user's processes (`hyperbeam lab status` shows whether the lab is set up). To stop your own test, give the "
     "lab command a `--timeout`."),
]


CWD = ""         # the tool call's working directory (set by main)


INSTALLED = os.path.expanduser("~/.local/lib/hyperbeam")      # the app the user runs: a clone of main that install.sh keeps current


def is_worktree_dir(d):
    """A folder of a git worktree: under ~/.cache/hyperbeam-work/, or with a .git *file* (a linked worktree), anywhere up its path; or, once hyperbeam is
    installed, any other checkout of hyperbeam itself (the dev folder ~/projects/hyperbeam): only the installed copy may run as the user."""
    d = os.path.realpath(d)
    if "/hyperbeam-work/" in d + "/":
        return True
    if os.path.isdir(INSTALLED) and d != os.path.realpath(INSTALLED) and os.path.isfile(os.path.join(d, "guard.py")) and os.path.isfile(os.path.join(d, "hyperbeam")):
        return True
    while d != "/":
        if os.path.isfile(os.path.join(d, ".git")):
            return True
        d = os.path.dirname(d)
    return False


def runs_worktree_script(cmd):
    """Any token that names a `hyperbeam` script (relative to the working directory, tracking `cd`) inside a worktree."""
    cwd = CWD or os.getcwd()
    for line in cmd.split("\n"):
        try:
            toks = shlex.split(line)
        except ValueError:
            toks = line.split()
        toks = [t for t in toks if not re.fullmatch(r"\w+=.*", t)]
        if not toks:
            continue
        if toks[0] == "cd" and len(toks) > 1:
            cwd = os.path.normpath(os.path.join(cwd, os.path.expandvars(os.path.expanduser(toks[1]))))
            continue
        # the script run directly, or by an interpreter / wrapper (`uv run --script ./hyperbeam`, `python3 hyperbeam`, `timeout 5 ./hyperbeam`);
        # a bare mention (`git add hyperbeam`, `py_compile hyperbeam`) is not a run
        if re.search(r"\blab\s+(?:status|stop|log|digest)\b", " ".join(toks)) or re.search(r"\bhyperbeam\s+(?:tool|shot)\b", " ".join(toks)):         # read-only / per-project lab commands never touch state
            continue
        cand = [toks[0]]
        if re.fullmatch(r"(?:.*/)?(?:python[\d.]*|bash|sh)", toks[0]):          # the script is the first argument that isn't an option (not after -m / -c)
            rest = [t for t in toks[1:] if not t.startswith("-")]
            cand += rest[:1] if not {"-m", "-c"} & set(toks[1:3]) else []
        elif re.fullmatch(r"(?:.*/)?(?:uv|env|timeout|sudo|exec|nohup|setsid)", toks[0]):
            cand += [t for t in toks[1:8] if os.path.basename(t) == "hyperbeam"]
        for t in cand:
            if os.path.basename(t) != "hyperbeam":
                continue
            if t == toks[0] and "/" not in t:          # a bare `hyperbeam` is looked up on PATH (the installed one), not in the working directory
                continue
            p = os.path.normpath(os.path.join(cwd, os.path.expandvars(os.path.expanduser(t))))
            if os.path.isfile(p) and is_worktree_dir(os.path.dirname(p)):
                return True
    return False


RULES = RULES + [
    ("worktree-script-outside-lab", runs_worktree_script,
     "BLOCKED by hyperbeam: a worktree's or the dev folder's `hyperbeam` script must not run as the user: it uses the user's real state, tmux and config (running one "
     "once migrated the user's live state folder). Run it in the lab: `hyperbeam lab run --dir <worktree> -- uv run --quiet --script hyperbeam ...` "
     "(the lab copies the folder and runs it as hblab with its own home, tmux and display). Only `hyperbeam lab run ...` itself is allowed from a "
     "worktree. The installed `hyperbeam` (~/.local/lib/hyperbeam, on PATH) is the one that runs as the user; or ask the user."),
]


def runs_lab_reset(cmd):
    """`hyperbeam lab reset` (forced or not): it kills processes, and the lab is shared with other projects' runs. Agents use `hyperbeam lab stop`."""
    return bool(re.search(r"hyperbeam\S*\s+lab\s+reset\b", cmd))


def force_removes_worktree(cmd):
    for line in cmd.split("\n"):
        try:
            toks = shlex.split(line)
        except ValueError:
            toks = line.split()
        for i in range(len(toks) - 1):
            if toks[i] == "worktree" and toks[i + 1] == "remove" and any(t in ("-f", "-ff", "--force") or re.fullmatch(r"-[a-z]*f[a-z]*", t) for t in toks[i + 2:]):
                return True
    return False


def deletes_dirty_worktree(cmd):
    """`rm -r` of a git worktree folder (or of the folder that holds worktrees) that has uncommitted changes or untracked files."""
    cwd = CWD or os.getcwd()
    for line in cmd.split("\n"):
        try:
            toks = shlex.split(line)
        except ValueError:
            toks = line.split()
        toks = [t for t in toks if not re.fullmatch(r"\w+=.*", t)]
        while toks and toks[0] in ("sudo", "env", "command", "nohup", "time"):
            toks = toks[1:]
        if not toks or os.path.basename(toks[0]) != "rm":
            continue
        if not any(t.startswith("-") and not t.startswith("--") and set(t[1:]) & set("rR") or t == "--recursive" for t in toks[1:]):
            continue
        for t in toks[1:]:
            if t.startswith("-"):
                continue
            path = os.path.normpath(os.path.join(cwd, os.path.expandvars(os.path.expanduser(t))))
            cands = [path]
            if os.path.basename(path) == "hyperbeam-work" and os.path.isdir(path):
                cands = [os.path.join(path, d) for d in os.listdir(path)]
            for c in cands:
                if os.path.isfile(os.path.join(c, ".git")):
                    r = subprocess.run(["git", "-C", c, "status", "--porcelain"], capture_output=True, text=True, timeout=10)
                    if r.stdout.strip():
                        return True
    return False


RULES = RULES + [
    ("lab-reset", runs_lab_reset,
     "BLOCKED by hyperbeam: `hyperbeam lab reset` (forced or not) is for the user only. The lab is shared: reset kills what other projects have running "
     "(it once killed another project's e2e suite). To stop your own runs use `hyperbeam lab stop` (it touches only this project's runs). To see what is "
     "running: `hyperbeam lab status`. If a reset is really needed, ask the user."),
    ("worktree-force-remove", force_removes_worktree,
     "BLOCKED by hyperbeam: `git worktree remove --force` throws away uncommitted work (it was lost once). Commit or stash first, push the branch, then "
     "`git worktree remove <path>` without --force: git itself refuses if something is uncommitted."),
    ("rm-dirty-worktree", deletes_dirty_worktree,
     "BLOCKED by hyperbeam: that worktree has uncommitted changes or untracked files, and deleting it would lose them. Commit or stash first (and push), "
     "then remove it with `git worktree remove <path>`."),
]


def check(cmd):
    """The message of the first rule the command breaks, else None. `hyperbeam lab run ...` parts are not looked at."""
    cmd = outside_lab(cmd)
    for name, test, message in RULES:
        if test(cmd):
            return message
    return None


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
