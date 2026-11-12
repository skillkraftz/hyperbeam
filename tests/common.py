"""Shared by the tests: the hyperbeam script and guard.py loaded as modules, and a throwaway git repo with an origin."""
import importlib.machinery
import importlib.util
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def load(name, file):
    loader = importlib.machinery.SourceFileLoader(name, str(HERE / file))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


hb = load("hb", "hyperbeam")


class Repo:
    """A throwaway repo with an origin: main, and PRs merged with merge commits."""

    def __init__(self):
        self.d = Path(tempfile.mkdtemp())
        self.o, self.r = self.d / "o.git", self.d / "r"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.o)], check=True)
        subprocess.run(["git", "clone", "-q", str(self.o), str(self.r)], check=True, capture_output=True)
        self.git("config", "user.email", "t@t")
        self.git("config", "user.name", "t")
        self.git("checkout", "-qb", "main")
        self.write("README.md", "base\n")
        self.commit("base")
        self.git("push", "-q", "origin", "main")

    def git(self, *a):
        return subprocess.run(["git", *a], cwd=self.r, check=True, capture_output=True, text=True).stdout.strip()

    def write(self, f, text):
        p = self.r / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def commit(self, msg):
        self.git("add", "-A")
        self.git("commit", "-qm", msg)

    def merge_pr(self, n, files=None):
        b = f"pr{n}"
        self.git("checkout", "-qb", b, "main")
        for f in files or [f"file{n}.txt"]:
            self.write(f, f"{n}\n")
        self.commit(f"change {n}")
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--no-ff", "-m", f"Merge pull request #{n} from o/{b}", b)
        self.git("push", "-q", "origin", "main")
        return self.git("rev-parse", "--short", "HEAD")

    def review_record(self, date, through, prs="[1, 2]"):
        self.write(f"docs/reviews/{date}.md", f"---\nthrough: {through}\nprs: {prs}\n---\nreviewed\n")
        self.commit(f"review {date}")
        self.git("push", "-q", "origin", "main")
