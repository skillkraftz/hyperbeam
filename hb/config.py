# hyperbeam, part 'config': imports, settings (config.toml), small helpers. Runs in the namespace of the `hyperbeam` script (see its loader): no imports of its own.
import argparse, asyncio, datetime, hashlib, uuid, json, os, pwd, re, shlex, shutil, signal, socket, subprocess, sys, tempfile, textwrap, threading, time, tomllib, types
from pathlib import Path
from urllib.parse import urlparse

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, OptionList, Static
from textual.widgets.option_list import Option


def strip_uv_env():
    """`uv run --script` puts its own environment in ours (VIRTUAL_ENV, UV*, a venv bin dir first in PATH). Everything hyperbeam
    starts (the tmux server, so every project session) must get the normal login environment, so remove it here."""
    venv = os.environ.get("VIRTUAL_ENV", "")
    for k in [k for k in os.environ if k in ("VIRTUAL_ENV", "UV") or k.startswith("UV_")]:
        del os.environ[k]
    os.environ["PATH"] = clean_path(os.environ.get("PATH", ""), venv)


def clean_path(path, venv=""):
    keep = [d for d in path.split(":") if d and d != f"{venv}/bin" and "/.cache/uv/environments-" not in d]
    return ":".join(dict.fromkeys(keep))      # also drops duplicate entries


strip_uv_env()
HERE = Path(os.path.realpath(__file__)).parent
DEFAULT_FILE = HERE / "config.default.toml"      # in the repo: defaults, never written by hyperbeam
CONFIG_FILE = Path(os.environ.get("HB_CONFIG", Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "hyperbeam" / "config.toml"))   # the user's settings (HB_CONFIG is for tests)


def read_toml(f):
    try:
        return tomllib.loads(Path(f).read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def load_cfg():
    """The defaults file overlaid with the user's file."""
    return {**read_toml(DEFAULT_FILE), **read_toml(CONFIG_FILE)}


def migrate_config(legacy=None):
    """Once: if the user has no settings file yet but the repo still has an old config.toml, copy its values over (the repo file is left alone)."""
    legacy = Path(legacy or HERE / "config.toml")
    if CONFIG_FILE.exists() or not legacy.exists():
        return False
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text("# hyperbeam settings: overrides config.default.toml in the repo. The Settings screen writes this file.\n" + legacy.read_text())
    return True


migrate_config()
CFG = load_cfg()
ROOT = Path(os.path.expanduser(os.environ.get("HB_PROJECTS_DIR") or CFG.get("projects_dir", "~/projects")))
MANIFESTS = Path(os.environ.get("HB_MANIFESTS", HERE / "projects"))   # (override is for tests)
ACCOUNTS = {a.lower() for a in CFG["accounts"]}
IGNORE_OWNERS = {o.lower() for o in CFG.get("ignore_owners", [])}        # GitHub owners hyperbeam leaves alone: no PR badge, no Merge, not in `verify`
DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "hyperbeam"     # global files; per project: DATA_DIR/projects/<name>-<hash>/
STATE_DIR = DATA_DIR
OLD_STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "hyperbeam"   # before the foundation PR; migrated once
SKIP = {"node_modules", ".venv", "venv", "target", "dist", "build", "out", "__pycache__",
        ".next", ".cache", ".tox", "vendor", ".git"}
SELF = shlex.quote(str(HERE / "hyperbeam"))
MENU = "manager"            # name of the tmux session the menu runs in: the manager (Opus as a conversation partner about every project); hyperbeam the project is an ordinary one
DEV = "hyperbeam"           # the project hyperbeam itself (~/projects/hyperbeam, the dev folder): an ordinary session, where prompts about hyperbeam go
MANAGER_DIR = Path(os.environ.get("HB_MANAGER", Path.home() / "manager"))       # the manager's notes (a local git repo); HB_MANAGER is for tests
# The keys of hyperbeam.conf (keep in sync with it). Shown in the menu's button bar and Settings tab and in the status bar.
KEYS = [("M-Left/Right/Up/Down", "select pane"), ("M-z", "zoom / unzoom the pane"),
        ("M-h", "back to the hyperbeam session (menu), from anywhere"), ("M-]", "next session in the stack"), ("M-[", "previous session in the stack"),
        ("M-y", "copy the Claude conversation / the pane's whole scrollback (clipboard; outbox over SSH)"),
        ("M-s", "hide / show the sidebar (desktop sidebar window)"), ("Shift+Tab", "Claude plan mode (cycles Claude Code's permission modes)")]
USER_KEYS = [("C-a |  /  C-a -", "split right / below"), ("C-a h j k l", "select pane"), ("C-a H J K L", "resize pane"),
             ("M-n / M-p", "next / previous window"), ("C-a w", "window tree"), ("C-a [", "copy mode (v select, y copy)"),
             ("M-`", "mouse on/off"), ("C-a r", "reload tmux.conf")]
HINT = "M-arrows pane  M-z zoom  M-h menu  M-s sidebar  M-[ M-] stack  M-y copy"


DEFAULTS = {"open_mode": "sidebar", "claude_model": "sonnet", "manager_model": "opus", "claude_effort": "medium", "claude_permissions": "skip", "menu_width": 45, "recent_days": 7, "context_warn": 300000}
CHOICES = {"open_mode": ["sidebar", "switch", "window"], "claude_model": ["sonnet", "opusplan", "opus", "haiku", "fable"], "manager_model": ["opus", "fable", "sonnet", "opusplan", "haiku"],
           "claude_effort": ["low", "medium", "high", "xhigh", "max"], "claude_permissions": ["skip", "ask"], "menu_width": [35, 40, 45, 50, 55, 60], "recent_days": [1, 3, 7, 14, 30]}
CONFIG_NOTES = {"open_mode": '"sidebar" (desktop): one kitty window, menu on the left, tmux on the right that switches sessions. "switch": Open switches this terminal. "window": a new kitty window per project. Over SSH it is always switch.',
                "claude_model": "model for every Claude hyperbeam starts (claude --model): sonnet (the default: planning happens in the manager conversation), opusplan (Opus plans in plan mode, Sonnet does the work; injected prompts then start in plan mode), opus, haiku, fable",
                "manager_model": "model for the manager (the first row: a conversation with Claude about all your projects, never in plan mode, never writes code in a project)",
                "claude_effort": "effort for every Claude hyperbeam starts (claude --effort): low, medium, high, xhigh, max",
                "claude_permissions": '"skip": every Claude hyperbeam starts runs without permission prompts (claude --dangerously-skip-permissions; the guard hook still blocks the dangerous commands). "ask": Claude asks as usual.',
                "menu_width": "columns of the menu sidebar (takes effect when the sidebar window is opened again)",

                "recent_days": "a project opened within this many days is 'recent' (bold white in the menu)"}


def cfg_get(key):
    """A setting from config.toml, read each time so the Settings screen takes effect at once; default if missing or invalid."""
    try:
        v = load_cfg().get(key, DEFAULTS[key])
    except Exception:
        v = DEFAULTS[key]
    return v if type(v) is type(DEFAULTS[key]) and (key not in ("claude_model", "manager_model", "claude_effort", "claude_permissions", "open_mode") or v in CHOICES[key]) else DEFAULTS[key]


def set_config(key, value):
    """Write a setting to the user's config file (created if missing), keeping the rest of the file (comments) as it is."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    text = CONFIG_FILE.read_text() if CONFIG_FILE.exists() else "# hyperbeam settings: overrides config.default.toml in the repo. The Settings screen writes this file.\n"
    line = f"{key} = " + (json.dumps(value) if isinstance(value, str) else str(value))
    if re.search(rf"^{key}\s*=.*$", text, flags=re.M):
        text = re.sub(rf"^{key}\s*=.*$", line, text, flags=re.M)
    else:
        text = text.rstrip("\n") + f"\n# {CONFIG_NOTES[key]}\n{line}\n"
    CONFIG_FILE.write_text(text)


def open_mode():
    return cfg_get("open_mode")


def run(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def tmux(*a, check=True):
    sock = os.environ.get("HB_TMUX_SOCKET")      # tests: an isolated tmux server (`tmux -L`)
    return subprocess.run(["tmux", *(["-L", sock] if sock else []), *a], capture_output=True, text=True, check=check)


def sanitize(name):
    """tmux session name of a project (the manager's session, MENU, is not a project)."""
    return re.sub(r"[.:]", "_", name)


def home_rel(p):
    s = str(p)
    h = str(Path.home())
    return "~" + s[len(h):] if s.startswith(h) else s


