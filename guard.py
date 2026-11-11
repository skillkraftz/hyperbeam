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
    for seg in re.split(r"[;&|\n]+", cmd):
        if re.search(r"tmux\s+-[LS]\s", seg):                       # a pattern aimed at a test server's own command line
            continue
        if re.search(r"\b(?:pkill|killall)\b.*\b(?:tmux|kitty)\b", seg):
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
     "BLOCKED by hyperbeam: killing tmux or kitty processes would take down the user's real sessions and terminals. Instead: stop only a test "
     "server you started yourself (`tmux -L hb-test kill-server`), or ask the user."),
    ("gui-on-user-screens", gui_with_display,
     "BLOCKED by hyperbeam: starting a kitty or other GUI app here would open a window on the user's screens (WAYLAND_DISPLAY or DISPLAY is set). "
     "Instead: run headless (`env -u WAYLAND_DISPLAY -u DISPLAY ...`) or use the lab (coming soon)."),
]


def check(cmd):
    """The message of the first rule the command breaks, else None."""
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
    message = check(str((call.get("tool_input") or {}).get("command", "")))
    if message:
        print(message, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
