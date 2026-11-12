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


class LabRules(unittest.TestCase):
    """No lab inside the lab, no lab setup and no sudo for agents (the 2026-11-12 incident: `lab run -- ... hyperbeam tool ...` failed with a sudo error that sent an agent to the setup script)."""
    @classmethod
    def setUpClass(cls):
        cls.g = load("guard_lab", "guard.py")
        cls.g.CWD = "/tmp"

    def blocked(self, cmd):
        return self.g.check(cmd) is not None

    def test_a_lab_command_inside_a_lab_run_is_blocked(self):
        for cmd in ("hyperbeam lab run --why x -- uv run --quiet --script hyperbeam tool decisions check",
                    "hyperbeam lab run --why x -- hyperbeam lab status",
                    "hyperbeam lab run -- hyperbeam dotwork test",
                    "hyperbeam lab run -- hyperbeam shot --cols 35"):
            self.assertEqual(self.g.check(cmd), self.g.NEST_MESSAGE, cmd)

    def test_normal_lab_runs_and_direct_tool_calls_are_not(self):
        for cmd in ("hyperbeam lab run --why x -- uv run --quiet --with textual python3 -m unittest discover -s tests",
                    "hyperbeam lab run --dir ~/projects/hyperbeam -- uv run --quiet --script hyperbeam list",
                    "hyperbeam tool decisions check", "hyperbeam hyperbeam test", "hyperbeam lab status"):
            self.assertFalse(self.blocked(cmd), cmd)

    def test_the_setup_scripts_are_blocked_but_reading_them_is_not(self):
        for cmd in ("sudo bash lab/setup.sh", "bash ~/projects/hyperbeam/lab/remove.sh", "sh lab/podman-setup.sh 100G", "./lab/setup.sh", "sudo -n bash /x/lab/setup.sh"):
            self.assertTrue(self.blocked(cmd), cmd)
        for cmd in ("cat lab/setup.sh", "grep -n sudo lab/setup.sh", "sed -n 1,20p lab/remove.sh", "git diff lab/setup.sh"):
            self.assertFalse(self.blocked(cmd), cmd)

    def test_sudo_is_blocked_except_listing_the_rules(self):
        for cmd in ("sudo apt-get install -y gh", "sudo -n -u hblab true", "env X=1 sudo reboot", "echo hi && sudo mount /srv/hblab"):
            self.assertTrue(self.blocked(cmd), cmd)
        for cmd in ("sudo -n -l", "sudo -n -l | head -3", "echo sudo is mentioned", "ls /etc/sudoers.d"):
            self.assertFalse(self.blocked(cmd), cmd)

    def test_the_lab_check_inside_the_lab_says_so_and_never_names_the_setup_script(self):
        import os
        from common import hb
        os.environ["HB_LAB"] = "1"
        try:
            self.assertEqual(hb.lab_ready(), hb.LAB_NESTED)
        finally:
            del os.environ["HB_LAB"]
        for msg in (hb.LAB_NESTED, hb.LAB_SETUP, hb.LAB_USERS_OWN):
            self.assertNotIn("sudo bash", msg)
            self.assertNotIn("run lab/setup.sh", msg)


if __name__ == "__main__":
    unittest.main()
