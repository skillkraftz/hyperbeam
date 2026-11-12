"""guard.py: only the installed copy of hyperbeam may run as the user (the dev folder's and a worktree's script are blocked), with the exceptions that never
touch state. The review rule is tested in test_swap.py."""
import os
import tempfile
import unittest
from pathlib import Path

from common import load


class InstalledRule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = Path(tempfile.mkdtemp())
        cls.saved_home = os.environ.get("HOME")
        os.environ["HOME"] = str(cls.home)                              # guard.py reads ~ when it is imported
        cls.dev, cls.lib, cls.wt = cls.home / "projects/hyperbeam", cls.home / ".local/lib/hyperbeam", cls.home / ".cache/hyperbeam-work/x"
        for d in (cls.dev, cls.lib, cls.wt):
            d.mkdir(parents=True)
            for f in ("guard.py", "hyperbeam"):
                (d / f).write_text("")
        cls.g = load("guard_installed", "guard.py")

    @classmethod
    def tearDownClass(cls):
        os.environ["HOME"] = cls.saved_home

    def blocked(self, cwd, cmd, g=None):
        g = g or self.g
        g.CWD = str(cwd)
        return g.runs_worktree_script(cmd)

    def test_the_dev_folders_script_is_blocked(self):
        for cmd in ("./hyperbeam list", "uv run --script hyperbeam update", "python3 hyperbeam list", f"{self.dev}/hyperbeam list"):
            self.assertTrue(self.blocked(self.dev, cmd), cmd)

    def test_a_worktrees_script_is_blocked(self):
        self.assertTrue(self.blocked(self.wt, "./hyperbeam list"))

    def test_the_installed_copy_may_run(self):
        self.assertFalse(self.blocked(self.lib, "./hyperbeam list"))

    def test_a_bare_hyperbeam_is_the_one_on_path_not_the_one_in_the_folder(self):
        self.assertFalse(self.blocked(self.dev, "hyperbeam lab run --dir . -- bash t.sh"))
        self.assertFalse(self.blocked(self.dev, "hyperbeam list"))

    def test_exceptions_that_never_touch_state(self):
        self.assertFalse(self.blocked(self.dev, "uv run --script hyperbeam shot --cols 35"))
        self.assertFalse(self.blocked(self.dev, "python3 hyperbeam lab status"))
        self.assertFalse(self.blocked(self.dev, "uv run --script hyperbeam tool --test decisions"))

    def test_a_mention_is_not_a_run(self):
        self.assertFalse(self.blocked(self.dev, "git add hyperbeam"))
        self.assertFalse(self.blocked(self.dev, "python3 -m py_compile hyperbeam"))

    def test_before_the_install_exists_only_worktrees_are_blocked(self):
        home = Path(tempfile.mkdtemp())
        os.environ["HOME"] = str(home)
        try:
            g = load("guard_before", "guard.py")
        finally:
            os.environ["HOME"] = str(self.home)
        dev = home / "projects/hyperbeam"
        dev.mkdir(parents=True)
        for f in ("guard.py", "hyperbeam"):
            (dev / f).write_text("")
        self.assertFalse(self.blocked(dev, "./hyperbeam list", g))


if __name__ == "__main__":
    unittest.main()
